from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite://' + (DATA_DIR / 'campus.sqlite3').as_posix())
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(DATA_DIR / 'uploads'))).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TORTOISE_ORM = {
    'connections': {'default': DATABASE_URL},
    'apps': {'models': {'models': ['models'], 'default_connection': 'default'}},
    'use_tz': True, 'timezone': 'UTC',
}
