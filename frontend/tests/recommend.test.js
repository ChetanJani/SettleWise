import test from 'node:test';
import assert from 'node:assert/strict';
import {rankLocal,safetyEvidence,routeKey} from '../src/lib/recommend.js';
const defaults={area:'Office',location:{lat:23,lng:72},property_types:['pg','hostel','hotel','flat','house'],gender_requirement:'any',occupants:1,bedrooms:null,amenities:[],priority:'balanced',strict_budget:true,travel_mode:'transit',departure_time:'09:00',return_time:'18:00',sort:'match'};
const place=(id,props={})=>({id,name:id,type:'pg',price:null,price_unit:'month',area_distance_km:1,amenities:[],gender_restriction:null,...props});
test('monthly and nightly budgets stay separate; unknown is not confirmed',()=>{
 const result=rankLocal([place('cheap',{price:9000}),place('expensive',{price:16000}),place('unknown'),place('hotel',{type:'hotel',price:2000,price_unit:'night'})],{...defaults,budget:10000,hotel_budget:2500});
 assert.deepEqual(result.properties.map(p=>p.id).sort(),['cheap','hotel']);assert.equal(result.unconfirmed[0].id,'unknown');assert.equal(result.excluded_count,1);
});
test('female eligibility includes mixed, rejects male, flags unknown',()=>{
 const result=rankLocal([place('women',{gender_restriction:'women'}),place('mixed',{gender_restriction:'any'}),place('men',{gender_restriction:'men'}),place('unknown')],{...defaults,gender_requirement:'women'});
 assert.deepEqual(result.properties.map(p=>p.id).sort(),['mixed','women']);assert.equal(result.unconfirmed[0].id,'unknown');assert.equal(result.excluded_count,1);
});
test('gender is not applied to flats; BHK is not applied to PGs',()=>{
 assert.equal(rankLocal([place('flat',{type:'flat',bedrooms:2})],{...defaults,gender_requirement:'women'}).properties.length,1);
 assert.equal(rankLocal([place('pg')],{...defaults,bedrooms:2}).properties.length,1);
});
test('only matching travel contexts satisfy a commute limit',()=>{
 const routes={[routeKey(defaults)]:{morning:{minutes:20},evening:{minutes:25}}};
 assert.equal(rankLocal([place('pg',{routes})],{...defaults,max_commute:30}).properties.length,1);
 assert.equal(rankLocal([place('pg',{routes})],{...defaults,max_commute:30,travel_mode:'driving'}).unconfirmed.length,1);
});
test('safety percentage measures documented answers, never stars',()=>{
 assert.equal(safetyEvidence({rating:5}).score,null);
 assert.equal(safetyEvidence({security_facts:{cctv:true,guard:false}}).score,50);
 const result=rankLocal([place('unknown',{rating:5}),place('documented',{security_facts:{guard:false}})],{...defaults,sort:'safety'});
 assert.equal(result.properties[0].id,'documented');
});
test('type, radius, photos and known-only use collected data',()=>{
 const items=[place('pg',{images:[{url:'https://example.com/source.jpg'}]}),place('hotel',{type:'hotel',area_distance_km:5})];
 assert.equal(rankLocal(items,{...defaults,property_types:['pg'],photos_only:true,radius_km:2}).properties.length,1);
 assert.equal(rankLocal(items,{...defaults,budget:10000,hotel_budget:1000,known_only:true}).properties.length,0);
});
