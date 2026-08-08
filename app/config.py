from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

# --- Mistral ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
MISTRAL_CHAT_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "mistral-small-latest").strip()
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed").strip()
MISTRAL_EMBED_BATCH_SIZE = max(1, int(os.getenv("MISTRAL_EMBED_BATCH_SIZE", "16")))
MISTRAL_MAX_RETRIES = max(1, int(os.getenv("MISTRAL_MAX_RETRIES", "5")))

# --- Sécurité ---
REBUILD_API_KEY = os.getenv("REBUILD_API_KEY", "").strip()

# --- OpenDataSoft / OpenAgenda ---
OPENAGENDA_API_URL = os.getenv(
    "OPENAGENDA_API_URL",
    "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "evenements-publics-openagenda/records",
).rstrip("/")
OPENAGENDA_CITY = os.getenv("OPENAGENDA_CITY", "Paris").strip()
OPENAGENDA_PAGE_SIZE = min(max(int(os.getenv("OPENAGENDA_PAGE_SIZE", "100")), 1), 100)

# 0 = aucune limite artificielle : tous les résultats correspondant au périmètre.
OPENAGENDA_MAX_EVENTS = max(int(os.getenv("OPENAGENDA_MAX_EVENTS", "0")), 0)

# --- Indexation ---
INDEX_BATCH_SIZE = max(1, int(os.getenv("INDEX_BATCH_SIZE", "32")))
MAX_DESCRIPTION_CHARS = max(500, int(os.getenv("MAX_DESCRIPTION_CHARS", "1800")))
CHUNK_SIZE = max(500, int(os.getenv("CHUNK_SIZE", "1400")))
CHUNK_OVERLAP = min(max(0, int(os.getenv("CHUNK_OVERLAP", "150"))), CHUNK_SIZE - 1)
MAX_CHUNKS_PER_EVENT = max(1, int(os.getenv("MAX_CHUNKS_PER_EVENT", "2")))

INDEX_DIR = ROOT / os.getenv("INDEX_DIR", "index/faiss")
DATA_PATH = ROOT / os.getenv("DATA_PATH", "data/events.json")
REBUILD_STATUS_PATH = ROOT / os.getenv("REBUILD_STATUS_PATH", "index/rebuild_status.json")

# --- Recherche ---
MIN_RELEVANCE_SCORE = min(max(float(os.getenv("MIN_RELEVANCE_SCORE", "0.55")), -1.0), 1.0)
TOP_K = max(1, int(os.getenv("TOP_K", "5")))
CANDIDATE_K = max(TOP_K, int(os.getenv("CANDIDATE_K", "30")))

AUTO_REBUILD_ON_START = os.getenv("AUTO_REBUILD_ON_START", "false").lower() in {
    "1", "true", "yes", "on"
}
