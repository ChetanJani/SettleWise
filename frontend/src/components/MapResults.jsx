import {useEffect,useRef} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {money,typeLabel} from '../lib/api';
export default function MapResults({properties,centre,onSelect,highlighted}){
  const element=useRef(null),instance=useRef(null),layer=useRef(null),markers=useRef({});const select=useRef(onSelect);select.current=onSelect;
  useEffect(()=>{
    const map=L.map(element.current,{zoomControl:false,scrollWheelZoom:false}).setView([centre?.lat??23.04,centre?.lng??72.55],13);
    L.control.zoom({position:'bottomright'}).addTo(map);
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',maxZoom:19}).addTo(map);
    instance.current=map;layer.current=L.layerGroup().addTo(map);
    const observer=new ResizeObserver(()=>map.invalidateSize());observer.observe(element.current);
    return()=>{observer.disconnect();tiles.off();map.remove();instance.current=null};
  },[]);
  useEffect(()=>{
    const map=instance.current;if(!map)return;layer.current.clearLayers();markers.current={};const points=[];
    for(const p of properties){const c=p.coordinates;if(!c||!Number.isFinite(c.lat)||!Number.isFinite(c.lng))continue;
      const label=p.price!=null?money(p.price):typeLabel[p.type]||'Place';const marker=L.marker([c.lat,c.lng],{icon:L.divIcon({className:'price-marker',html:`<span>${label}</span>`,iconSize:[80,30],iconAnchor:[40,15]})}).addTo(layer.current);
      marker.on('click',()=>select.current(p));markers.current[p.id]=marker;points.push([c.lat,c.lng]);
    }
    if(centre){L.circleMarker([centre.lat,centre.lng],{radius:6,color:'#145c45',weight:2,fillColor:'#fff',fillOpacity:1}).bindTooltip('Your selected area').addTo(layer.current);points.push([centre.lat,centre.lng])}
    if(points.length)map.fitBounds(L.latLngBounds(points),{padding:[45,45],maxZoom:14,animate:false});
  },[properties,centre]);
  useEffect(()=>{for(const [id,marker]of Object.entries(markers.current)){const el=marker.getElement();el?.classList.toggle('highlighted',id===highlighted)}},[highlighted]);
  return <div className="map-canvas" ref={element} aria-label="Map of property locations"><span className="map-caption">{properties.some(p=>p.is_demo)?'Example pins · fictional properties':'Place locations · confirm the exact available unit'}</span></div>;
}
