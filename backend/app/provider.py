"""SerpApi adapters with bounded concurrency and no fabricated live fields."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import math
import re
import time
from .cache import SearchCache
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
    text=str(title).lower()
    men=bool(re.search(r'\b(boys|men only|male only|gents)\b',text))
    women=bool(re.search(r'\b(girls|women only|female only|ladies)\b',text))
    p['gender_restriction']='any' if men and women else 'men' if men else 'women' if women else None
    p['gender_source']='Place name — verify eligibility' if men or women else None
    if p['type']=='hotel':p['price_unit']='night'
    return p

class SerpApi:
    def __init__(self,key,cache_path=None,daily_limit=30):
        self.key=key;self.cache={};self.locks={};self.sem=asyncio.Semaphore(3)
        self.http=httpx.AsyncClient(timeout=httpx.Timeout(22,connect=8))
        self.request_count=0
        self.cache_hits=0
        self.disk=SearchCache(cache_path,daily_limit) if cache_path else None

    async def close(self):await self.http.aclose()

    async def search(self,engine,ttl=86400,**params):
        query={'engine':engine,'hl':'en',**{k:v for k,v in params.items() if v is not None}}
        ck=hashlib.sha256(json.dumps(query,sort_keys=True).encode()).hexdigest()
        cached=self.cache.get(ck)
        if cached and time.monotonic()-cached[0]<ttl:self.cache_hits+=1;return deepcopy(cached[1])
        # Per-query locks prevent identical in-flight searches consuming extra credits.
        lock=self.locks.setdefault(ck,asyncio.Lock())
        async with lock:
            cached=self.cache.get(ck)
            if cached and time.monotonic()-cached[0]<ttl:self.cache_hits+=1;return deepcopy(cached[1])
            if self.disk:
                disk=await asyncio.to_thread(self.disk.get,ck)
                if disk is not None:
                    self.cache_hits+=1;self.cache[ck]=(time.monotonic(),deepcopy(disk));return disk
            async with self.sem:
                if not self.key:raise ProviderError('Live search needs a SerpApi key in backend/.env.')
                if self.disk and not await asyncio.to_thread(self.disk.reserve):raise ProviderError('Local daily search limit reached. Cached results and filters still work.')
                try:
                    self.request_count+=1
                    response=await self.http.get('https://serpapi.com/search.json',params={**query,'api_key':self.key})
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
            payload.pop('search_metadata',None)
            if self.disk:await asyncio.to_thread(self.disk.put,ck,payload,ttl)
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

    async def autocomplete(self,q,city='Worldwide'):
        payload=await self.search('google_maps_autocomplete',q=q,ll='@0,0,3z',ttl=604800)
        result=[];seen=set()
        for row in (payload.get('suggestions') or [])[:12]:
            if isinstance(row,str):row={'value':row}
            if not isinstance(row,dict):continue
            name=row.get('value') or row.get('title') or row.get('text')
            if not isinstance(name,str):continue
            address=str(row.get('subtext') or '')[:240]
            key=(name.casefold(),address.casefold())
            if key in seen:continue
            seen.add(key)
            point=coords({'gps_coordinates':{'latitude':row.get('latitude'),'longitude':row.get('longitude')}})
            result.append({'text':name[:160],'address':address,'coordinates':point,'type':row.get('type','place')})
        return result

    async def discover(self,body):
        centre=body.location.model_dump() if body.location else await self.resolve(body.area,body.city)
        if not centre:raise ProviderError('Choose a more specific place or include its city.')
        context=f'{body.location.name}, {body.location.address}'.strip(', ') if body.location else body.area if body.city=='Worldwide' else f'{body.area}, {body.city}'
        types=body.property_types or (['flat','pg','hostel','hotel','house'] if body.property_type=='any' else [body.property_type])
        terms={'pg':'paying guest PG','hostel':'hostels','hotel':'hotels','flat':'apartments flats','house':'rental houses villas'}
        # One combined discovery query returns the selected accommodation types.
        payload=await self.search('google_maps',q=' '.join(terms[t] for t in types)+' near '+context,type='search',ll=f"@{centre['lat']},{centre['lng']},14z")
        items=[];seen=set()
        for row in rows(payload):
            item=base_property(row,body.area,body.city);point=item['coordinates']
            if not point or km(centre,point)>12 or item['id'] in seen:continue
            if item['type'] not in types and item['type']!='other':continue
            seen.add(item['id']);item['area_distance_km']=km(centre,point)
            items.append(item)
        return centre,items[:40],[]

    async def photos(self,prop,body=None):
        if not prop.get('data_id'):return {'images':prop.get('images',[])}
        payload=await self.search('google_maps_photos',data_id=prop['data_id'],ttl=604800)
        images=[{'url':u,'kind':'place_photo','caption':'Source photo; available room may differ'} for row in payload.get('photos',[])[:10] if isinstance(row,dict) and (u:=safe_url(row.get('image') or row.get('thumbnail')))]
        return {'images':images or prop.get('images',[])}

    async def reviews_only(self,prop,body=None):
        if not (prop.get('place_id') or prop.get('data_id')):return {'reviews':[]}
        params={'place_id':prop['place_id']} if prop.get('place_id') else {'data_id':prop['data_id']}
        payload=await self.search('google_maps_reviews',**params,sort_by='newestFirst',ttl=86400)
        return {'reviews':[{'text':str(r.get('snippet') or r.get('text') or '')[:260],'rating':finite(r.get('rating')),'date':r.get('iso_date') or r.get('date'),'url':safe_url(r.get('link')) or prop['source_url']} for r in payload.get('reviews',[])[:10]]}

    async def place_only(self,prop,body=None):
        if not (prop.get('place_id') or prop.get('data_id')):return {'property_facts':{}}
        params={'place_id':prop['place_id']} if prop.get('place_id') else {'data_cid':str(int(prop['data_id'].split(':')[-1],16))}
        payload=await self.search('google_maps',**params,ttl=86400)
        row=payload.get('place_results') or {}
        return {'property_facts':{k:row[k] for k in ('address','phone','website','description','hours','extensions') if row.get(k)}}

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
        if not point:return {'places':[],'warnings':['Location unavailable.']}
        labels={'grocery':('grocery','supermarket'),'pharmacy':('pharmacy','medical shop'),'hospital':('hospital',),'transit':('bus stop','metro station'),'petrol':('petrol','gas station'),'railway':('railway station','train station'),'airport':('airport',)}
        if body.household=='family':labels['school']=('school',)
        payload=await self.search('google_maps',q='grocery pharmacy hospital petrol public transport '+('school ' if body.household=='family' else '')+'near '+(prop.get('address') or prop['name']),ll=f"@{point['lat']},{point['lng']},14z",type='search',ttl=86400)
        found=[]
        for row in rows(payload):
            coordinate=coords(row)
            if not coordinate:continue
            text=(str(row.get('title',''))+' '+str(row.get('type',''))).lower()
            category=next((k for k,terms in labels.items() if any(term in text for term in terms)),None)
            if category and km(point,coordinate)<=8:found.append({'category':category,'name':row.get('title'),'distance_km':km(point,coordinate),'distance_kind':'straight_line','url':maps_link(row.get('title','')+' '+body.city)})
        return {'places':sorted(found,key=lambda x:x['distance_km'])[:12],'warnings':[],'retrieved_at':stamp()}

    async def area_evidence(self,prop,body):
        results=[]
        try:
            p=await self.search('google',q=f'{prop["area"]} {prop["city"]} local safety advisories crime news',gl='in',num=5,ttl=3600)
            for r in p.get('organic_results',[])[:5]:
                if u:=safe_url(r.get('link')):results.append({'title':r.get('title','Source'),'snippet':r.get('snippet',''),'date':r.get('date'),'url':u,'status':'Search result — relevance and claims need checking'})
        except ProviderError:return {'sources':[],'warning':'Local report search is unavailable. No safety conclusion can be drawn.'}
        return {'sources':results,'summary':'Search results are leads to inspect, not a verified local crime database or a safety verdict.','retrieved_at':stamp()}
