import {useEffect,useRef} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {money,typeLabel} from '../lib/api';

// DOM text nodes keep provider names safe while preserving the complete name.
function pinIcon(p,zoom){
 const named=zoom>=15,label=document.createElement('span');
 label.className='map-pin-label';label.textContent=named?p.name:p.price!=null?money(p.price):typeLabel[p.type]||'Place';
 label.title=p.name;
 return L.divIcon({className:`price-marker ${named?'named-marker':''}`,html:label,iconSize:null,iconAnchor:[30,16]});
}
export default function MapResults({properties=[],centre,onSelect,highlighted}){
 const element=useRef(null),instance=useRef(null),layer=useRef(null),markers=useRef({}),select=useRef(onSelect),lastBounds=useRef('');useEffect(()=>{select.current=onSelect},[onSelect]);
 useEffect(()=>{
  const map=L.map(element.current,{zoomControl:false,scrollWheelZoom:true}).setView([0,0],2);
  L.control.zoom({position:'bottomright'}).addTo(map);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',maxZoom:19}).addTo(map);
  instance.current=map;layer.current=L.layerGroup().addTo(map);
  const zoom=()=>{for(const {marker,property}of Object.values(markers.current))marker.setIcon(pinIcon(property,map.getZoom()))};map.on('zoomend',zoom);
  const observer=new ResizeObserver(()=>map.invalidateSize());observer.observe(element.current);
  return()=>{observer.disconnect();map.off('zoomend',zoom);map.remove();instance.current=null};
 },[]);
 useEffect(()=>{
  const map=instance.current;if(!map)return;layer.current.clearLayers();markers.current={};const points=[];
  for(const p of properties){const c=p.coordinates;if(!c||!Number.isFinite(c.lat)||!Number.isFinite(c.lng))continue;
   const marker=L.marker([c.lat,c.lng],{title:p.name,alt:p.name,icon:pinIcon(p,map.getZoom()),riseOnHover:true}).addTo(layer.current);
   const tooltip=document.createElement('span');tooltip.textContent=p.name;marker.bindTooltip(tooltip,{direction:'top'});
   marker.on('click',()=>select.current?.(p));markers.current[p.id]={marker,property:p};points.push([c.lat,c.lng]);
  }
  if(centre&&Number.isFinite(centre.lat)&&Number.isFinite(centre.lng)){const label=document.createElement('span');label.textContent=centre.name||'Selected place';L.circleMarker([centre.lat,centre.lng],{radius:7,color:'#145c45',weight:3,fillColor:'#fff',fillOpacity:1}).bindTooltip(label).addTo(layer.current);points.push([centre.lat,centre.lng])}
  const boundsKey=JSON.stringify(points);
  if(points.length&&boundsKey!==lastBounds.current){lastBounds.current=boundsKey;map.fitBounds(L.latLngBounds(points),{padding:[50,50],maxZoom:14,animate:false})}
 },[properties,centre]);
 useEffect(()=>{for(const [id,{marker}]of Object.entries(markers.current))marker.getElement()?.classList.toggle('highlighted',id===highlighted)},[highlighted,properties]);
 return <div className="map-canvas" ref={element} aria-label="Map of property locations"/>;
}
