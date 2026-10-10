"""Explicit fictional hackathon scenarios; never calls the provider."""
import hashlib
import math
from copy import deepcopy
from .provider import stamp,km
from .evidence import review_safety

NAMES={
 'flat':['The Courtyard Residence','The Quiet Corner','The Window Studio','Sage Park Apartments','Maple One','The Terrace Loft','Ivory Court','Juniper Heights','Cedar Grove','The Sunlit Apartment'],
 'pg':['Aster Living PG','Willow Women’s PG','Cedar Men’s PG','Olive Co-living','The Study House PG','Ivy Women’s Residence','Northstar Men’s PG','Sage Social Living','Bloom Women’s PG','Maple Co-living'],
 'hostel':['Olive Student Hostel','The Campus Nest','Willow Women’s Hostel','Cedar Men’s Hostel','The Reading Room','Juniper Student House','Northstar Women’s Hostel','Sage Men’s Hostel','The Commons Hostel','Bloom Student Living'],
 'house':['The Garden House','The Cedar Bungalow','Willow Courtyard','The Palm Villa','Sage Family Home','Maple Garden Villa','The Ivy House','Juniper Cottage','Olive Terrace House','The Sunlit Bungalow'],
 'hotel':['The Ivory Hotel','Sage Boutique Stay','Cedar Business Hotel','The Courtyard Suites','Willow City Hotel','Maple Comfort Inn','The Palm Retreat','Juniper Studio Suites','Olive Urban Hotel','The Terrace Hotel']}
PRICES={'flat':[16500,18500,14500,24000,21000,28500,17500,32000,26500,19500],'pg':[12500,14000,8500,11500,7500,16000,9500,13500,10500,15000],
 'hostel':[6500,7200,8500,5800,9500,6800,10500,7500,6200,9000],'house':[28000,35000,42000,55000,32000,48000,38000,26000,45000,36000],
 'hotel':[2200,3400,1800,4500,2800,1600,5200,3600,2400,4100]}
GENDERS={'pg':['any','women','men','any','men','women','men','any','women','any'],'hostel':['any','men','women','men','any','any','women','men','any','women']}
POSITIVE=['Safe entry with helpful guards, including for women returning in the evening.','The building feels secure and has good security at the gate.','Well-lit access made the last part of my walk feel safe.','CCTV and helpful guards made the shared entrance feel secure.']
NEGATIVE=['Poor lighting on the side street made the last walk feel unsafe.','No guards at the rear entrance; security needs improvement.','The dark street felt unsafe when I returned late.']

def demo_reviews(index):
    positives=[11,10,9,8,10,7,9,6,8,10][index]
    return [{'text':f'Example resident {n+1}: '+(POSITIVE[n%4] if n<positives else NEGATIVE[n%3]),'rating':5 if n<positives else 3,'date':f'2026-10-{1+n%8:02}','url':None,'is_demo':True} for n in range(12)]

def demo_properties(area,city):
    items=[];suffix=hashlib.sha256((area+'|'+city).encode()).hexdigest()[:8]
    for index in range(10):
        for category,kind in enumerate(('flat','pg','hostel','house','hotel')):
            price=PRICES[kind][index];reviews=demo_reviews(index)
            beds=([1,2,0,3,2,2,1,3,2,1][index] if kind=='flat' else [3,3,4,4,2,4,3,2,3,3][index] if kind=='house' else None)
            capacity=(max(2,(beds or 1)*2) if beds is not None else [1,2,3,2,4,1,2,3,2,1][index] if kind in ('pg','hostel') else [2,2,2,4,2,2,4,3,2,4][index])
            amenities=(['kitchen','parking','furnished','security','lift'] if kind=='flat' else ['kitchen','parking','pets','furnished','security'] if kind=='house' else ['food','furnished','security'] if kind in ('pg','hostel') else ['furnished','parking','security','accessible'])
            if index in (5,7):amenities=[a for a in amenities if a not in ('security','parking')]
            scenes=([1,2,3,4,5] if kind=='flat' else [6,7,8,9,10] if kind=='house' else [11,12,13,14,15] if kind=='hotel' else [16,17,18,19,20])
            images=[{'url':f'/demo-photos/scene-{scenes[(index+n)%5]:02}.jpg','kind':'illustrative_stock','caption':'Illustrative stock scene, not this fictional property'} for n in range(3)]
            score={**review_safety(reviews),'is_demo':True}
            items.append({'id':f'demo-v2-{kind}-{index+1}-{suffix}','name':NAMES[kind][index],'type':kind,'discovery_types':[kind],'area':area,'city':city,
                'address':f'Example Block {chr(65+index)}, {area}','coordinates':{'lat':23.041,'lng':72.554},'price':price,'price_unit':'night' if kind=='hotel' else 'month',
                'deposit':0 if kind=='hotel' else price*(1 if kind in ('pg','hostel') else 2),'maintenance':800+index*100 if kind in ('flat','house') else 0,
                'bedrooms':beds,'bathrooms':max(1,(beds or 1)-1),'occupancy':capacity,'sharing':('Single room' if capacity==1 else f'{capacity}-person sharing') if kind in ('pg','hostel') else 'Private room' if kind=='hotel' else 'Entire home',
                'gender_restriction':GENDERS[kind][index] if kind in GENDERS else None,'amenities':amenities,'furnishing':'Furnished','ventilation':'Cross ventilation with opening windows' if index%2==0 else 'Window ventilation with natural light',
                'rating':round(sum(r['rating'] for r in reviews)/len(reviews),1),'review_count':len(reviews),'images':images,'source_kind':'demo','source_name':'Fictional example','source_url':None,
                'listing_status':'Fictional property — not available to book','verified':False,'is_demo':True,'last_updated':stamp(),
                'description':f'Fictional {kind} scenario for comparing cost, commute and everyday convenience. Photos are illustrative stock scenes.',
                'security_facts':{'cctv':index!=7,'guard':index not in (5,7),'access_control':index!=5,'lighting':index not in (3,7)},'security_source':'Fictional demonstration scenario',
                'reviews':reviews,'review_safety':score,'details':{'reviews-v2':{'reviews':reviews,'review_safety':score}},
                '_demo_index':index,'_demo_radius_km':.28+index*.24+category*.08,'_demo_bearing':index*137.5+category*47})
    return items

