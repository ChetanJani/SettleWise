from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
API_KEY = os.getenv('SERPAPI_API_KEY', '').strip()
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = 'postgresql://' + DATABASE_URL[len('postgres://'):]
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
if not DATABASE_URL:
    (ROOT / 'data').mkdir(exist_ok=True)
    DATABASE_URL = 'sqlite:///' + str(ROOT / 'data' / 'settlewise.sqlite3')
