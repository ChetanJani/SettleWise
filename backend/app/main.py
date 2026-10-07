from contextlib import asynccontextmanager
from copy import deepcopy
import asyncio
import json
import re
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from .config import API_KEY, DATABASE_URL, ROOT
from .database import Store
from .models import SearchRequest, RecommendationRequest, DetailRequest, ObservationInput, PropertyInputs
from .provider import SerpApi, ProviderError, safe_url, stamp
from .ranking import rank
from .demo import demo_properties, demo_commute, demo_overview

def create_app(database_url=DATABASE_URL, api_key=API_KEY, provider=None):
    store=Store(database_url)
    @asynccontextmanager
    async def lifespan(app):
        try:await asyncio.to_thread(store.initialise)
        except Exception:store.ready=False
        app.state.provider=provider or SerpApi(api_key)
        yield
        await app.state.provider.close()
        store.engine.dispose()

    app=FastAPI(title='SettleWise',version='2.0.0',lifespan=lifespan)
    app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5174','http://localhost:5174'],allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','X-Client-Id'])
    app.state.store=store;app.state.inventory={};app.state.rates={}

    def require_database():
        if not store.ready:raise HTTPException(503,'Saving and community storage are unavailable. Check the database connection and restart the backend.')

    def require_provider():
        if not api_key and not provider:raise HTTPException(503,'Live search needs a SerpApi key. Add it to backend/.env and restart. Example mode remains available.')
        return app.state.provider

    def identity(token):
        if not token or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',token):raise HTTPException(400,'A valid browser identifier is required.')
        return token

    async def remember(items):
        for p in items:app.state.inventory[p['id']]=deepcopy(p)
        if len(app.state.inventory)>500:
            for key in list(app.state.inventory)[:100]:app.state.inventory.pop(key,None)
        if store.ready:await asyncio.to_thread(store.put_properties,items)

    async def get_property(pid):
        p=app.state.inventory.get(pid)
        if p:return deepcopy(p)
        if store.ready:return await asyncio.to_thread(store.get,pid)
        return None

    async def personal(items, token):
        return await asyncio.to_thread(store.inputs,identity(token),items) if token and store.ready else items

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request,exc):
        # Never put connection strings, SQL parameters, or upstream exceptions in responses.
        return JSONResponse(status_code=503,content={'detail':'Database operation unavailable. Try again; your existing data has not been replaced.'})

    @app.get('/api/health')
    def health():
        return {'app':'SettleWise','version':'2.0.0','status':'ok' if store.ready else 'degraded','serpapi_configured':bool(api_key or provider),'database':store.kind,'database_ready':store.ready,'default_mode':'live' if api_key or provider else 'demo'}

    @app.get('/api/autocomplete')
    async def autocomplete(q:str=Query(min_length=3,max_length=180),city:str=Query(default='Ahmedabad',max_length=80)):
        try:return {'suggestions':await require_provider().autocomplete(q,city)}
        except ProviderError as exc:raise HTTPException(502,str(exc)) from None

    @app.post('/api/search')
    async def search(body:SearchRequest,x_client_id:str|None=Header(default=None)):
        warnings=[];leads=[]
        if body.mode=='demo':
            items=demo_properties(body.area,body.city)
            centre={'lat':23.040,'lng':72.552,'name':body.area+' (example)'} if body.city.lower()=='ahmedabad' else None
            if body.property_type=='hotel':items=[];warnings.append('Example mode contains monthly rentals only. Use live search for date-specific hotel results.')
            for p in items:p['commute']=demo_commute(p,body)
            warnings.append('Example mode: properties, prices, routes and illustrations are fictional. No real availability is implied.')
        else:
            try:
                async with asyncio.timeout(65):centre,items,leads=await require_provider().discover(body)
            except ProviderError as exc:raise HTTPException(502,str(exc)) from None
            except TimeoutError:raise HTTPException(504,'Finding places took too long. Try a smaller area.') from None
            # Explicit local inventory augments discovery; there is no invented rental feed.
            inventory_file=ROOT/'inventory.json'
            if inventory_file.exists():
                try:
                    for p in json.loads(inventory_file.read_text(encoding='utf-8')):
                        if str(p.get('city','')).casefold()!=body.city.casefold() or str(p.get('area','')).casefold()!=body.area.casefold():continue
                        if not p.get('id') or not p.get('name') or p.get('type') not in ('flat','pg','hostel','house'):continue
                        if not isinstance(p.get('price'),(int,float)) or p['price']<0:continue
                        item={'amenities':[],'images':[],'price_unit':'month','occupancy':None,'bedrooms':None,'deposit':None,'maintenance':None,'gender_restriction':None,'is_demo':False,'verified':False,'last_updated':stamp(),'coordinates':None,**p,'source_kind':'owner_listing','source_name':'Provided listing','source_url':safe_url(p.get('source_url')),'listing_status':'Provided listing — confirm availability and terms'}
                        item['images']=[im for im in item['images'] if isinstance(im,dict) and safe_url(im.get('url'))]
                        items.append(item)
                except (ValueError,TypeError,KeyError):warnings.append('The local listing file could not be loaded.')
        await remember(items)
        data=rank(await personal(items,x_client_id),body)
        return {**data,'candidate_ids':[p['id'] for p in items],'area_location':centre,'listing_leads':leads,'mode':body.mode,'warnings':warnings,'generated_at':stamp(),'area':body.area,'city':body.city}

    @app.post('/api/recommendations')
    async def recommendations(body:RecommendationRequest,x_client_id:str|None=Header(default=None)):
        items=[]
        for pid in dict.fromkeys(body.property_ids):
            if p:=await get_property(pid):
                # Keep example and real places strictly separated even across stored searches.
                if bool(p.get('is_demo'))!=(body.preferences.mode=='demo'):continue
                items.append(p)
        if body.preferences.destination and (body.preferences.priority=='commute' or body.preferences.max_commute or body.preferences.sort=='commute'):
            # Check six candidates on explicit commute prioritisation, not every visible card.
            targets=items[:6]
            async def travel(p):
                p['commute']=demo_commute(p,body.preferences) if p.get('is_demo') else await require_provider().commute(p,body.preferences)
            try:
                async with asyncio.timeout(65):await asyncio.gather(*(travel(p) for p in targets))
            except TimeoutError:pass
        elif body.preferences.mode=='demo':
            for p in items:p['commute']=demo_commute(p,body.preferences)
        return {**rank(await personal(items,x_client_id),body.preferences),'route_candidates_checked':min(6,len(items)) if body.preferences.priority=='commute' and body.preferences.destination else 0}

    @app.post('/api/properties/{pid}/details')
    async def details(pid:str,body:DetailRequest,x_client_id:str|None=Header(default=None)):
        p=await get_property(pid)
        if not p:raise HTTPException(404,'This place is no longer in the local search cache. Search again.')
        if bool(p.get('is_demo'))!=(body.preferences.mode=='demo'):raise HTTPException(400,'The place and search mode do not match.')
        if p.get('is_demo'):
            if body.section=='overview':data=demo_overview(p,body.preferences)
            elif body.section=='nearby':data={'places':[],'warnings':['Nearby services require live search. No fictional businesses are presented.']}
            else:data={'sources':[],'summary':'No real safety reports are asserted in example mode.'}
        else:
            try:
                async with asyncio.timeout(65):
                    provider=require_provider()
                    data=await (provider.overview(p,body.preferences) if body.section=='overview' else provider.nearby(p,body.preferences) if body.section=='nearby' else provider.area_evidence(p,body.preferences))
            except TimeoutError:raise HTTPException(504,'Some local information took too long to load. Try again.') from None
            except ProviderError as exc:raise HTTPException(502,str(exc)) from None
        p=(await personal([p],x_client_id))[0]
        return {'property':p,'section':body.section,**data}

    @app.post('/api/properties/{pid}/inputs')
    async def inputs(pid:str,body:PropertyInputs,x_client_id:str|None=Header(default=None)):
        require_database();client=identity(x_client_id)
        p=await get_property(pid)
        if not p:raise HTTPException(404,'Place not found.')
        if p.get('price_unit')=='night':raise HTTPException(400,'Hotel prices use the dated source, not monthly rental inputs.')
        await asyncio.to_thread(store.set_inputs,client,pid,body.model_dump(exclude_none=True))
        return {'property':(await personal([p],client))[0]}

    @app.get('/api/saved')
    def saved(x_client_id:str|None=Header(default=None)):
        require_database();client=identity(x_client_id);return {'properties':store.inputs(client,store.saved(client))}

    @app.post('/api/saved/{pid}')
    async def save(pid:str,x_client_id:str|None=Header(default=None)):
        require_database();client=identity(x_client_id)
        if not await get_property(pid):raise HTTPException(404,'Place not found.')
        await asyncio.to_thread(store.save,client,pid,True)
        return {'saved':True,'property_id':pid}

    @app.delete('/api/saved/{pid}')
    def unsave(pid:str,x_client_id:str|None=Header(default=None)):
        require_database();store.save(identity(x_client_id),pid,False)
        return {'saved':False,'property_id':pid}

    @app.get('/api/observations')
    def observations(area:str=Query(min_length=2,max_length=160),city:str=Query(min_length=2,max_length=80)):
        require_database();return {'observations':store.observations(area,city)}

    @app.post('/api/observations',status_code=201)
    def observe(body:ObservationInput,x_client_id:str|None=Header(default=None)):
        require_database();client=identity(x_client_id);now=time.monotonic()
        recent=[t for t in app.state.rates.get(client,[]) if now-t<60]
        if len(recent)>=5:raise HTTPException(429,'Please wait a minute before posting another observation.')
        if len(app.state.rates)>1000:app.state.rates.clear()
        app.state.rates[client]=recent+[now]
        return store.observe(body)

    @app.post('/api/observations/{oid}/helpful')
    def helpful(oid:str,x_client_id:str|None=Header(default=None)):
        require_database();row=store.helpful(identity(x_client_id),oid)
        if not row:raise HTTPException(404,'Observation not found.')
        return row

    return app

app=create_app()
