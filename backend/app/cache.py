"""Persistent, local provider cache and an atomic daily request budget."""
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

class SearchCache:
    def __init__(self,path,limit=30):
        self.path=str(path);self.limit=limit
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, expires REAL, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, count INTEGER NOT NULL)')

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:yield db
        finally:db.close()
    def get(self,key):
        with self.connection() as db:
            row=db.execute('SELECT payload FROM responses WHERE key=? AND expires>?',(key,time.time())).fetchone()
            return json.loads(row[0]) if row else None
    def put(self,key,payload,ttl):
        with self.connection() as db:
            db.execute('INSERT INTO responses VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET expires=excluded.expires,payload=excluded.payload',(key,time.time()+ttl,json.dumps(payload)))
            db.execute('DELETE FROM responses WHERE expires<?',(time.time(),))
    def reserve(self):
        day=datetime.now(timezone.utc).date().isoformat()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            count=(db.execute('SELECT count FROM usage WHERE day=?',(day,)).fetchone() or (0,))[0]
            if count>=self.limit:return False
            db.execute('INSERT INTO usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET count=count+1',(day,))
            return True
    def stats(self):
        day=datetime.now(timezone.utc).date().isoformat()
        with self.connection() as db:
            count=(db.execute('SELECT count FROM usage WHERE day=?',(day,)).fetchone() or (0,))[0]
            return {'requests_today':count,'daily_limit':self.limit,'scope':'This backend instance; shared key usage elsewhere is not included.','reset_timezone':'UTC'}
