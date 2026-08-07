# Puls-Events — POC RAG événements culturels

POC de chatbot événementiel fondé sur **OpenAgenda → Mistral Embed → FAISS → LangChain → Mistral → FastAPI**. Il n'utilise ni TF-IDF ni backend de réponses template.

## Architecture
1. `app/openagenda.py` récupère les pages OpenAgenda jusqu'à épuisement des résultats et conserve les événements de moins d'un an / à venir.
2. `app/indexer.py` transforme les événements en `Document` LangChain, calcule les embeddings `mistral-embed` et persiste un index FAISS.
3. `app/rag.py` recherche les voisins sémantiques, convertit la distance L2 normalisée en pertinence cosinus et applique `MIN_RELEVANCE_SCORE`.
4. Mistral génère une réponse uniquement à partir du contexte retenu.
5. FastAPI expose `/health`, `/ask`, `/rebuild` et `/docs`. `/rebuild` exige l'en-tête `X-Rebuild-Key`.

## Installation
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows ; cp .env.example .env sur macOS/Linux
```
Renseigner `MISTRAL_API_KEY` et changer `REBUILD_API_KEY`.

## Construire l'index réel
```bash
python scripts/rebuild_index.py
```
Le nombre exact d'événements est écrit dans `index/faiss/metadata.json` et visible via `/health`.

## Lancer l'API
```bash
uvicorn app.main:app --reload --port 7860
```
Swagger : `http://localhost:7860/docs`.

## Appels
```bash
curl http://localhost:7860/health
curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" -d '{"question":"Y a-t-il des concerts de reggae à Paris ?"}'
curl -X POST http://localhost:7860/rebuild -H "X-Rebuild-Key: VOTRE_SECRET"
```

## Docker
```bash
docker build -t puls-events-rag .
docker run --env-file .env -p 7860:7860 puls-events-rag
```
Pour une démo hors connexion, construire l'index avant la soutenance et conserver le dossier `index/` localement.

## Évaluation
`data/eval_dataset.json` contient des cas annotés positifs et négatifs. Le cas reggae est explicitement négatif. Après construction de l'index :
```bash
python scripts/evaluate_rag.py
```
Le rapport est écrit dans `reports/evaluation.json`. Le seuil `MIN_RELEVANCE_SCORE` doit être calibré sur ce jeu de validation (valeur initiale 0,55), puis figé avant le test final.

## Tests
```bash
pytest -q
```
La CI GitHub Actions exécute les tests sans appeler Mistral : les appels externes doivent rester hors des tests unitaires.

## Structure
- `app/` : API, RAG, embeddings, indexation, OpenAgenda
- `scripts/` : reconstruction, test API, évaluation
- `tests/` : tests unitaires
- `data/` : jeu annoté ; `events.json` généré
- `index/` : index FAISS généré
- `docs/` : rapport et présentation

## Limites / perspectives
Le seuil sémantique dépend du corpus et doit être calibré. Les filtres temporels complexes (« cette semaine ») peuvent être renforcés par un parsing déterministe des dates avant la recherche. En production : authentification forte, rate limiting, cache, observabilité, stockage persistant de l'index et reconstruction asynchrone.
