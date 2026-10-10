import asyncio
from pathlib import Path
import tempfile
import unittest
import httpx
from app.provider import SerpApi,ProviderError,base_property
from app.evidence import evidence
from app.models import SearchRequest
from app.main import create_app
from fastapi.testclient import TestClient

class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_queries_and_restart_use_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            async def handle(request):
                calls.append(str(request.url));return httpx.Response(200,json={'local_results':[], 'search_parameters':{'api_key':'secret'}})
            path=Path(tmp)/'cache.sqlite3'
            first=SerpApi('unused',path,daily_limit=2);await first.http.aclose();first.http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
            data=await asyncio.gather(*(first.search('google_maps',q='PG nearby') for _ in range(5)))
            self.assertEqual(len(calls),1);self.assertNotIn('search_parameters',data[0]);await first.close()
            second=SerpApi('unused',path,daily_limit=2);await second.http.aclose();second.http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
            await second.search('google_maps',q='PG nearby');self.assertEqual(len(calls),1)
            await second.search('google_maps',q='Hotels elsewhere')
            with self.assertRaises(ProviderError):await second.search('google_maps',q='Third request')
            self.assertEqual(len(calls),2);self.assertEqual(second.disk.stats()['requests_today'],2);await second.close()
    async def test_autocomplete_is_one_provider_request(self):
        provider=SerpApi('unused');calls=[]
        async def search(engine,**params):calls.append((engine,params));return {'suggestions':[]}
        provider.search=search;await provider.autocomplete('nav','Worldwide');self.assertEqual(len(calls),1);await provider.close()
    async def test_discovery_collects_all_five_types_at_selected_point(self):
        provider=SerpApi('unused');calls=[]
        async def search(engine,**params):calls.append((engine,params));return {'local_results':[]}
        provider.search=search
        await provider.discover(SearchRequest(area='Office',city='Pune',location={'name':'Office','lat':18.56,'lng':73.91},property_types=['pg','hotel','flat']))
        self.assertEqual(len(calls),10)
        self.assertEqual(sum(params['ll'].endswith('15z') for _,params in calls),5)
        self.assertEqual(sum(params['ll'].endswith('13z') for _,params in calls),5)
        await provider.close()

class EvidenceTests(unittest.TestCase):
    def test_rating_does_not_become_safety(self):self.assertIsNone(evidence({'rating':5,'review_count':1000})['score'])
    def test_percent_is_documentation_coverage(self):self.assertEqual(evidence({'security_facts':{'cctv':True,'guard':False}})['score'],50)
    def test_female_does_not_match_male_substring(self):self.assertEqual(base_property({'title':'Female only PG'},'Area','City')['gender_restriction'],'women')
    def test_empty_required_types_rejected(self):
        with self.assertRaises(ValueError):SearchRequest(area='Area',property_types=[])

class OfflineFiltersTests(unittest.TestCase):
    def test_filters_never_fetch_routes(self):
        class Provider:
            calls=0
            async def close(self):pass
            async def discover(self,b):return {'lat':23,'lng':72},[base_property({'title':'Boys PG','place_id':'one'},b.area,b.city)],[]
            async def commute(self,p,b):self.calls+=1;raise AssertionError('Filtering must not fetch a route')
            async def reviews_only(self,p,b):self.calls+=1;return {'reviews':[]}
        provider=Provider()
        with tempfile.TemporaryDirectory() as tmp,TestClient(create_app('sqlite:///'+str(Path(tmp)/'test.db'),api_key='',provider=provider)) as client:
            data=client.post('/api/search',json={'area':'Office','property_types':['pg']}).json()
            response=client.post('/api/recommendations',json={'property_ids':data['candidate_ids'],'preferences':{'area':'Office','priority':'commute','gender_requirement':'men'}})
            self.assertEqual(response.status_code,200);self.assertEqual(provider.calls,0)
            pid=data['candidate_ids'][0];body={'section':'reviews','preferences':{'area':'Office'}}
            for _ in range(2):self.assertEqual(client.post('/api/properties/'+pid+'/details',json=body).status_code,200)
            self.assertEqual(provider.calls,1)
            client.post('/api/search',json={'area':'Office','property_types':['pg']})
            client.post('/api/properties/'+pid+'/details',json=body);self.assertEqual(provider.calls,1)
