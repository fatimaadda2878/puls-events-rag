from __future__ import annotations

from .config import (
    CANDIDATE_K,
    MIN_RELEVANCE_SCORE,
    MISTRAL_API_KEY,
    MISTRAL_CHAT_MODEL,
    TOP_K,
)
from .filters import overlaps_period, passes_genre_guard, requested_period
from .indexer import load_index
from .mistral_client import Mistral

NO_RESULT = "Je n’ai trouvé aucun événement suffisamment pertinent pour cette demande."


def _message_content(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    # Compatibilité éventuelle avec des contenus structurés.
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(getattr(item, "text", "")))
        return "\n".join(x for x in parts if x).strip()

    return str(content or "").strip()


class RAGService:
    def __init__(self):
        if not MISTRAL_API_KEY:
            raise RuntimeError("MISTRAL_API_KEY manquante.")
        self.store = load_index()
        self.client = Mistral(api_key=MISTRAL_API_KEY)

    @staticmethod
    def relevance_from_l2(distance: float) -> float:
        """
        Index FAISS avec vecteurs L2-normalisés :
        squared_L2 = 2 - 2*cosine  => cosine = 1 - squared_L2 / 2.
        """
        return max(-1.0, min(1.0, 1.0 - float(distance) / 2.0))

    def retrieve(self, question: str):
        period = requested_period(question)
        hits = self.store.similarity_search_with_score(
            question,
            k=CANDIDATE_K,
        )

        accepted = []
        seen_events = set()

        for doc, distance in hits:
            relevance = self.relevance_from_l2(distance)
            if relevance < MIN_RELEVANCE_SCORE:
                continue

            if not passes_genre_guard(question, doc.page_content):
                continue

            if not overlaps_period(doc.metadata, period):
                continue

            event_id = (
                doc.metadata.get("id")
                or (
                    doc.metadata.get("title"),
                    doc.metadata.get("start"),
                    doc.metadata.get("address"),
                )
            )
            if event_id in seen_events:
                continue

            seen_events.add(event_id)
            accepted.append((doc, relevance))

            if len(accepted) >= TOP_K:
                break

        return accepted

    def ask(self, question: str):
        hits = self.retrieve(question)

        if not hits:
            return {
                "answer": NO_RESULT,
                "sources": [],
                "backend_used": "mistral",
                "retrieval": "faiss+mistral-embed",
            }

        context_blocks = []
        for i, (doc, relevance) in enumerate(hits, start=1):
            context_blocks.append(
                f"[EVENEMENT {i} | score={relevance:.3f}]\n{doc.page_content}"
            )
        context = "\n\n---\n\n".join(context_blocks)

        system_prompt = (
            "Tu es l'assistant événementiel Puls-Events. "
            "Tu dois répondre uniquement à partir des événements fournis dans le contexte. "
            "N'invente jamais de titre, date, lieu, tarif ou disponibilité. "
            "Si le contexte ne répond pas précisément à la question, réponds exactement : "
            f"« {NO_RESULT} » "
            "Réponds en français, de façon concise et utile."
        )

        user_prompt = f"QUESTION:\n{question}\n\nCONTEXTE:\n{context}"

        response = self.client.chat.complete(
            model=MISTRAL_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        answer = _message_content(response.choices[0].message)
        if not answer:
            answer = NO_RESULT

        sources = [
            {
                **doc.metadata,
                "relevance": round(score, 4),
            }
            for doc, score in hits
        ]

        return {
            "answer": answer,
            "sources": sources,
            "backend_used": "mistral",
            "retrieval": "faiss+mistral-embed",
        }
