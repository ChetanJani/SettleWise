function browserId() {
  try { let id=localStorage.getItem('sw-browser');if(!id){id=crypto.randomUUID();localStorage.setItem('sw-browser',id)}return id }
  catch { return sessionStorage.getItem('sw-browser') || (()=>{const id=crypto.randomUUID();sessionStorage.setItem('sw-browser',id);return id})() }
}
export const clientId=browserId();
export async function api(path, options={}) {
  const response=await fetch(`/api${path}`,{...options,headers:{'Content-Type':'application/json','X-Client-Id':clientId,...options.headers}});
  const data=await response.json().catch(()=>({detail:'The local backend did not respond. Check that it is running.'}));
  if(!response.ok){const detail=Array.isArray(data.detail)?data.detail.map(x=>x.msg).join(' '):data.detail;throw new Error(detail || 'Something went wrong. Please try again.')}
  return data;
}
export const post=(path,body,signal)=>api(path,{method:'POST',body:JSON.stringify(body),signal});
export const money=v=>typeof v==='number'?new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(v):'Price to confirm';
export const typeLabel={any:'Any type',flat:'Flat',pg:'PG',hostel:'Hostel',hotel:'Hotel',house:'House',other:'Accommodation'};
export const modeLabel={transit:'Public transport',driving:'Car',two_wheeler:'Two-wheeler',walking:'Walking',cycling:'Bicycle'};
export function dateLabel(value){if(!value)return 'Date not provided';const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}
export function safeLink(value){try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&!url.username?url.href:null}catch{return null}}
export function loadLocal(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}}
export function saveLocal(key,value){try{localStorage.setItem(key,JSON.stringify(value))}catch{/* Device storage may be disabled; current session still works. */}}
export const defaults={area:'',city:'Ahmedabad',destination:'',mode:'live',property_type:'any',budget:null,strict_budget:true,household:'solo',occupants:1,gender_requirement:'any',bedrooms:null,amenities:[],priority:'balanced',travel_mode:'transit',departure_time:'09:00',return_time:'18:00',office_days:22,max_commute:null,check_in:null,check_out:null,sort:'match'};
