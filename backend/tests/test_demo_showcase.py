from collections import Counter
from pathlib import Path
import tempfile,unittest
from fastapi.testclient import TestClient
from app.main import create_app
from app.demo import demo_properties,demo_commute,position_demo
from app.models import SearchRequest

class NoLiveProvider:
    request_count=0
    async def close(self):pass
    def __getattr__(self,name):raise AssertionError('Demo touched live provider: '+name)

class ShowcaseTests(unittest.TestCase):
    def test_fifty_complete_stays_and_local_photos(self):
        items=demo_properties('Navrangpura','Ahmedabad')
        self.assertEqual(Counter(p['type'] for p in items),{t:10 for t in ('pg','hostel','hotel','flat','house')})
        self.assertEqual(len({p['id'] for p in items}),50)
        public=Path(__file__).resolve().parents[2]/'frontend/public'
        for p in items:
            self.assertTrue(p['is_demo']);self.assertFalse(p['verified'])
            self.assertGreater(p['price'],0);self.assertGreater(p['occupancy'],0)
            self.assertEqual(p['price_unit'],'night' if p['type']=='hotel' else 'month')
            self.assertEqual(p['review_safety']['classified_reviews'],12)
            self.assertEqual(len(p['images']),3)
            self.assertTrue(all((public/im['url'].lstrip('/')).exists() for im in p['images']))
        self.assertGreater(len({p['review_safety']['score'] for p in items}),4)

    def test_route_estimates_follow_distance_and_transport(self):
        p=demo_properties('Office','City')[1];centre={'lat':23.04,'lng':72.55};position_demo(p,centre)
        walk=demo_commute(p,SearchRequest(area='Office',destination='Office',travel_mode='walking'))
        car=demo_commute(p,SearchRequest(area='Office',destination='Office',travel_mode='driving'))
        self.assertGreaterEqual(walk['morning']['distance_km'],p['area_distance_km'])
        self.assertLess(walk['morning']['minutes'],15)
        self.assertLessEqual(car['morning']['minutes'],walk['morning']['minutes'])
        self.assertTrue(walk['is_demo'])

    def test_demo_search_and_all_details_without_provider_or_database(self):
        with tempfile.TemporaryDirectory() as temp:
            app=create_app('sqlite:///'+str(Path(temp)/'test.db'),api_key='',provider=NoLiveProvider())
            with TestClient(app) as client:
                # Presentation still works if database connectivity is unavailable.
                app.state.store.ready=False
                prefs={'area':'Navrangpura','city':'Ahmedabad','mode':'demo','destination':'Navrangpura','property_types':['pg'],'location':{'name':'Navrangpura','lat':23.041,'lng':72.554},'household':'family'}
                response=client.post('/api/search',json=prefs,headers={'X-Client-Id':'demo-showcase-browser'})
                self.assertEqual(response.status_code,200)
                data=response.json();self.assertEqual(len(data['candidates']),50)
                self.assertEqual(len(data['properties']),10)
                self.assertTrue(data['discovery']['complete'])
                self.assertTrue(all(p['commute'] and p['area_distance_km']<3 for p in data['candidates']))
                pid=data['candidates'][1]['id']
                for section in ('place','photos','reviews','nearby','commute','area'):
                    result=client.post(f'/api/properties/{pid}/details',json={'section':section,'preferences':prefs})
                    self.assertEqual(result.status_code,200,section)
                    self.assertTrue(result.json()['is_demo'])
                    if section=='nearby':self.assertTrue(any(p['category']=='School' for p in result.json()['places']))
                    if section=='reviews':self.assertEqual(len(result.json()['reviews']),12)
                mismatch=client.post(f'/api/properties/{pid}/details',json={'section':'reviews','preferences':{**prefs,'mode':'live'}})
                self.assertEqual(mismatch.status_code,400)
