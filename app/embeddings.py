from langchain_core.embeddings import Embeddings
from mistralai.client import Mistral
from .config import MISTRAL_API_KEY, MISTRAL_EMBED_MODEL

class MistralEmbeddings(Embeddings):
    def __init__(self, api_key: str=MISTRAL_API_KEY, model: str=MISTRAL_EMBED_MODEL, batch_size: int=32):
        if not api_key: raise RuntimeError("MISTRAL_API_KEY manquante")
        self.client=Mistral(api_key=api_key); self.model=model; self.batch_size=batch_size
    def embed_documents(self, texts):
        vectors=[]
        for i in range(0,len(texts),self.batch_size):
            res=self.client.embeddings.create(model=self.model, inputs=texts[i:i+self.batch_size])
            vectors.extend([x.embedding for x in res.data])
        return vectors
    def embed_query(self, text):
        return self.client.embeddings.create(model=self.model, inputs=[text]).data[0].embedding
