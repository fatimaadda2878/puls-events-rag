from __future__ import annotations

import random
import time
from typing import Sequence

from langchain_core.embeddings import Embeddings

from .config import (
    MISTRAL_API_KEY,
    MISTRAL_EMBED_BATCH_SIZE,
    MISTRAL_EMBED_MODEL,
    MISTRAL_MAX_RETRIES,
)
from .mistral_client import Mistral


def _embedding_of(item) -> list[float]:
    value = getattr(item, "embedding", None)
    if value is None and isinstance(item, dict):
        value = item.get("embedding")
    if value is None:
        raise RuntimeError("Réponse Mistral embeddings invalide : embedding absent.")
    return list(value)


def _index_of(item, fallback: int) -> int:
    value = getattr(item, "index", None)
    if value is None and isinstance(item, dict):
        value = item.get("index")
    return fallback if value is None else int(value)


class MistralEmbeddings(Embeddings):
    """Adaptateur LangChain pour l'API Mistral `mistral-embed`."""

    def __init__(
        self,
        api_key: str = MISTRAL_API_KEY,
        model: str = MISTRAL_EMBED_MODEL,
        batch_size: int = MISTRAL_EMBED_BATCH_SIZE,
        max_retries: int = MISTRAL_MAX_RETRIES,
    ):
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY manquante.")

        self.client = Mistral(api_key=api_key)
        self.model = model
        self.batch_size = max(1, int(batch_size))
        self.max_retries = max(1, int(max_retries))

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    inputs=list(texts),
                )
                data = list(getattr(response, "data", []) or [])
                if len(data) != len(texts):
                    raise RuntimeError(
                        f"Mistral a renvoyé {len(data)} embeddings pour {len(texts)} textes."
                    )

                ordered = sorted(
                    enumerate(data),
                    key=lambda pair: _index_of(pair[1], pair[0]),
                )
                return [_embedding_of(item) for _, item in ordered]

            except Exception as exc:
                last_error = exc
                if attempt + 1 == self.max_retries:
                    break
                # Backoff exponentiel + léger jitter, utile en cas de 429/5xx.
                delay = min(2 ** attempt, 12) + random.random() * 0.25
                time.sleep(delay)

        raise RuntimeError(
            f"Échec Mistral embeddings après {self.max_retries} tentative(s) : "
            f"{type(last_error).__name__}: {last_error}"
        ) from last_error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed_batch(texts[start:start + self.batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]
