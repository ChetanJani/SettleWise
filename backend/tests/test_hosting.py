import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import create_app


class HostingTests(unittest.TestCase):
    def test_only_configured_production_origin_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CORS_ORIGINS': 'https://settlewisehca.netlify.app/' }):
            app = create_app('sqlite:///' + str(Path(directory) / 'test.sqlite3'), api_key='')
            with TestClient(app) as client:
                headers = {'Origin': 'https://settlewisehca.netlify.app', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type,x-client-id'}
                allowed = client.options('/api/search', headers=headers)
                self.assertEqual(allowed.status_code, 200)
                self.assertEqual(allowed.headers['access-control-allow-origin'], headers['Origin'])
                rejected = client.options('/api/search', headers={**headers, 'Origin': 'https://unrelated.example'})
                self.assertEqual(rejected.status_code, 400)
                self.assertNotIn('access-control-allow-origin', rejected.headers)
