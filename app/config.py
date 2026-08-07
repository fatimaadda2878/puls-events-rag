from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_CHAT_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "mistral-small-latest")
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")
REBUILD_API_KEY = os.getenv("REBUILD_API_KEY", "")
OPENAGENDA_API_URL = os.getenv("OPENAGENDA_API_URL", "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records")
OPENAGENDA_CITY = os.getenv("OPENAGENDA_CITY", "Paris")
OPENAGENDA_PAGE_SIZE = min(int(os.getenv("OPENAGENDA_PAGE_SIZE", "100")), 100)
OPENAGENDA_MAX_EVENTS = int(os.getenv("OPENAGENDA_MAX_EVENTS", "0"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.55"))
TOP_K = int(os.getenv("TOP_K", "5"))
INDEX_DIR = ROOT / os.getenv("INDEX_DIR", "index/faiss")
DATA_PATH = ROOT / os.getenv("DATA_PATH", "data/events.json")
