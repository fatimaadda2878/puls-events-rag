from __future__ import annotations

import hmac
from functools import lru_cache

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .config import AUTO_REBUILD_ON_START, REBUILD_API_KEY
from .indexer import index_is_ready, read_index_metadata
from .rag import RAGService
from .rebuild_manager import rebuild_manager

app = FastAPI(
    title="Puls-Events RAG API",
    version="2.0.0",
    description=(
        "POC RAG : OpenAgenda/OpenDataSoft → mistral-embed → FAISS/LangChain "
        "→ Mistral → FastAPI."
    ),
)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@lru_cache(maxsize=1)
def service() -> RAGService:
    return RAGService()


def _clear_service_cache():
    service.cache_clear()


def _valid_rebuild_key(value: str | None) -> bool:
    if not REBUILD_API_KEY or not value:
        return False
    return hmac.compare_digest(value, REBUILD_API_KEY)


@app.on_event("startup")
def startup():
    # Optionnel : utile uniquement si l'utilisateur choisit de reconstruire
    # automatiquement après un redémarrage Render.
    if AUTO_REBUILD_ON_START and not index_is_ready() and REBUILD_API_KEY:
        rebuild_manager.start(on_success=_clear_service_cache)


@app.get("/")
def root():
    return {
        "name": "Puls-Events RAG API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    meta = read_index_metadata()
    rebuild = rebuild_manager.snapshot()

    return {
        "status": "ok",
        "index_ready": index_is_ready(),
        "events_indexed": meta.get("events_indexed"),
        "documents_indexed": meta.get("documents_indexed"),
        "retrieval": "faiss+mistral-embed",
        "generation": "mistral",
        "rebuild": rebuild,
    }


@app.post("/ask")
def ask(body: AskRequest):
    question = body.question.strip()

    if not question:
        raise HTTPException(status_code=422, detail="Question vide.")

    if not index_is_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Index FAISS absent. Lancez POST /rebuild puis surveillez /health "
                "jusqu'à index_ready=true."
            ),
        )

    try:
        return service().ask(question)
    except Exception as exc:
        # Message utile dans Swagger, sans exposer de secret.
        raise HTTPException(
            status_code=500,
            detail=f"Erreur RAG : {type(exc).__name__}: {exc}",
        ) from exc


@app.post("/rebuild", status_code=status.HTTP_202_ACCEPTED)
def rebuild(x_rebuild_key: str | None = Header(default=None)):
    if not _valid_rebuild_key(x_rebuild_key):
        raise HTTPException(
            status_code=401,
            detail="Clé de reconstruction invalide.",
        )

    started = rebuild_manager.start(on_success=_clear_service_cache)
    if not started:
        return {
            "status": "already_running",
            "message": "Une reconstruction est déjà en cours.",
        }

    return {
        "status": "accepted",
        "message": (
            "Reconstruction lancée hors de la requête HTTP. "
            "Surveillez GET /health."
        ),
    }
