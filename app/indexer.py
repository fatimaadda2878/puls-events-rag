from __future__ import annotations
import json
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from .config import INDEX_DIR, DATA_PATH
from .embeddings import MistralEmbeddings
from .openagenda import fetch_all_events

def event_text(e):
    kw=e.get("keywords",[]); kw=", ".join(kw) if isinstance(kw,list) else str(kw)
    return f"Titre: {e['title']}\nDescription: {e['description']}\nMots-clés: {kw}\nVille: {e['city']}\nAdresse: {e['address']}\nDébut: {e['start']}\nFin: {e['end']}"

def build_index(events=None):
    events = events if events is not None else fetch_all_events()
    if not events: raise RuntimeError("Aucun événement récupéré: index non construit")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
    docs=[Document(page_content=event_text(e),metadata={k:e.get(k,"") for k in ("id","title","city","address","start","end","url")}) for e in events]
    emb=MistralEmbeddings()
    store=FAISS.from_documents(docs, emb, normalize_L2=True, distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE)
    INDEX_DIR.mkdir(parents=True,exist_ok=True); store.save_local(str(INDEX_DIR))
    (INDEX_DIR/"metadata.json").write_text(json.dumps({"events_indexed":len(events),"documents_indexed":len(docs)},indent=2),encoding="utf-8")
    return {"events_indexed":len(events),"documents_indexed":len(docs)}

def load_index():
    emb=MistralEmbeddings()
    return FAISS.load_local(str(INDEX_DIR),emb,allow_dangerous_deserialization=True,normalize_L2=True,distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE)
