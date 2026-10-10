import unittest
from app.provider import SerpApi,ProviderError
from app.models import SearchRequest
from app.evidence import review_safety

class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_cached_hotels_at_limit_are_explicitly_partial(self):
        provider=SerpApi('unused')
        async def search(engine,**params):
            if params['q'].startswith('hotels near '):
                return {'local_results':[{'title':f'Hotel {i}','place_id':str(i),'gps_coordinates':{'latitude':23+.0001*i,'longitude':72}} for i in range(12)]}
            raise ProviderError('Local daily search limit reached. Cached results and filters still work.')
        provider.search=search
        try:
            _,items,_,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72}))
            self.assertEqual(len(items),12)
            self.assertTrue(report['provider_incomplete'])
            self.assertTrue(report['limit_reached'])
            self.assertEqual([t['type'] for t in report['types'] if t['status']=='unavailable'],['pg','hostel','flat','house'])
        finally:await provider.close()

    async def test_selecting_only_pg_still_collects_ten_of_each_type_nearby(self):
        provider=SerpApi('unused');calls=[]
        names=['PG accommodation','Student Hostel','City Hotel','Residential Apartments','Rental House Villa']
        async def search(engine,**params):
            calls.append(params)
            title=names[len(calls)-1]
            result=[{'title':f'{title} {i}','place_id':f'{title}-{i}','gps_coordinates':{'latitude':23+.0001*i,'longitude':72}} for i in range(12)]
            result.append({'title':title+' Too Far','place_id':'far-'+title,'gps_coordinates':{'latitude':24,'longitude':72}})
            return {'local_results':result}
        provider.search=search
        try:
            centre,items,leads,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72},property_types=['pg']))
            self.assertEqual(len(calls),5)
            self.assertEqual(len(items),60)
            self.assertTrue(all(p['area_distance_km']<=3 for p in items))
            self.assertTrue(all(r['count']>=10 for r in report['types']))
            self.assertTrue(report['complete'])
        finally:await provider.close()

    async def test_sparse_results_are_not_filled_with_fictional_listings(self):
        provider=SerpApi('unused')
        async def search(*args,**params):return {'local_results':[]}
        provider.search=search
        try:
            _,items,_,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72}))
            self.assertEqual(items,[])
            self.assertFalse(report['complete'])
            self.assertEqual(len(report['types']),5)
            self.assertTrue(all(r['count']==0 and r['reason'] for r in report['types']))
        finally:await provider.close()

    async def test_second_page_is_bounded_deduplicated_and_stays_in_radius(self):
        provider=SerpApi('unused');calls=[]
        async def search(engine,**params):
            calls.append(params)
            title='PG Hostel Hotel Residential Apartments Rental House Villa'
            indices=range(12) if params.get('start')==20 else range(2)
            rows=[{'title':f'{title} {i}','place_id':f'{params["q"]}-{i}','gps_coordinates':{'latitude':23+.0001*i,'longitude':72}} for i in indices]
            rows.append({'title':title,'place_id':'far','gps_coordinates':{'latitude':25,'longitude':72}})
            return {'local_results':rows,'serpapi_pagination':{'next':'https://example.com/next'}}
        provider.search=search
        try:
            _,items,_,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72},property_types=['pg']))
            self.assertEqual(len(calls),10)
            self.assertEqual(sum(p.get('start')==20 for p in calls),5)
            self.assertEqual(len(items),60)
            self.assertTrue(report['complete'])
            self.assertTrue(all(p['area_distance_km']<=3 for p in items))
        finally:await provider.close()

    async def test_news_includes_flat_highlight_and_grouped_stories_with_sources(self):
        provider=SerpApi('unused')
        async def search(engine,**params):
            self.assertEqual(engine,'google_news')
            return {'news_results':[{'title':'Local lighting','link':'https://example.com/a','source':{'name':'City News'},'iso_date':'2026-10-01'}, {'highlight':{'title':'Transit news','link':'https://example.com/b'},'stories':[{'title':'Resident report','link':'https://example.com/c'}]}]}
        provider.search=search
        try:
            data=await provider.area_evidence({},SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72}))
            self.assertEqual(len(data['sources']),3)
            self.assertEqual(data['sources'][0]['publisher'],'City News')
            self.assertIn('not a local crime database',data['summary'])
        finally:await provider.close()

    async def test_farther_listings_on_same_page_fill_target_without_more_requests(self):
        provider=SerpApi('unused');calls=[]
        async def search(engine,**params):
            calls.append(params)
            title='PG Hostel Hotel Residential Apartments Rental House Villa'
            # Three nearby and seven 5-8 km away; a >10 km row must be excluded.
            points=[23+.0001*i for i in range(3)]+[23+.045+.004*i for i in range(7)]+[23.11]
            return {'local_results':[{'title':f'{title} {i}','place_id':f'{params["q"]}-{i}','gps_coordinates':{'latitude':lat,'longitude':72}} for i,lat in enumerate(points)],'serpapi_pagination':{'next':'https://example.com/next'}}
        provider.search=search
        try:
            _,items,_,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72},property_types=['pg'],radius_km=3))
            self.assertEqual(len(calls),5)
            self.assertEqual(len(items),50)
            self.assertTrue(report['complete'])
            self.assertTrue(any(p['area_distance_km']>3 for p in items))
            self.assertTrue(all(p['area_distance_km']<=10 for p in items))
            self.assertEqual([p['area_distance_km'] for p in items],sorted(p['area_distance_km'] for p in items))
        finally:await provider.close()

    async def test_sparse_category_expands_map_and_paginates_once(self):
        provider=SerpApi('unused');calls=[]
        async def search(engine,**params):
            calls.append(params)
            title='PG Hostel Hotel Residential Apartments Rental House Villa'
            wide=params['ll'].endswith('13z')
            indices=range(12) if wide and params.get('start')==20 else range(4) if wide else range(1)
            return {'local_results':[{'title':f'{title} {i}','place_id':f'{params["q"]}-{i}','gps_coordinates':{'latitude':23+.005*i,'longitude':72}} for i in indices],'serpapi_pagination':{'next':'https://example.com/next'}}
        provider.search=search
        try:
            _,items,_,report=await provider.discover(SearchRequest(area='Office',location={'name':'Office','lat':23,'lng':72},property_types=['pg']))
            self.assertEqual(len(calls),20)
            self.assertTrue(report['complete'])
            self.assertEqual(len(items),60)
            self.assertTrue(all(r['count']==12 for r in report['types']))
        finally:await provider.close()

