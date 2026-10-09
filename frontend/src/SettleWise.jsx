import {useState,useEffect,useRef,useMemo,useLayoutEffect} from 'react';
import {House,Heart,SlidersHorizontal,Map,ArrowLeft,Check,ArrowRight,MapPin} from 'lucide-react';
import DestinationSearch from './components/DestinationSearch';
import PropertyCard from './components/PropertyCard';
import Preferences from './components/Preferences';
import Compare from './components/Compare';
import MapResults from './components/MapResults';
import Loading from './components/Loading';
import {api,post,defaults,loadLocal,saveLocal,typeLabel} from './lib/api';
import {rankLocal,routeKey,accommodationTypes} from './lib/recommend';

const WORKSPACE='sw-workspace-v3',SEARCHES='sw-searches-v3';
const restored=loadLocal(WORKSPACE,{});
const initial={...defaults,...restored.preferences,property_types:restored.preferences?.property_types?.length?restored.preferences.property_types:accommodationTypes};
function searchKey(f){return JSON.stringify([f.mode,f.area.trim().toLowerCase(),f.location?.lat,f.location?.lng,[...f.property_types].sort()])}
function sectionKey(section,f){return section==='commute'?`commute|${routeKey(f)}`:section==='nearby'?`nearby|${f.household}`:section}
export default function SettleWise(){
 const [preferences,setPreferences]=useState(initial),[result,setResult]=useState(restored.result||null),[health,setHealth]=useState(null),[view,setView]=useState('explore'),[busy,setBusy]=useState(false),[error,setError]=useState(''),[panel,setPanel]=useState(null),[toast,setToast]=useState('');
 const [saved,setSaved]=useState(()=>loadLocal('sw-saved',[])),[compare,setCompare]=useState([]),[mapVisible,setMapVisible]=useState(false),[highlighted,setHighlighted]=useState(null),[focused,setFocused]=useState(null),[preview,setPreview]=useState(initial.location),[loading,setLoading]=useState({});
 const sequence=useRef(0),controller=useRef(null),timer=useRef(null),pending=useRef(new globalThis.Map());
 const current=useRef({result,preferences,saved});useLayoutEffect(()=>{current.current={result,preferences,saved}},[result,preferences,saved]);
 useEffect(()=>{api('/health').then(h=>{setHealth(h);if(!restored.preferences&&!h.serpapi_configured)setPreferences(p=>({...p,mode:'demo'}))}).catch(()=>setError('Backend unavailable. Start the local services.'));return()=>{controller.current?.abort();clearTimeout(timer.current)}},[]);
 useEffect(()=>{saveLocal(WORKSPACE,{preferences,result})},[preferences,result]);
 useEffect(()=>{saveLocal('sw-saved',saved)},[saved]);
 const candidates=useMemo(()=>result?.candidates||[...(result?.properties||[]),...(result?.unconfirmed||[])],[result]);
 const ranked=useMemo(()=>rankLocal(view==='saved'?saved:candidates,preferences),[candidates,saved,view,preferences]);
 const displayed=useMemo(()=>[...ranked.properties,...ranked.unconfirmed],[ranked]);
 function notify(s){setToast(s);clearTimeout(timer.current);timer.current=setTimeout(()=>setToast(''),3500)}
 function updateProperty(id,patch){
  const merge=p=>p.id===id?{...p,...patch,details:{...p.details,...patch.details},routes:{...p.routes,...patch.routes}}:p;
  setResult(r=>r?{...r,candidates:(r.candidates||[...(r.properties||[]),...(r.unconfirmed||[])]).map(merge)}:r);
  setSaved(s=>s.map(merge));setCompare(s=>s.map(merge));
  const cache=loadLocal(SEARCHES,{});
  for(const entry of Object.values(cache))if(entry.data?.candidates)entry.data.candidates=entry.data.candidates.map(merge);
  saveLocal(SEARCHES,cache);
 }
 async function enrich(p,section,f=current.current.preferences){
  const key=sectionKey(section,f),token=`${p.id}|${key}`;
  const freshest=current.current.result?.candidates?.find(x=>x.id===p.id)||current.current.saved.find(x=>x.id===p.id)||p;
  if(freshest.details?.[key]&&Date.now()-(freshest.details[key].saved_at||0)<86400000)return freshest.details[key];
  if(pending.current.has(token))return pending.current.get(token);
  const seq=sequence.current;
  const request=(async()=>{
   setLoading(s=>({...s,[p.id]:key}));
   try{
    const data=await post(`/properties/${encodeURIComponent(p.id)}/details`,{section,preferences:{...f,mode:p.is_demo?'demo':'live',destination:f.area}});
    const {property,...details}=data;details.saved_at=Date.now();
    if(seq===sequence.current){const patch={details:{[key]:details},detail_error:null};if(data.images)patch.images=data.images;if(data.commute)patch.routes={[routeKey(f)]:data.commute};if(property?.security_facts)patch.security_facts=property.security_facts;updateProperty(p.id,patch)}
    return details;
   }catch(e){if(seq===sequence.current)updateProperty(p.id,{detail_error:e.message});return null}
   finally{pending.current.delete(token);setLoading(s=>{const next={...s};delete next[p.id];return next})}
  })();pending.current.set(token,request);return request;
 }
 async function search(f){
  if(!f.property_types.length)return;
  const seq=++sequence.current;controller.current?.abort();controller.current=new AbortController();setPreferences(f);setPreview(f.location);setView('explore');setError('');setCompare([]);setFocused(null);setPanel(null);
  const cache=loadLocal(SEARCHES,{}),cached=cache[searchKey(f)];
  if(cached&&Date.now()-cached.at<86400000){setResult(cached.data);setBusy(false);notify('Loaded from this device');return}
  setBusy(true);setResult(null);
  try{
   const data=await post('/search',f,controller.current.signal);
   if(seq!==sequence.current)return;
   data.candidates=(data.candidates||[...(data.properties||[]),...(data.unconfirmed||[])]).map(p=>({...p,...(p.is_demo&&p.commute?{routes:{[routeKey(f)]:p.commute}}:{})}));
   setResult(data);setBusy(false);saveLocal(SEARCHES,Object.fromEntries(Object.entries({...cache,[searchKey(f)]:{at:Date.now(),data}}).slice(-6)));
   // Cards render immediately. At most two missing-photo places are enriched afterwards.
   const missing=data.candidates.filter(p=>!p.is_demo&&!p.images?.length&&p.data_id).slice(0,2);
   for(const p of missing){if(seq!==sequence.current)break;await enrich(p,'photos',f)}
  }catch(e){if(e.name!=='AbortError'&&seq===sequence.current)setError(e.message)}finally{if(seq===sequence.current)setBusy(false)}
 }
 function apply(f){setPreferences(f);setPanel(null)}
 function save(p){setSaved(s=>s.some(x=>x.id===p.id)?s.filter(x=>x.id!==p.id):[p,...s]);}
 function toggleType(type){setPreferences(f=>({...f,property_types:type==='all'?accommodationTypes:f.property_types.includes(type)?f.property_types.length===1?f.property_types:f.property_types.filter(t=>t!==type):[...f.property_types,type]}))}
 function toggleCompare(p){setCompare(s=>s.some(x=>x.id===p.id)?s.filter(x=>x.id!==p.id):s.length<4?[...s,p]:s)}
 function selectPin(p){setFocused(p.id);document.getElementById(`card-${p.id}`)?.scrollIntoView({behavior:'smooth',block:'center'})}
 function home(){setView('explore');setResult(null);setCompare([]);setError('');window.scrollTo(0,0)}
 const landing=view==='explore'&&!result&&!busy;
 const filterCount=[preferences.budget,preferences.hotel_budget,preferences.gender_requirement!=='any',preferences.occupants>1,preferences.bedrooms!=null,preferences.amenities.length,preferences.radius_km,preferences.max_commute,preferences.photos_only,preferences.known_only,preferences.priority!=='balanced',preferences.household==='family'].filter(Boolean).length;
 const searchControls=<><DestinationSearch preferences={preferences} onSearch={search} busy={busy} live={preferences.mode==='live'&&health?.serpapi_configured} onLocation={setPreview}/><div className="search-options"><div className="type-options" role="group" aria-label="Accommodation types"><button className={preferences.property_types.length===5?'selected':''} onClick={()=>toggleType('all')} aria-pressed={preferences.property_types.length===5}>All types</button>{accommodationTypes.map(type=><button key={type} className={preferences.property_types.includes(type)?'selected':''} onClick={()=>toggleType(type)} aria-pressed={preferences.property_types.includes(type)}>{typeLabel[type]}</button>)}</div><button className="secondary filters-button" onClick={()=>setPanel('filters')}><SlidersHorizontal size={18}/>Filters{filterCount>0&&<span>{filterCount}</span>}</button></div></>;
 const map=<MapResults properties={displayed} centre={result?.area_location||preview} onSelect={selectPin} highlighted={highlighted||focused}/>;
 return <><header className="site-header"><button className="brand" aria-label="SettleWise home" onClick={home}><span className="brand-symbol"><House size={20}/></span>SettleWise<span className="brand-dot">.</span></button><nav><div className="data-mode"><button className={preferences.mode==='live'?'active':''} onClick={()=>setPreferences(f=>({...f,mode:'live'}))}>Live</button><button className={preferences.mode==='demo'?'active':''} onClick={()=>setPreferences(f=>({...f,mode:'demo'}))}>Example</button></div><button className={view==='saved'?'nav-active':''} onClick={()=>setView(v=>v==='saved'?'explore':'saved')}><Heart size={19}/>Saved{saved.length>0&&<span className="count-badge">{saved.length}</span>}</button></nav></header>
 <main className={landing?'landing':'results-page'}>{landing?<div className="landing-layout"><section className="landing-intro"><span className="eyebrow">YOUR NEXT CHAPTER</span><h1>Find your place.<br/><span>Feel at home.</span></h1><p>Live closer to what matters.</p><div className="landing-search">{searchControls}</div></section><aside className="map-feature"><div className="map-feature-heading"><Map size={21}/><div><h2>Around your world.</h2><p>Explore places on the map.</p></div></div><MapResults properties={[]} centre={preview} onSelect={()=>{}}/><span className="map-hint"><MapPin size={15}/>Choose a place to explore nearby</span></aside></div>:<><div className="results-search">{searchControls}</div><div className="results-heading"><div>{view==='saved'&&<button className="back-link" onClick={()=>setView('explore')}><ArrowLeft size={16}/>Explore</button>}<h1>{view==='saved'?'Your saved places.':busy&&!result?'Finding your place.':`Near ${result?.area||preferences.area}`}</h1><span className="result-count">{busy&&!result?'':`${displayed.length} places`}{result&&view!=='saved'&&` · ${new Date(result.generated_at||'1970-01-01').toLocaleDateString('en-IN',{day:'numeric',month:'short'})}`}</span></div><div className="view-controls"><select aria-label="Sort places" value={preferences.sort} onChange={e=>setPreferences(f=>({...f,sort:e.target.value}))}><option value="match">Best fit</option><option value="distance">Distance</option><option value="price">Price</option><option value="rating">Rating</option><option value="commute">Travel time</option><option value="safety">Safety evidence %</option></select><button className={`secondary mobile-map-button ${mapVisible?'selected':''}`} onClick={()=>setMapVisible(v=>!v)} aria-expanded={mapVisible}><Map size={18}/>{mapVisible?'Hide map':'Map'}</button></div></div>
 {result&&preferences.property_types.some(t=>!result.searched_types?.includes(t))&&<p className="field-note">Search to include newly selected types.</p>}
 <div className={`results-layout ${mapVisible?'map-visible':''}`}><section className="list-column">{busy&&!result?<><Loading label="Finding places nearby"/><div className="property-grid">{[0,1,2,3].map(i=><div className="skeleton-card" key={i}><i/><span/><span/><span/></div>)}</div></>:displayed.length?<div className="property-grid">{displayed.map(p=><PropertyCard key={p.id} property={p} preferences={preferences} saved={saved.some(x=>x.id===p.id)} compared={compare.some(x=>x.id===p.id)} best={p.id===ranked.best_id} focused={focused===p.id} onSave={save} onCompare={toggleCompare} onHover={setHighlighted} onEnrich={enrich} onUpdated={p=>updateProperty(p.id,p)} busySection={loading[p.id]}/>)}</div>:<div className="empty-state"><House size={36}/><h2>{view==='saved'?'Keep your favourites.':'No matching places.'}</h2><p>{view==='saved'?'Tap a heart to save a place.':'Try a wider area or fewer filters.'}</p></div>}</section><aside className="desktop-map"><div className="map-side-heading"><Map size={18}/><strong>Explore the neighbourhood</strong></div>{map}<small className="map-footnote">Zoom in for property names</small></aside></div></>}
 {error&&<p className="search-error" role="alert">{error}</p>}{result?.mode==='demo'&&<p className="field-note">Example data · fictional places, prices and routes</p>}</main>
 <footer className="site-footer"><span>SettleWise.</span><small>Saved on this device · no account needed</small></footer>
 {compare.length>0&&<div className="compare-bar"><span>{compare.length} selected</span><button className="text-button" onClick={()=>setCompare([])}>Clear</button><button className="primary" disabled={compare.length<2} onClick={()=>setPanel('compare')}>Compare<ArrowRight size={17}/></button></div>}
 {toast&&<div className="toast" role="status"><Check size={17}/>{toast}</div>}{panel==='filters'&&<Preferences value={preferences} onApply={apply} onClose={()=>setPanel(null)}/>}{panel==='compare'&&<Compare properties={compare} preferences={preferences} onClose={()=>setPanel(null)}/>}</>;
}
