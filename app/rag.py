from __future__ import annotations
from mistralai import Mistral
from .config import MISTRAL_API_KEY,MISTRAL_CHAT_MODEL,MIN_RELEVANCE_SCORE,TOP_K
from .indexer import load_index

NO_RESULT="Je n’ai trouvé aucun événement suffisamment pertinent pour cette demande."

class RAGService:
    def __init__(self):
        if not MISTRAL_API_KEY: raise RuntimeError("MISTRAL_API_KEY manquante")
        self.store=load_index(); self.client=Mistral(api_key=MISTRAL_API_KEY)
    @staticmethod
    def relevance_from_l2(distance: float) -> float:
        # Vecteurs L2-normalisés: squared L2 = 2 - 2*cosine.
        return max(-1.0,min(1.0,1.0-float(distance)/2.0))
    def retrieve(self, question: str):
        hits=self.store.similarity_search_with_score(question,k=TOP_K)
        out=[]
        for doc,distance in hits:
            relevance=self.relevance_from_l2(distance)
            if relevance >= MIN_RELEVANCE_SCORE: out.append((doc,relevance))
        return out
    def ask(self, question: str):
        hits=self.retrieve(question)
        if not hits: return {"answer":NO_RESULT,"sources":[],"backend_used":"mistral","retrieval":"faiss+mistral-embed"}
        context="\n\n---\n\n".join(d.page_content for d,_ in hits)
        prompt=f"""Tu es l'assistant événementiel Puls-Events. Réponds uniquement à partir du CONTEXTE. N'invente aucun événement. Si le contexte ne permet pas de répondre précisément, dis qu'aucun événement pertinent n'a été trouvé. Réponds en français, brièvement, avec titre, date et lieu quand disponibles.

QUESTION:
{question}

CONTEXTE:
{context}"""
        res=self.client.chat.complete(model=MISTRAL_CHAT_MODEL,messages=[{"role":"user","content":prompt}],temperature=0.1)
        answer=res.choices[0].message.content
        sources=[{**d.metadata,"relevance":round(s,4)} for d,s in hits]
        return {"answer":answer,"sources":sources,"backend_used":"mistral","retrieval":"faiss+mistral-embed"}
