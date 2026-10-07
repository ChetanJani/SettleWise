from .provider import stamp

def demo_properties(area,city):
    seeds=[('The Courtyard Residence','flat',16500,1,2,['kitchen','parking','furnished','security'],23.042,72.557,18,27),('Aster Living PG','pg',12500,None,1,['food','furnished','security'],23.036,72.548,12,18),('The Quiet Corner','flat',18500,2,4,['kitchen','lift','parking','security'],23.050,72.560,22,31),('Olive Student Hostel','hostel',8500,None,1,['food','furnished'],23.044,72.543,25,35),('The Garden House','house',28000,3,6,['kitchen','parking','pets'],23.049,72.570,32,42),('The Window Studio','flat',14500,0,2,['kitchen','furnished'],23.030,72.556,16,24)]
    items=[]
    for i,(name,kind,price,beds,occupancy,amenities,lat,lng,morning,evening) in enumerate(seeds):
        items.append({'id':f'demo-{i+1}','name':name,'type':kind,'area':area,'city':city,'address':f'Illustrative address in {area}, {city}','coordinates':{'lat':lat,'lng':lng} if city.lower()=='ahmedabad' else None,'price':price,'price_unit':'month','deposit':price*2,'maintenance':1000 if kind in ('flat','house') else 0,'bedrooms':beds,'bathrooms':1,'occupancy':occupancy,'gender_restriction':'any','amenities':amenities,'furnishing':'Furnished' if 'furnished' in amenities else 'Unfurnished','ventilation':'Illustrative: window ventilation','rating':None,'review_count':None,'images':[],'source_kind':'demo','source_name':'Fictional example','source_url':None,'listing_status':'Fictional property — not available to book','verified':False,'is_demo':True,'last_updated':stamp(),'description':'A fictional property used to demonstrate comparison, costs and preferences. This is not a real listing.','_demo_morning':morning,'_demo_evening':evening})
    return items

def demo_commute(prop,body):
    if not body.destination:return None
    return {'morning':{'minutes':prop.get('_demo_morning',20),'distance_km':4.2},'evening':{'minutes':prop.get('_demo_evening',30),'distance_km':4.4},'mode':body.travel_mode,'date':None,'departure_time':body.departure_time,'return_time':body.return_time,'office_days':body.office_days,'source_url':None,'retrieved_at':stamp(),'is_demo':True}

def demo_overview(prop,body):
    return {'images':[],'reviews':[],'review_topics':[],'commute':demo_commute(prop,body),'property_facts':{},'warnings':['Fictional property, costs and route estimates. No real reviews or incidents are asserted.']}
