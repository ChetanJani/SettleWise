import {useState,useEffect,useRef} from 'react';
import {MapPin,Building2,ArrowRight,LoaderCircle,Globe2} from 'lucide-react';
import {api} from '../lib/api';

function LocationField({value,onChange,onSelect,label,placeholder,city,live,icon:Icon,required=false,id}){
  const [suggestions,setSuggestions]=useState([]),[focused,setFocused]=useState(false),[active,setActive]=useState(-1),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const requestId=useRef(0),skip=useRef(false);
  useEffect(()=>{if(active>=0)document.getElementById(`${id}-option-${active}`)?.scrollIntoView({block:'nearest'})},[active,id]);
  useEffect(()=>{
    const sequence=++requestId.current;setActive(-1);setSuggestions([]);setLoading(false);setError('');
    if(!live||!focused||value.trim().length<3||skip.current){skip.current=false;return}
    const controller=new AbortController();
    const timer=setTimeout(()=>{
      setLoading(true);
      api(`/autocomplete?q=${encodeURIComponent(value.trim())}&city=${encodeURIComponent(city)}`,{signal:controller.signal})
        .then(d=>{if(sequence===requestId.current)setSuggestions(d.suggestions||[])})
        .catch(e=>{if(e.name!=='AbortError'&&sequence===requestId.current)setError('Suggestions unavailable. Type the full location to search.')})
        .finally(()=>{if(sequence===requestId.current)setLoading(false)});
    },500);
    return()=>{clearTimeout(timer);controller.abort()};
  },[value,city,live,focused]);
  function choose(s){skip.current=true;if(onSelect)onSelect(s);else onChange([s.text,s.address].filter(Boolean).join(', ').slice(0,240));setSuggestions([]);setFocused(false);setLoading(false);setActive(-1)}
  const expanded=focused&&(suggestions.length>0||loading||error);
  return <label className="location-field" htmlFor={id}><span>{label}</span><div className="location-input"><Icon size={19}/><input id={id} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} maxLength={required?160:240} required={required} autoComplete="off" onFocus={()=>setFocused(true)} onBlur={()=>setFocused(false)} role="combobox" aria-expanded={!!expanded} aria-controls={suggestions.length?`${id}-suggestions`:undefined} aria-autocomplete="list" aria-activedescendant={active>=0?`${id}-option-${active}`:undefined} onKeyDown={e=>{
    if(e.key==='ArrowDown'&&suggestions.length){e.preventDefault();setActive(i=>(i+1)%suggestions.length)}
    if(e.key==='ArrowUp'&&suggestions.length){e.preventDefault();setActive(i=>i<=0?suggestions.length-1:i-1)}
    if(e.key==='Enter'&&active>=0&&suggestions[active]){e.preventDefault();choose(suggestions[active])}
    if(e.key==='Escape'){e.preventDefault();setSuggestions([]);setFocused(false)}
  }}/>{loading&&<LoaderCircle className="spin location-loading" size={15}/>}</div>{expanded&&<div className="suggestions"><div className="suggestions-heading"><Globe2 size={12}/><span>Places worldwide</span></div>{loading?<p className="suggestions-status" role="status">Finding places…</p>:error?<p className="suggestions-status" role="status">{error}</p>:<div id={`${id}-suggestions`} role="listbox" aria-label="Location suggestions">{suggestions.map((s,i)=><button key={`${s.text}-${s.address}-${i}`} id={`${id}-option-${i}`} type="button" role="option" aria-selected={active===i} className={active===i?'active':''} onMouseDown={e=>e.preventDefault()} onClick={()=>choose(s)}><MapPin size={16}/><span className="suggestion-copy"><strong>{s.text}</strong>{s.address&&<small>{s.address}</small>}</span></button>)}</div>}</div>}</label>;
}

export default function DestinationSearch({preferences,onSearch,busy,compact=false,live}){
  const [area,setArea]=useState(preferences.area),[destination,setDestination]=useState(preferences.destination),[city,setCity]=useState(preferences.city),[location,setLocation]=useState(preferences.location||null);
  const areaId=compact?'result-area':'search-area';
  useEffect(()=>{setArea(preferences.area);setDestination(preferences.destination);setCity(preferences.city);setLocation(preferences.location||null)},[preferences.area,preferences.destination,preferences.city,preferences.location]);
  function chooseArea(s){
    setArea(s.text);
    if(s.coordinates){setLocation({name:s.text,address:s.address||'',...s.coordinates});setCity((s.address||s.text).slice(0,80))}
    else{setLocation(null);setCity('Worldwide');setArea([s.text,s.address].filter(Boolean).join(', ').slice(0,160))}
  }
  function editArea(v){setArea(v);if(location){setLocation(null);setCity('Worldwide')}}
  const cities=['Worldwide','Ahmedabad','Bengaluru','Mumbai','Pune','Delhi','Hyderabad','Chennai','Jaipur'];
  return <form className={`destination-search ${compact?'compact':''}`} onSubmit={e=>{e.preventDefault();onSearch({...preferences,area:area.trim(),destination:destination.trim(),city,location})}}><div className="search-fields"><LocationField id={areaId} label="Preferred area" value={area} onChange={editArea} onSelect={chooseArea} placeholder="Search any area, city or country" city={city} live={live} icon={MapPin} required/><LocationField id={compact?'result-destination':'search-destination'} label="Work or college · optional" value={destination} onChange={setDestination} placeholder="Where do you need to go?" city={city} live={live} icon={Building2}/>{compact&&<button className="primary search-submit" disabled={busy} aria-label="Search places">{busy?<LoaderCircle className="spin" size={19}/>:<ArrowRight size={20}/>}</button>}</div><div className="city-row"><Globe2 size={13}/>{location?<><span className="selected-location-context">{location.address||location.name}</span><button type="button" className="location-change" onClick={()=>{setLocation(null);setCity('Worldwide');setArea('');document.getElementById(areaId)?.focus()}}>Change</button></>:<><label htmlFor={compact?'result-city':'search-city'}>Suggestions near</label><select id={compact?'result-city':'search-city'} value={city} onChange={e=>setCity(e.target.value)}>{[...new Set([city,...cities])].map(c=><option key={c}>{c}</option>)}</select><span className="worldwide-hint">+ worldwide</span></>}</div>{!compact&&<button className="primary find-button" disabled={busy}>{busy?<><LoaderCircle className="spin" size={20}/>Finding nearby places…</>:<>Find my place<ArrowRight size={20}/></>}</button>}</form>;
}
