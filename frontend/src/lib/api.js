function browserId() {
  try {
    let id=localStorage.getItem('sw-browser');
    // Older builds stored this value as a JSON string. Send the identifier without quotes.
    if(id?.startsWith('"')) { try { id=JSON.parse(id); } catch { id=null; } }
    if(typeof id!=='string'||!/^[A-Za-z0-9_-]{8,128}$/.test(id))id=crypto.randomUUID();
    localStorage.setItem('sw-browser',id);
    return id;
  }
  catch { return sessionStorage.getItem('sw-browser') || (()=>{const id=crypto.randomUUID();sessionStorage.setItem('sw-browser',id);return id})() }
}
export const clientId=browserId();
const apiBase=(import.meta.env?.VITE_API_BASE_URL || '').replace(/\/+$/,'');
export async function api(path, options={}) {
  const response=await fetch(`${apiBase}/api${path}`,{...options,headers:{'Content-Type':'application/json','X-Client-Id':clientId,...options.headers}});
  const data=await response.json().catch(()=>({detail:'The service is temporarily unavailable. Please try again.'}));
  if(!response.ok){const detail=Array.isArray(data.detail)?data.detail.map(x=>x.msg).join(' '):data.detail;throw new Error(detail || 'Something went wrong. Please try again.')}
  return data;
}
export const post=(path,body,signal)=>api(path,{method:'POST',body:JSON.stringify(body),signal});
export const money=v=>typeof v==='number'?new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(v):'Not available';
export const typeLabel={any:'Any type',flat:'Flat',pg:'PG',hostel:'Hostel',hotel:'Hotel',house:'House',other:'Accommodation'};
export const modeLabel={transit:'Public transport',driving:'Car',two_wheeler:'Two-wheeler',walking:'Walking',cycling:'Bicycle'};
export function dateLabel(value){if(!value)return 'Date not provided';const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}
export function safeLink(value){try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&!url.username?url.href:null}catch{return null}}
export function loadLocal(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}}
export function saveLocal(key,value){try{localStorage.setItem(key,JSON.stringify(value))}catch{/* Device storage may be disabled; current session still works. */}}
export function incompleteSearch(data){return !!(data?.discovery?.provider_incomplete||data?.discovery?.types?.some(t=>t.request_failed||t.status==='unavailable'))}
export const defaults={area:'',city:'Worldwide',location:null,destination:'',mode:'live',property_type:'any',property_types:['pg','hostel','hotel','flat','house'],budget:null,hotel_budget:null,strict_budget:true,household:'solo',occupants:1,gender_requirement:'any',bedrooms:null,amenities:[],priority:'balanced',travel_mode:'transit',departure_time:'09:00',return_time:'18:00',office_days:22,max_commute:null,radius_km:10,photos_only:false,known_only:false,check_in:null,check_out:null,sort:'match'};
