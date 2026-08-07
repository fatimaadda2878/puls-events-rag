from functools import lru_cache
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from .config import REBUILD_API_KEY, INDEX_DIR
from .indexer import build_index
from .rag import RAGService

app=FastAPI(title="Puls-Events RAG API",version="1.0.0")
class AskRequest(BaseModel): question:str=Field(min_length=2,max_length=500)
@lru_cache
def service(): return RAGService()
@app.get("/health")
def health():
    meta=INDEX_DIR/"metadata.json"; count=None
    if meta.exists():
        import json; count=json.loads(meta.read_text()).get("events_indexed")
    return {"status":"ok","index_ready":INDEX_DIR.exists(),"events_indexed":count,"retrieval":"faiss+mistral-embed","generation":"mistral"}
@app.post("/ask")
def ask(body:AskRequest):
    q=body.question.strip()
    if not q: raise HTTPException(422,"Question vide")
    try: return service().ask(q)
    except FileNotFoundError: raise HTTPException(503,"Index absent. Lancez /rebuild ou scripts/rebuild_index.py")
@app.post("/rebuild")
def rebuild(x_rebuild_key:str|None=Header(default=None)):
    if not REBUILD_API_KEY or x_rebuild_key != REBUILD_API_KEY: raise HTTPException(401,"Clé de reconstruction invalide")
    result=build_index(); service.cache_clear(); return {"status":"rebuilt",**result}
