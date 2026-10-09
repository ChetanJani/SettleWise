export const accommodationTypes=['pg','hostel','hotel','flat','house'];
export const evidenceMeaning='Documentation coverage for CCTV, guard, controlled entry and lighting. It measures available answers, not personal safety. An absent feature can still have a documented answer.';
export function safetyEvidence(p){
  const facts=p.security_facts||{},keys=['cctv','guard','access_control','lighting'];
  const documented=keys.filter(k=>typeof facts[k]==='boolean');
  return {score:documented.length?documented.length/4*100:null,documented,features:facts};
}
export function routeKey(f){return [f.area,f.location?.lat,f.location?.lng,f.travel_mode,f.departure_time,f.return_time].join('|')}
export function activeCommute(p,f){return p.routes?.[routeKey(f)]||null}
export function rankLocal(candidates,f){
  const known=[],unknown=[];let excluded=0;
  const priceRefs={month:Math.min(...candidates.filter(p=>p.price_unit!=='night'&&p.price>0).map(p=>p.price)),night:Math.min(...candidates.filter(p=>p.price_unit==='night'&&p.price>0).map(p=>p.price))};
  const personalised=!!(f.budget||f.hotel_budget||f.gender_requirement!=='any'||f.occupants>1||f.bedrooms!=null||f.amenities.length||f.max_commute||f.priority!=='balanced');
  for(const raw of candidates){
    const p={...raw},missing=[],reasons=[],tradeoffs=[];let fails=false;
    if(!f.property_types.includes(p.type)&&p.type!=='other'){excluded++;continue}
    if(p.type==='other'&&f.property_types.length!==5)missing.push('Type unknown');
    if(f.photos_only&&!p.images?.length){excluded++;continue}
    if(f.radius_km&&(p.area_distance_km==null||p.area_distance_km>f.radius_km)){excluded++;continue}
    const budget=p.price_unit==='night'?f.hotel_budget:f.budget;
    if(budget){if(p.price==null)missing.push('Price unavailable');else if(p.price>budget){if(f.strict_budget)fails=true;else tradeoffs.push('Above budget')}else reasons.push('Within budget')}
    if(f.occupants>1){if(p.occupancy==null)missing.push('Capacity unknown');else if(p.occupancy<f.occupants)fails=true;else reasons.push(`Fits ${f.occupants} people`)}
    if(f.gender_requirement!=='any'&&['pg','hostel'].includes(p.type)){
      const g=p.gender_restriction;
      if(f.gender_requirement==='unknown'){if(g!=null)fails=true}
      else if(g==null)missing.push('Eligibility unknown');
      else if(f.gender_requirement==='both'?g!=='any':![f.gender_requirement,'any'].includes(g))fails=true;
    }
    if(f.bedrooms!=null&&['flat','house'].includes(p.type)){if(p.bedrooms==null)missing.push('BHK unavailable');else if(p.bedrooms<f.bedrooms)fails=true}
    for(const a of f.amenities){if(p.amenities?.includes(a))reasons.push(a);else if(p.is_demo||p.source_kind==='owner_listing')fails=true;else missing.push(`${a} unknown`)}
    const commute=activeCommute(p,f),out=commute?.morning?.minutes,back=commute?.evening?.minutes;
    if(f.max_commute){if(out==null||back==null)missing.push('Route not loaded');else if(Math.max(out,back)>f.max_commute)fails=true}
    if(fails||(missing.length&&f.known_only)){excluded++;continue}
    const weights={balanced:[35,45,20],cost:[70,20,10],commute:[15,75,10],space:[20,20,60],security:[30,50,20]}[f.priority]||[35,45,20];
    const parts=[];
    if(p.price!=null)parts.push([Math.min(100,100*priceRefs[p.price_unit==='night'?'night':'month']/Math.max(1,p.price)),weights[0]]);
    if(f.priority==='commute'){if(out!=null&&back!=null)parts.push([Math.max(0,100-(out+back)/2/90*100),weights[1]])}
    else if(p.area_distance_km!=null)parts.push([Math.max(0,100-p.area_distance_km/12*100),weights[1]]);
    if(f.priority==='space'&&p.occupancy!=null)parts.push([Math.min(100,60+Math.max(0,p.occupancy-f.occupants)*10),weights[2]]);
    p.safety_evidence=safetyEvidence(p);p.commute=commute;
    p.match_score=personalised&&!missing.length&&parts.length?Math.round(parts.reduce((sum,[v,w])=>sum+v*w,0)/parts.reduce((sum,[,w])=>sum+w,0)):null;
    if(f.priority==='security')p.match_score=null; // Evidence completeness must not masquerade as safety quality.
    p.missing=missing;p.match_reasons=reasons;p.tradeoffs=tradeoffs;p.alternative=tradeoffs.length>0;
    p.monthly_cost=p.price!=null&&p.price_unit!=='night'?{total_known:p.price+(p.maintenance||0)}:null;
    (missing.length?unknown:known).push(p);
  }
  const sorts={price:(a,b)=>Number(a.price==null)-Number(b.price==null)||(a.price_unit||'month').localeCompare(b.price_unit||'month')||(a.price||0)-(b.price||0),rating:(a,b)=>Number(a.rating==null)-Number(b.rating==null)||(b.rating||0)-(a.rating||0),distance:(a,b)=>Number(a.area_distance_km==null)-Number(b.area_distance_km==null)||(a.area_distance_km||0)-(b.area_distance_km||0),safety:(a,b)=>Number(a.safety_evidence.score==null)-Number(b.safety_evidence.score==null)||(b.safety_evidence.score||0)-(a.safety_evidence.score||0),commute:(a,b)=>Number(a.commute?.morning?.minutes==null)-Number(b.commute?.morning?.minutes==null)||(a.commute?.morning?.minutes||0)-(b.commute?.morning?.minutes||0)};
  const compare=sorts[f.sort]||((a,b)=>Number(a.alternative)-Number(b.alternative)||Number(a.match_score==null)-Number(b.match_score==null)||(b.match_score||0)-(a.match_score||0)||(a.area_distance_km??Infinity)-(b.area_distance_km??Infinity));
  known.sort(compare);unknown.sort(compare);
  return {properties:known,unconfirmed:unknown,excluded_count:excluded,best_id:known.find(p=>p.match_score!=null&&!p.alternative)?.id,personalised};
}
