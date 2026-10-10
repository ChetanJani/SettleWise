import asyncio
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import create_app
from app.models import SearchRequest, ObservationInput
from app.demo import demo_properties
from app.ranking import rank
from app.provider import SerpApi, base_property, safe_url

class FakeProvider:
    def __init__(self):self.discover_calls=0
    async def close(self): pass
    async def autocomplete(self,q,city='Worldwide'):
        return [{'text':'Navrangpura','address':'Ahmedabad, India','coordinates':None}]
    async def discover(self, body):
        self.discover_calls+=1
        p=base_property({'title':'Example PG','place_id':'test','gps_coordinates':{'latitude':23.03,'longitude':72.55}},body.area,body.city)
        return {'lat':23.03,'lng':72.55},[p],[]
    async def overview(self,p,b): return {'images':[],'reviews':[],'commute':None}
    async def place_only(self,p,b):return {'property_facts':{}}
    async def photos(self,p,b):return {'images':[]}
    async def reviews_only(self,p,b):return {'reviews':[]}
    async def nearby(self,p,b): return {'places':[]}
    async def area_evidence(self,p,b): return {'sources':[]}
    async def commute(self,p,b): return None

class RankingTests(unittest.TestCase):
    def setUp(self): self.items=demo_properties('Navrangpura','Ahmedabad')
    def prefs(self,**kw): return SearchRequest(area='Navrangpura',**kw)
    def test_unpersonalised_has_no_best(self): self.assertIsNone(rank(self.items,self.prefs())['best_id'])
    def test_budget_excludes_expensive(self):
        r=rank(self.items,self.prefs(budget=15000));self.assertTrue(all(p['price']<=15000 for p in r['properties']));self.assertGreater(r['excluded_count'],0)
    def test_unknown_price_not_match(self):
        self.items[0]['price']=None;r=rank(self.items[:1],self.prefs(budget=15000));self.assertEqual(len(r['unconfirmed']),1);self.assertIsNone(r['best_id'])
    def test_flexible_alternatives(self): self.assertTrue(any(p['alternative'] for p in rank(self.items,self.prefs(budget=10000,strict_budget=False))['properties']))
    def test_capacity_unknown(self):
        self.items[0]['occupancy']=None;self.assertEqual(len(rank(self.items[:1],self.prefs(occupants=3))['unconfirmed']),1)
    def test_missing_commute_not_zero(self):
        self.assertEqual(len(rank(self.items,self.prefs(destination='Office',max_commute=30))['unconfirmed']),len(self.items))
    def test_lower_cost_scores_better(self):
        r=rank(self.items,self.prefs(priority='cost',budget=100000));prices=[p['price'] for p in r['properties']];self.assertEqual(prices,sorted(prices))
    def test_unknown_gender(self):
        self.items[1]['gender_restriction']=None;self.assertEqual(len(rank(self.items[1:2],self.prefs(gender_requirement='women'))['unconfirmed']),1)
    def test_bad_time(self):
        with self.assertRaises(ValidationError):self.prefs(departure_time='25:90')
    def test_hotels_allow_no_dates(self):
        self.assertIsNone(self.prefs(property_type='hotel').check_in)
    def test_dates_order(self):
        with self.assertRaises(ValidationError):self.prefs(check_in=date.today()+timedelta(days=3),check_out=date.today()+timedelta(days=2))
    def test_no_keys_in_source_url(self): self.assertEqual(safe_url('https://example.com/x?api_key=secret&key=secret&q=home'),'https://example.com/x?q=home')
    def test_reject_unsafe_url(self): self.assertIsNone(safe_url('javascript:alert(1)'))
    def test_no_invented_live_price(self): self.assertIsNone(base_property({'title':'Live PG','price':'₹5000'},'Area','City')['price'])
    def test_no_private_contact_in_observation(self):
        with self.assertRaises(ValidationError):ObservationInput(area='Area',city='City',category='other',sentiment='bad',text='Please contact person@example.com about this')

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=create_app('sqlite:///'+str(Path(self.temp.name)/'test.db'),api_key='',provider=FakeProvider());self.client=TestClient(self.app);self.client.__enter__();self.headers={'X-Client-Id':'test-browser-one'}
    def tearDown(self): self.client.__exit__(None,None,None);self.temp.cleanup()
    def search(self,mode='demo'):
        response=self.client.post('/api/search',json={'area':'Navrangpura','mode':mode},headers=self.headers);self.assertEqual(response.status_code,200);return response.json()
    def test_health(self):self.assertTrue(self.client.get('/api/health').json()['database_ready'])
    def test_two_character_location_suggestions(self):
        response=self.client.get('/api/autocomplete?q=na&city=Worldwide')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['suggestions'][0]['text'],'Navrangpura')
        self.assertEqual(self.client.get('/api/autocomplete?q=n').status_code,422)
    def test_invalid_browser_id_is_rejected_before_provider_search(self):
        response=self.client.post('/api/search',json={'area':'Navrangpura','mode':'live'},headers={'X-Client-Id':'"test-browser-one"'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.app.state.provider.discover_calls,0)
    def test_saved_is_private_and_idempotent(self):
        p=self.search('live')['properties'][0];url='/api/saved/'+p['id']
        for _ in range(2):self.assertEqual(self.client.post(url,headers=self.headers).status_code,200)
        self.assertEqual(len(self.client.get('/api/saved',headers=self.headers).json()['properties']),1)
        self.assertEqual(self.client.get('/api/saved',headers={'X-Client-Id':'test-browser-two'}).json()['properties'],[])
        self.client.delete(url,headers=self.headers);self.assertEqual(self.client.get('/api/saved',headers=self.headers).json()['properties'],[])
    def test_demo_cannot_leak_into_live(self):
        d=self.search();r=self.client.post('/api/recommendations',json={'property_ids':d['candidate_ids'],'preferences':{'area':'Navrangpura','mode':'live'}},headers=self.headers);self.assertEqual(r.json()['properties'],[])
    def test_private_inputs_survive_search(self):
        p=self.search('live')['properties'][0];r=self.client.post('/api/properties/'+p['id']+'/inputs',json={'price':14000,'bedrooms':2},headers=self.headers);self.assertEqual(r.status_code,200)
        self.assertEqual(self.search('live')['properties'][0]['price'],14000)
        other=self.client.post('/api/search',json={'area':'Navrangpura','mode':'live'},headers={'X-Client-Id':'test-browser-two'});self.assertIsNone(other.json()['properties'][0]['price'])
    def test_helpful_deduplicates(self):
        r=self.client.post('/api/observations',headers=self.headers,json={'area':'Navrangpura','city':'Ahmedabad','category':'lighting','sentiment':'bad','text':'Street lights were out on the road yesterday.'});self.assertEqual(r.status_code,201)
        url='/api/observations/'+r.json()['id']+'/helpful'
        for _ in range(2):self.assertEqual(self.client.post(url,headers=self.headers).json()['helpful'],1)
    def test_unknown_property(self):self.assertEqual(self.client.post('/api/saved/missing',headers=self.headers).status_code,404)
    def test_identifier_required(self):self.assertEqual(self.client.get('/api/saved').status_code,400)

class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_worldwide_autocomplete_keeps_place_context(self):
        provider=SerpApi('unused')
        async def resolve(*args):return {'lat':23,'lng':72}
        async def search(engine,**params):
            return {'suggestions':[{'value':'Navsari','subtext':'Gujarat, India','latitude':20.95,'longitude':72.93}]} if params['ll']=='@0,0,3z' else {'suggestions':[{'value':'Navrangpura','subtext':'Ahmedabad, Gujarat, India','latitude':23.04,'longitude':72.55},{'value':'Navsari','subtext':'Gujarat, India','latitude':20.95,'longitude':72.93}]}
        provider.resolve=resolve;provider.search=search
        data=await provider.autocomplete('nav','Ahmedabad')
        self.assertEqual([p['text'] for p in data],['Navsari']);self.assertEqual(data[0]['coordinates']['lat'],20.95);self.assertEqual(data[0]['address'],'Gujarat, India');await provider.close()

    async def test_global_suggestions_survive_nearby_failure(self):
        provider=SerpApi('unused')
        async def resolve(*args):raise RuntimeError('Nearby unavailable')
        async def search(*args,**params):return {'suggestions':[{'value':'Paris','subtext':'France','latitude':48.85,'longitude':2.35}]}
        provider.resolve=resolve;provider.search=search
        self.assertEqual((await provider.autocomplete('par','Ahmedabad'))[0]['address'],'France');await provider.close()

    async def test_selected_coordinates_bypass_previous_city(self):
        provider=SerpApi('unused');queries=[]
        async def resolve(*args):raise AssertionError('Selected location must not be re-geocoded in old city')
        async def search(engine,**params):queries.append(params);return {}
        provider.resolve=resolve;provider.search=search
        body=SearchRequest(area='Navsari',city='Ahmedabad',location={'name':'Navsari','address':'Gujarat, India','lat':20.95,'lng':72.93})
        centre,items,leads,report=await provider.discover(body)
        self.assertEqual(centre['lat'],20.95);self.assertNotIn('Ahmedabad',queries[0]['q']);self.assertIn('@20.95,72.93',queries[0]['ll']);await provider.close()

    async def test_worldwide_queries_do_not_append_worldwide(self):
        provider=SerpApi('unused');queries=[]
        async def search(engine,**params):queries.append(params);return {}
        provider.search=search
        await provider.resolve('Paris France','Worldwide');self.assertEqual(queries[0]['q'],'Paris France');await provider.close()

    async def test_seconds_metres_and_mode(self):
        provider=SerpApi('unused')
        async def fake(*args,**kwargs):return {'directions':[{'travel_mode':'driving','duration':61,'distance':1250},{'travel_mode':'walking','duration':1,'distance':10}]}
        provider.search=fake
        p=base_property({'title':'Home','gps_coordinates':{'latitude':23,'longitude':72}},'Area','City')
        r=await provider.commute(p,SearchRequest(area='Area',destination='Office',travel_mode='driving'));self.assertEqual(r['morning']['minutes'],2);self.assertEqual(r['morning']['distance_km'],1.25);await provider.close()

if __name__=='__main__': unittest.main()
