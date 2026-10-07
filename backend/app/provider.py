"""SerpApi adapters with bounded concurrency and no fabricated live fields."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import math
import time
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import httpx

logging.getLogger('httpx').setLevel(logging.WARNING)

class ProviderError(Exception): pass

def stamp(): return datetime.now(timezone.utc).isoformat()

def safe_url(value):
    if not isinstance(value,str): return None
    try:
        u=urlparse(value)
        if u.scheme not in ('https','http') or not u.hostname or u.username:return None
        return urlunparse(u._replace(query=urlencode([(k,v) for k,v in parse_qsl(u.query) if k.lower() not in ('api_key','key','token','access_token')]),fragment=''))
    except ValueError:return None

def maps_link(q):return 'https://www.google.com/maps/search/?'+urlencode({'api':1,'query':q})

def coords(row):
    p=row.get('gps_coordinates') or {}
    try:
        lat,lng=float(p['latitude']),float(p['longitude'])
        if math.isfinite(lat) and math.isfinite(lng) and -90<=lat<=90 and -180<=lng<=180:return {'lat':lat,'lng':lng}
    except (KeyError,ValueError,TypeError):pass
    return None

def km(a,b):
    x,y=map(math.radians,(a['lat'],b['lat']))
    dlat=math.radians(b['lat']-a['lat']);dlng=math.radians(b['lng']-a['lng'])
    h=math.sin(dlat/2)**2+math.cos(x)*math.cos(y)*math.sin(dlng/2)**2
    return round(6371*2*math.atan2(math.sqrt(h),math.sqrt(max(0,1-h))),2)

def rows(payload):
    if isinstance(payload.get('place_results'),dict):return [payload['place_results']]
    return [r for r in payload.get('local_results',[]) if isinstance(r,dict)]

def finite(v):return v if isinstance(v,(int,float)) and math.isfinite(v) else None

def property_type(row):
    text=' '.join([str(row.get('title','')),str(row.get('type','')),str(row.get('description',''))]+[str(x) for x in row.get('types',[]) or []]).lower()
    if any(x in text for x in ('paying guest',' pg ','p.g.','pg accommodation','boys pg','girls pg')) or text.startswith('pg '):return 'pg'
    if 'hostel' in text:return 'hostel'
    if any(x in text for x in ('hotel','resort','guest house','guesthouse')):return 'hotel'
    if any(x in text for x in ('apartment','flats','flat ','residential complex')):return 'flat'
    if any(x in text for x in ('bungalow','villa',' house')):return 'house'
    return 'other'

def base_property(row,area,city,kind='maps'):
    point=coords(row)
    title=row.get('title') or row.get('name') or 'Accommodation'
    identifier=str(row.get('place_id') or row.get('data_id') or row.get('property_token') or row.get('link') or title+str(point))
    photo=safe_url(row.get('thumbnail'))
    p={
        'id':kind+'-'+hashlib.sha256(identifier.encode()).hexdigest()[:24],
        'name':title,'type':property_type({**row,'title':title}),'area':area,'city':city,
        'address':row.get('address') or None,'coordinates':point,'price':None,'price_unit':'month',
        'deposit':None,'maintenance':None,'bedrooms':None,'bathrooms':None,'occupancy':None,
        'gender_restriction':None,'amenities':[],'furnishing':None,'ventilation':None,
        'rating':finite(row.get('rating') or row.get('overall_rating')),'review_count':finite(row.get('reviews')),
        'images':[{'url':photo,'kind':'place_photo','caption':'Place photo; available room may differ'}] if photo else [],
        'source_kind':'map_place','source_name':'Google Maps','source_url':maps_link(title+' '+city),
        'listing_status':'Availability and rental details need confirmation','verified':False,'is_demo':False,
        'last_updated':stamp(),'phone':row.get('phone'),'website':safe_url(row.get('website')),
        'place_id':row.get('place_id'),'data_id':row.get('data_id'),'property_token':row.get('property_token'),
        'description':row.get('description') or 'A map-listed place. Confirm the available accommodation, price and terms with the provider.'
    }
    return p

class SerpApi:
    def __init__(self,key):
        self.key=key;self.cache={};self.locks={};self.sem=asyncio.Semaphore(3)
        self.http=httpx.AsyncClient(timeout=httpx.Timeout(22,connect=8))
        self.request_count=0

    async def close(self):await self.http.aclose()

    async def search(self,engine,ttl=1800,**params):
        query={'engine':engine,'hl':'en',**{k:v for k,v in params.items() if v is not None}}
        ck=hashlib.sha256(json.dumps(query,sort_keys=True).encode()).hexdigest()
        cached=self.cache.get(ck)
        if cached and time.monotonic()-cached[0]<ttl:return deepcopy(cached[1])
        # Per-query locks prevent identical in-flight searches consuming extra credits.
        lock=self.locks.setdefault(ck,asyncio.Lock())
        async with lock:
            cached=self.cache.get(ck)
            if cached and time.monotonic()-cached[0]<ttl:return deepcopy(cached[1])
            async with self.sem:
                if not self.key:raise ProviderError('Live search needs a SerpApi key in backend/.env.')
                try:
                    response=await self.http.get('https://serpapi.com/search.json',params={**query,'api_key':self.key})
                    self.request_count+=1
                    if response.status_code in (401,403):raise ProviderError('SerpApi rejected the configured key. Check the local key file.')
                    if response.status_code==429:raise ProviderError('SerpApi search credits or rate limit reached. Check your account.')
                    if response.status_code>=400:raise ProviderError('The search provider could not complete this request.')
                    payload=response.json()
                    if not isinstance(payload,dict):raise ProviderError('The search provider returned an unexpected response.')
                    if payload.get('error'):
                        if "hasn't returned any results" in str(payload['error']).lower():payload={}
                        else:raise ProviderError('No usable response from SerpApi. Check the query and available search credits.')
                except (httpx.RequestError,ValueError):raise ProviderError('The search provider is unavailable or timed out. Try again.') from None
            payload.pop('search_parameters',None)
            if len(self.cache)>400:
                oldest=min(self.cache,key=lambda k:self.cache[k][0]);self.cache.pop(oldest,None)
                if oldest!=ck:self.locks.pop(oldest,None)
            self.cache[ck]=(time.monotonic(),deepcopy(payload))
            return payload

    async def resolve(self,text,city=''):
        city='' if city=='Worldwide' else city
        p=await self.search('google_maps',q=(text+' '+city).strip(),type='search',ttl=86400)
        for row in rows(p):
            point=coords(row)
            if point:return {**point,'name':row.get('title',text),'address':row.get('address',text),'source_url':maps_link(text+' '+city)}
        return None

    async def autocomplete(self,q,city):
        async def nearby():
            if city=='Worldwide':return {}
            centre=await self.resolve(city)
            if not centre:return {}
            return await self.search('google_maps_autocomplete',q=q,ll=f"@{centre['lat']},{centre['lng']},12z")
        responses=await asyncio.gather(nearby(),self.search('google_maps_autocomplete',q=q,ll='@0,0,3z'),return_exceptions=True)
        if all(isinstance(p,Exception) for p in responses):raise ProviderError('Location suggestions are temporarily unavailable. You can still type a full area and city.')
        result=[];seen=set();batches=[]
        for payload in responses:
            suggestions=(payload.get('suggestions') or payload.get('suggestion_results') or []) if isinstance(payload,dict) else []
            batch=[]
            for s in suggestions[:8]:
                if isinstance(s,str):s={'value':s}
                if not isinstance(s,dict):continue
                value=s.get('value') or s.get('title') or s.get('text') or s.get('name')
                if not isinstance(value,str) or not value.strip():continue
                point=coords({'gps_coordinates':{'latitude':s.get('latitude'),'longitude':s.get('longitude')}})
                address=str(s.get('subtext') or '')[:240]
                batch.append({'text':value[:160],'address':address,'coordinates':point,'type':s.get('type','place' if point else 'keyword')})
            batches.append(batch)
        # Interleave nearby and worldwide results without discarding place context.
        for i in range(8):
            for batch in batches:
                if i>=len(batch):continue
                s=batch[i];key=(s['text'].casefold(),s['address'].casefold())
                if key in seen:continue
                seen.add(key);result.append(s)
        return result[:12]

    async def discover(self,body):
        centre=body.location.model_dump() if body.location else await self.resolve(body.area,body.city)
        if not centre:raise ProviderError('We could not locate that area. Add a city or choose a more specific location.')
        context=f'{body.location.name}, {body.location.address}'.strip(', ') if body.location else body.area if body.city=='Worldwide' else f'{body.area}, {body.city}'
        if body.property_type=='hotel':
            p=await self.search('google_hotels',q=f'Hotels near {context}',currency='INR',check_in_date=body.check_in.isoformat(),check_out_date=body.check_out.isoformat(),adults=body.occupants,ttl=600)
            items=[]
            for row in p.get('properties',[])[:16]:
                item=base_property(row,body.area,body.city,'hotel')
                item.update(type='hotel',price=finite((row.get('rate_per_night') or {}).get('extracted_lowest')),price_unit='night',total_stay_price=finite((row.get('total_rate') or {}).get('extracted_lowest')),amenities=[str(a) for a in row.get('amenities',[])],source_kind='hotel_result',source_name='Google Hotels',source_url=safe_url(row.get('link')) or maps_link(row.get('name','')+' '+body.city),stay_dates={'check_in':body.check_in.isoformat(),'check_out':body.check_out.isoformat(),'guests':body.occupants},listing_status='Date-specific search price; confirm final terms with booking provider')
                item['images']=[{'url':u,'kind':'hotel_photo','caption':'Hotel photo; room category may differ'} for im in row.get('images',[])[:6] if (u:=safe_url(im.get('original_image') or im.get('thumbnail') if isinstance(im,dict) else im))]
                if row.get('gps_coordinates'):item['coordinates']=coords(row)
                items.append(item)
            return centre,items,[]
        queries={'any':'PG hostels rental accommodation','pg':'paying guest PG accommodation','hostel':'hostels','flat':'residential apartments flats','house':'rental houses bungalows'}
        payload=await self.search('google_maps',q=f'{queries[body.property_type]} near {context}',type='search',ll=f"@{centre['lat']},{centre['lng']},14z")
        items=[]
        for row in rows(payload):
            item=base_property(row,body.area,body.city)
            point=item['coordinates']
            if not point or km(centre,point)>12:continue
            item['area_distance_km']=km(centre,point)
            if body.property_type!='any' and item['type'] not in (body.property_type,'other'):continue
            if item['type']=='hotel':continue
            items.append(item)
        leads=[]
        if body.property_type in ('any','flat','house'):
            try:
                search=await self.search('google',q=f'{body.property_type if body.property_type!="any" else "flats"} for rent {context}',num=6,ttl=3600)
                for r in search.get('organic_results',[])[:5]:
                    if u:=safe_url(r.get('link')):leads.append({'title':r.get('title','Listing website'),'url':u,'snippet':r.get('snippet',''),'source':'Google Search','verified':False})
            except ProviderError:pass
        return centre,items[:16],leads

    async def commute(self,prop,body):
        if not body.destination or not prop.get('coordinates'):return None
        point=prop['coordinates'];code={'transit':3,'driving':0,'two_wheeler':9,'walking':2,'cycling':1}[body.travel_mode]
        india=timezone(timedelta(hours=5,minutes=30));day=datetime.now(india).date()+timedelta(days=1)
        while day.weekday()>4:day+=timedelta(days=1)
        def timestamp(hhmm):
            h,m=map(int,hhmm.split(':'));return int(datetime(day.year,day.month,day.day,h,m,tzinfo=india).timestamp())
        async def route(returning):
            parameters={'start_addr':body.destination,'end_coords':f"{point['lat']},{point['lng']}"} if returning else {'start_coords':f"{point['lat']},{point['lng']}",'end_addr':body.destination}
            try:
                p=await self.search('google_maps_directions',**parameters,travel_mode=code,time=f"depart_at:{timestamp(body.return_time if returning else body.departure_time)}",distance_unit=0,gl='in',ttl=900)
                name={'transit':'transit','driving':'driving','two_wheeler':'two-wheeler','walking':'walking','cycling':'cycling'}[body.travel_mode]
                candidates=[r for r in p.get('directions',[]) if str(r.get('travel_mode','')).lower().replace('two wheeler','two-wheeler')==name and finite(r.get('duration')) is not None and r['duration']>=0]
                if not candidates:return {'minutes':None,'distance_km':None,'error':'No route returned for this transport mode.'}
                r=min(candidates,key=lambda r:r['duration'])
                return {'minutes':math.ceil(r['duration']/60),'distance_km':round(r['distance']/1000,2) if finite(r.get('distance')) is not None else None}
            except ProviderError as exc:return {'minutes':None,'distance_km':None,'error':str(exc)}
        outward,inward=await asyncio.gather(route(False),route(True))
        return {'morning':outward,'evening':inward,'mode':body.travel_mode,'date':day.isoformat(),'departure_time':body.departure_time,'return_time':body.return_time,'office_days':body.office_days,'source_url':'https://www.google.com/maps/dir/?'+urlencode({'api':1,'origin':prop.get('address') or prop['name']+' '+body.city,'destination':body.destination,'travelmode':'driving' if body.travel_mode=='two_wheeler' else body.travel_mode}),'retrieved_at':stamp(),'is_demo':False}

    async def overview(self,prop,body):
        warnings=[];result={'images':prop.get('images',[]),'reviews':[],'review_topics':[],'commute':None,'property_facts':{},'warnings':warnings}
        async def details():
            try:
                if prop.get('property_token'):
                    p=await self.search('google_hotels',q=prop['name'],property_token=prop['property_token'],gl='in',currency='INR',check_in_date=body.check_in.isoformat(),check_out_date=body.check_out.isoformat(),adults=body.occupants,ttl=600)
                    result['property_facts']={k:p.get(k) for k in ('address','phone','description','amenities','check_in_time','check_out_time') if p.get(k)}
                    result['images']=[{'url':u,'kind':'hotel_photo','caption':'Hotel photo; available room may differ'} for im in p.get('images',[])[:8] if isinstance(im,dict) and (u:=safe_url(im.get('original_image') or im.get('thumbnail')))] or result['images']
                elif prop.get('place_id') or prop.get('data_id'):
                    params={'place_id':prop['place_id']} if prop.get('place_id') else {'data_cid':str(int(prop['data_id'].split(':')[-1],16))}
                    p=await self.search('google_maps',**params,gl='in',ttl=3600)
                    place=p.get('place_results') or {}
                    result['property_facts']={k:place.get(k) for k in ('address','phone','website','description','hours','extensions') if place.get(k)}
            except (ProviderError,ValueError,KeyError) as exc:warnings.append('Some place details are unavailable. Confirm with the provider.')
        async def photos():
            if not prop.get('data_id'):return
            try:
                p=await self.search('google_maps_photos',data_id=prop['data_id'],ttl=86400)
                images=[{'url':u,'kind':'place_photo','caption':'Place photo; not a verified available room'} for im in p.get('photos',[])[:8] if (u:=safe_url(im.get('image') or im.get('thumbnail')))]
                if images:result['images']=images
            except ProviderError:warnings.append('Additional photos are unavailable.')
        async def reviews():
            if not (prop.get('place_id') or prop.get('data_id')):return
            try:
                params={'place_id':prop['place_id']} if prop.get('place_id') else {'data_id':prop['data_id']}
                p=await self.search('google_maps_reviews',**params,sort_by='newestFirst',ttl=3600)
                for r in p.get('reviews',[])[:12]:
                    text=r.get('snippet') or r.get('text') or ''
                    result['reviews'].append({'text':str(text)[:260],'rating':finite(r.get('rating')),'date':r.get('iso_date') or r.get('date'),'url':safe_url(r.get('link')) or prop['source_url']})
                topics={'Security':['security','guard','cctv'],'Cleanliness':['clean','dirty','hygiene'],'Water':['water','plumbing'],'Maintenance':['maintenance','repair'],'Noise':['noise','noisy'],'Food':['food','meal'],'Deposit':['deposit','refund'],'Transport':['bus','metro','transport']}
                for label,terms in topics.items():
                    count=sum(any(t in r['text'].lower() for t in terms) for r in result['reviews'])
                    if count:result['review_topics'].append({'topic':label,'mentions':count})
            except ProviderError:warnings.append('Reviews are unavailable for this place.')
        async def travel():result['commute']=await self.commute(prop,body)
        await asyncio.gather(details(),photos(),reviews(),travel())
        return result

    async def nearby(self,prop,body):
        point=prop.get('coordinates')
        if not point:return {'places':[],'warnings':['No coordinates available to measure nearby places.']}
        categories={'grocery':'grocery store','pharmacy':'pharmacy','hospital':'hospital','transit':'bus stop metro public transport','petrol':'petrol pump','school':'school','railway':'railway station','airport':'airport'}
        found=[];warnings=[]
        async def category(key,query):
            try:
                p=await self.search('google_maps',q=query+' near me',ll=f"@{point['lat']},{point['lng']},14z",nearby=True,type='search',gl='in',ttl=86400)
                options=[(km(point,c),r) for r in rows(p) if (c:=coords(r))]
                radius=60 if key=='airport' else 20 if key=='railway' else 8 if key=='hospital' else 3
                options=[(d,r) for d,r in options if d<=radius]
                for d,r in sorted(options,key=lambda x:x[0])[:2]:found.append({'category':key,'name':r.get('title',query),'distance_km':d,'distance_kind':'straight_line','rating':finite(r.get('rating')),'url':maps_link(r.get('title',query)+' '+body.city)})
            except ProviderError:warnings.append(f'{key.capitalize()} lookup is currently unavailable.')
        await asyncio.gather(*(category(k,q) for k,q in categories.items() if k!='school' or body.household=='family'))
        return {'places':found,'warnings':warnings,'retrieved_at':stamp()}

    async def area_evidence(self,prop,body):
        results=[]
        try:
            p=await self.search('google',q=f'{prop["area"]} {prop["city"]} local safety advisories crime news',gl='in',num=5,ttl=3600)
            for r in p.get('organic_results',[])[:5]:
                if u:=safe_url(r.get('link')):results.append({'title':r.get('title','Source'),'snippet':r.get('snippet',''),'date':r.get('date'),'url':u,'status':'Search result — relevance and claims need checking'})
        except ProviderError:return {'sources':[],'warning':'Local report search is unavailable. No safety conclusion can be drawn.'}
        return {'sources':results,'summary':'Search results are leads to inspect, not a verified local crime database or a safety verdict.','retrieved_at':stamp()}
