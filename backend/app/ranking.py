from copy import deepcopy
from .evidence import evidence

WEIGHTS={'balanced':{'cost':35,'commute':30,'space':20,'security':15},'cost':{'cost':60,'commute':20,'space':10,'security':10},'commute':{'cost':20,'commute':60,'space':10,'security':10},'space':{'cost':20,'commute':20,'space':50,'security':10},'security':{'cost':20,'commute':20,'space':10,'security':50}}

def rank(properties,prefs):
    output=[];unknown=[];excluded=0
    prices=[p['price'] for p in properties if isinstance(p.get('price'),(int,float)) and p['price']>0 and (prefs.property_type=='any' or p['type']==prefs.property_type)]
    price_reference=min(prices) if prices else None
    personalised=bool(prefs.budget or prefs.destination or prefs.amenities or prefs.bedrooms is not None or prefs.priority!='balanced' or prefs.occupants>1 or prefs.gender_requirement!='any')
    for raw in properties:
        p=deepcopy(raw);reasons=[];tradeoffs=[];missing=[];hard_failure=False
        p['safety_evidence']=evidence(p)
        if prefs.property_types and p['type'] not in prefs.property_types and p['type']!='other':excluded+=1;continue
        if prefs.photos_only and not p.get('images'):excluded+=1;continue
        if prefs.radius_km and (p.get('area_distance_km') is None or p['area_distance_km']>prefs.radius_km):excluded+=1;continue
        if prefs.property_type!='any' and p['type'] not in (prefs.property_type,'other'):excluded+=1;continue
        if prefs.property_type!='any' and p['type']=='other':missing.append('Accommodation type needs confirmation.')
        price=p.get('price')
        budget=prefs.hotel_budget if p.get('price_unit')=='night' else prefs.budget
        if budget:
            if price is None:missing.append('Price needs confirmation before budget fit can be assessed.')
            elif price>budget:
                if prefs.strict_budget:excluded+=1;continue
                tradeoffs.append(f'₹{price-budget:,} above your budget per {p["price_unit"]}.')
            else:reasons.append('Within your budget')
        if prefs.occupants>1:
            capacity=p.get('occupancy')
            if capacity is None:missing.append('Capacity for your household needs confirmation.')
            elif capacity<prefs.occupants:excluded+=1;continue
            else:reasons.append(f'Space for {prefs.occupants} people')
        if prefs.gender_requirement!='any' and p['type'] in ('pg','hostel'):
            restriction=p.get('gender_restriction')
            if prefs.gender_requirement=='unknown':
                if restriction is not None:excluded+=1;continue
            elif restriction is None:missing.append('Accommodation eligibility needs confirmation.')
            elif prefs.gender_requirement=='both' and restriction!='any':excluded+=1;continue
            elif restriction not in ('any',prefs.gender_requirement):excluded+=1;continue
        if prefs.bedrooms is not None and p['type'] in ('flat','house'):
            if p.get('bedrooms') is None:missing.append('Bedroom count needs confirmation.')
            elif p['bedrooms']<prefs.bedrooms:excluded+=1;continue
        for amenity in prefs.amenities:
            if amenity not in p.get('amenities',[]):
                if p.get('is_demo') or p.get('source_kind')=='owner_listing':hard_failure=True
                else:missing.append(f'{amenity.capitalize()} needs confirmation.')
            else:reasons.append(amenity.capitalize()+' included')
        if hard_failure:excluded+=1;continue
        c=p.get('commute') or {};morning=(c.get('morning') or {}).get('minutes');evening=(c.get('evening') or {}).get('minutes')
        if prefs.max_commute:
            if morning is None or evening is None:missing.append('Both commute estimates are needed to check your limit.')
            elif max(morning,evening)>prefs.max_commute:excluded+=1;continue
        components={};weights=WEIGHTS[prefs.priority].copy()
        if not prefs.destination or prefs.office_days==0:weights['commute']=0
        if prefs.occupants==1 and prefs.bedrooms is None and prefs.priority!='space':weights['space']=0
        if prefs.priority!='security' and 'security' not in prefs.amenities:weights['security']=0
        if price is not None:
            components['cost']=min(100,100*price_reference/price) if price and price_reference else 100
        if morning is not None and evening is not None:
            components['commute']=max(0,100-(morning+evening)/2/90*100)
            reasons.append(f'{morning} min going · {evening} min returning')
        if p.get('occupancy') is not None:components['space']=min(100,60+max(0,p['occupancy']-prefs.occupants)*10)
        if p.get('is_demo') or p.get('source_kind')=='owner_listing':components['security']=100 if 'security' in p.get('amenities',[]) else 0
        available=sum(weights[k] for k in components);total=sum(weights.values())
        coverage=round(100*available/total) if total else 0
        # Unknown hard requirements never become a confident recommendation.
        score=round(sum(components[k]*weights[k] for k in components)/available) if available and not missing and personalised and coverage>=60 else None
        p.update(match_score=score,match_reasons=reasons[:3],tradeoffs=tradeoffs,missing=missing,coverage=coverage,eligible=not missing,alternative=bool(tradeoffs),personalised=personalised,confidence='Example data' if p.get('is_demo') else 'Partial information' if coverage<100 or not p.get('verified') else 'Listing information available')
        if price is not None and p['price_unit']=='month':
            maintenance=p.get('maintenance');p['monthly_cost']={'rent':price,'maintenance':maintenance,'total_known':price+(maintenance or 0),'complete':False,'note':'Known housing cost only. Food, utilities and commute are additional unless explicitly included.'}
            p['initial_housing_cash']=price+(p.get('deposit') or 0)+(maintenance or 0) if p.get('deposit') is not None else None
        if missing and prefs.known_only:excluded+=1;continue
        if missing:unknown.append(p)
        else:output.append(p)
    if prefs.sort=='safety':output.sort(key=lambda p:(p['safety_evidence']['score'] is None,-(p['safety_evidence']['score'] or 0),p['id']))
    elif prefs.sort=='distance':output.sort(key=lambda p:(p.get('area_distance_km') is None,p.get('area_distance_km') or 0,p['id']))
    elif prefs.sort=='price':output.sort(key=lambda p:(p.get('price') is None,p.get('price_unit','month'),p.get('price') or 0,p['id']))
    elif prefs.sort=='rating':output.sort(key=lambda p:(p.get('rating') is None,-(p.get('rating') or 0),p['id']))
    elif prefs.sort=='commute':output.sort(key=lambda p:((p.get('commute') or {}).get('morning',{}).get('minutes') is None,(p.get('commute') or {}).get('morning',{}).get('minutes') or 0,p['id']))
    else:output.sort(key=lambda p:(p.get('alternative',False),p.get('match_score') is None,-(p.get('match_score') or 0),p.get('area_distance_km',0),p['id']))
    best=next((p['id'] for p in output if p.get('match_score') is not None and not p['alternative']),None)
    return {'properties':output,'unconfirmed':unknown,'excluded_count':excluded,'best_id':best,'personalised':personalised,'scoring_note':'Preference fit is a rules-based comparison, not a safety rating or a probability. Unknown requirements are never assumed satisfied.'}
