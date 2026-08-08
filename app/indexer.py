from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, Iterable, Iterator

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_PATH,
    INDEX_BATCH_SIZE,
    INDEX_DIR,
    MAX_CHUNKS_PER_EVENT,
    MAX_DESCRIPTION_CHARS,
)
from .embeddings import MistralEmbeddings
from .openagenda import iter_all_events


ProgressCallback = Callable[[dict], None]


def _clean_text(value) -> str:
    return " ".join(str(value or "").split())


def event_text(event: dict) -> str:
    keywords = event.get("keywords", [])
    if isinstance(keywords, list):
        keywords = ", ".join(map(str, keywords))

    description = _clean_text(event.get("description", ""))[:MAX_DESCRIPTION_CHARS]

    return (
        f"Titre: {_clean_text(event.get('title'))}\n"
        f"Description: {description}\n"
        f"Mots-clés: {_clean_text(keywords)}\n"
        f"Ville: {_clean_text(event.get('city'))}\n"
        f"Adresse: {_clean_text(event.get('address'))}\n"
        f"Début: {_clean_text(event.get('start'))}\n"
        f"Fin: {_clean_text(event.get('end'))}"
    )


def _chunks(text: str) -> Iterator[str]:
    text = text.strip()
    if not text:
        return

    if len(text) <= CHUNK_SIZE:
        yield text
        return

    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for number, start in enumerate(range(0, len(text), step)):
        if number >= MAX_CHUNKS_PER_EVENT:
            return
        chunk = text[start:start + CHUNK_SIZE].strip()
        if chunk:
            yield chunk


def event_documents(event: dict) -> list[Document]:
    base_metadata = {
        key: event.get(key, "")
        for key in ("id", "title", "city", "address", "start", "end", "url")
    }

    docs: list[Document] = []
    for i, chunk in enumerate(_chunks(event_text(event))):
        metadata = dict(base_metadata)
        metadata["chunk_index"] = i
        docs.append(Document(page_content=chunk, metadata=metadata))
    return docs


def _batched(iterable: Iterable[dict], size: int):
    batch: list[dict] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _atomic_replace_dir(source: Path, target: Path):
    backup = target.parent / f"{target.name}.backup"

    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)

    if target.exists():
        target.replace(backup)

    try:
        source.replace(target)
    except Exception:
        if backup.exists() and not target.exists():
            backup.replace(target)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


def build_index(
    events=None,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """
    Reconstruction mémoire-efficace :
    - OpenAgenda est parcouru en streaming ;
    - Mistral est appelé en petits lots ;
    - FAISS est alimenté progressivement ;
    - l'ancien index n'est remplacé qu'après succès complet.
    """
    source = iter(events) if events is not None else iter_all_events()

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.parent.mkdir(parents=True, exist_ok=True)

    tmp_data = DATA_PATH.parent / f".{DATA_PATH.name}.building"
    tmp_index = INDEX_DIR.parent / f".{INDEX_DIR.name}.building"

    if tmp_data.exists():
        tmp_data.unlink()
    if tmp_index.exists():
        shutil.rmtree(tmp_index, ignore_errors=True)

    embeddings = MistralEmbeddings()
    store: FAISS | None = None
    events_indexed = 0
    documents_indexed = 0
    first_json = True

    def progress(**extra):
        if progress_callback:
            progress_callback(
                {
                    "events_indexed": events_indexed,
                    "documents_indexed": documents_indexed,
                    **extra,
                }
            )

    try:
        with tmp_data.open("w", encoding="utf-8") as handle:
            handle.write("[\n")

            for event_batch in _batched(source, INDEX_BATCH_SIZE):
                docs: list[Document] = []

                for event in event_batch:
                    if not first_json:
                        handle.write(",\n")
                    json.dump(event, handle, ensure_ascii=False)
                    first_json = False

                    events_indexed += 1
                    docs.extend(event_documents(event))

                if not docs:
                    continue

                if store is None:
                    store = FAISS.from_documents(
                        docs,
                        embeddings,
                        normalize_L2=True,
                        distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE,
                    )
                else:
                    store.add_documents(docs)

                documents_indexed += len(docs)
                handle.flush()
                progress(stage="embedding")

            handle.write("\n]\n")

        if store is None or events_indexed == 0:
            raise RuntimeError("Aucun événement exploitable : index non construit.")

        tmp_index.mkdir(parents=True, exist_ok=True)
        store.save_local(str(tmp_index))

        metadata = {
            "events_indexed": events_indexed,
            "documents_indexed": documents_indexed,
            "embedding_model": embeddings.model,
            "distance_strategy": "EUCLIDEAN_DISTANCE",
            "normalize_L2": True,
        }
        (tmp_index / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        _atomic_replace_dir(tmp_index, INDEX_DIR)
        tmp_data.replace(DATA_PATH)

        progress(stage="done")
        return metadata

    except Exception:
        if tmp_data.exists():
            tmp_data.unlink(missing_ok=True)
        if tmp_index.exists():
            shutil.rmtree(tmp_index, ignore_errors=True)
        raise


def index_is_ready() -> bool:
    required = (
        INDEX_DIR / "index.faiss",
        INDEX_DIR / "index.pkl",
        INDEX_DIR / "metadata.json",
    )
    return all(path.exists() for path in required)


def read_index_metadata() -> dict:
    path = INDEX_DIR / "metadata.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_index():
    if not index_is_ready():
        raise FileNotFoundError("Index FAISS absent ou incomplet.")

    embeddings = MistralEmbeddings()
    return FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
        normalize_L2=True,
        distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE,
    )
