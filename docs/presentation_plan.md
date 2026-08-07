# Présentation soutenance — 12 slides
1. Contexte Puls-Events et besoin métier
2. Objectifs et périmètre du POC
3. Pourquoi un RAG ?
4. Architecture globale OpenAgenda → Mistral Embed → FAISS → Mistral → API
5. Collecte OpenAgenda : pagination, nettoyage, récence
6. Vectorisation : mistral-embed + Documents LangChain
7. Recherche FAISS et seuil minimal de pertinence
8. Génération Mistral et garde-fous anti-hallucination
9. API FastAPI : /health, /ask, /rebuild protégé, /docs
10. Tests et évaluation : cas positifs + négatifs, métriques réelles
11. Docker, CI et démonstration live
12. Limites, améliorations et conclusion