def position_demo(prop,centre):
    angle=math.radians(prop['_demo_bearing']);radius=prop['_demo_radius_km']
    lat=max(-89,min(89,centre['lat']+radius*math.cos(angle)/111.195))
    lng=(centre['lng']+radius*math.sin(angle)/(111.195*max(.02,math.cos(math.radians(centre['lat']))))+180)%360-180
    prop['coordinates']={'lat':lat,'lng':lng};prop['area_distance_km']=km(centre,prop['coordinates'])

def demo_commute(prop,body):
    if not body.destination:return None
    road=round(prop.get('area_distance_km',prop.get('_demo_radius_km',1))*1.3,2)
    speed,overhead={'walking':(4.8,0),'cycling':(12,0),'driving':(20,2),'two_wheeler':(24,1),'transit':(12,5)}[body.travel_mode]
    morning=max(2,round(road/speed*60+overhead));evening=max(2,round(morning*(1.18 if body.travel_mode in ('driving','two_wheeler','transit') else 1)))
    return {'morning':{'minutes':morning,'distance_km':road},'evening':{'minutes':evening,'distance_km':road},'mode':body.travel_mode,'date':None,'departure_time':body.departure_time,'return_time':body.return_time,'office_days':body.office_days,'source_url':None,'retrieved_at':stamp(),'is_demo':True}

def demo_nearby(prop,body):
    services=[('Metro stop','Public transport',.32),('Daily Grocer','Grocery',.18),('Care Pharmacy','Pharmacy',.24),('City Care Hospital','Hospital',1.1),('Fuel station','Petrol pump',.85),('Neighbourhood Café','Food',.35)]
    if body.household=='family':services.append(('Learning Grove School','School',.7))
    return {'places':[{'name':'Example '+name,'category':kind,'distance_km':round(distance+prop['_demo_index']*.03,2),'url':None,'is_demo':True} for name,kind,distance in services],'warnings':['Fictional nearby services; distances are illustrative.'],'is_demo':True}

def demo_overview(prop,body):
    return {'images':deepcopy(prop['images']),'reviews':deepcopy(prop['reviews']),'review_safety':deepcopy(prop['review_safety']),'commute':demo_commute(prop,body),
            'property_facts':{'description':prop['description'],'bedrooms':prop['bedrooms'],'occupancy':prop['occupancy'],'security_facts':prop['security_facts']},'warnings':['Fictional properties, reviews and route estimates. Illustrative stock photos.'],'is_demo':True}

def demo_details(prop,body,section):
    if section in ('overview','place'):return demo_overview(prop,body)
    if section=='photos':return {'images':deepcopy(prop['images']),'is_demo':True}
    if section=='reviews':return {'reviews':deepcopy(prop['reviews']),'review_safety':deepcopy(prop['review_safety']),'is_demo':True}
    if section=='commute':return {'commute':demo_commute(prop,body),'is_demo':True}
    if section=='nearby':return demo_nearby(prop,body)
    return {'sources':[],'summary':'Illustrative scenario: inspect lighting, access controls and last-mile transport. No real incidents or news reports are asserted.','is_demo':True}