class SafetyReviewTests(unittest.TestCase):
    def test_stars_and_unrelated_positive_reviews_do_not_become_safety(self):
        data=review_safety([{'text':'Great food and rooms','rating':5}]*10)
        self.assertIsNone(data['score']);self.assertEqual(data['relevant_reviews'],0)
    def test_explicit_safety_reviews_get_a_reason_and_correct_denominator(self):
        data=review_safety([{'text':'I felt safe here.'},{'text':'Good security and helpful guards.'},{'text':'This street is unsafe.'},{'text':'Very comfortable beds.'}])
        self.assertEqual(data['score'],67)
        self.assertEqual(data['counts']['positive'],2)
        self.assertEqual(data['counts']['negative'],1)
        self.assertEqual(data['classified_reviews'],3)
        self.assertIn('2 positive',data['reason'])
    def test_negation_and_small_samples_do_not_produce_a_positive_score(self):
        data=review_safety([{'text':'This is not safe for women.'},{'text':'Not very safe at night.'}])
        self.assertEqual(data['counts']['negative'],2)
        self.assertEqual(data['counts']['positive'],0)
        self.assertIsNone(data['score'])
        self.assertTrue(data['signals'][0]['women_mentioned'])
    def test_duplicate_and_unclear_reviews_are_excluded_from_scored_sample(self):
        data=review_safety([{'text':'Security at the gate.'},{'text':'Safe place.'},{'text':'Safe place.'}])
        self.assertEqual(data['sample_size'],2)
        self.assertEqual(data['counts']['unclear'],1)
        self.assertEqual(data['classified_reviews'],1)
