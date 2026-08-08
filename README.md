# Puls-Events — POC RAG

Assistant de recommandation d'événements culturels fondé sur une vraie chaîne RAG :

**OpenAgenda/OpenDataSoft → LangChain → Mistral `mistral-embed` → FAISS → seuil de pertinence → Mistral Chat → FastAPI**

Aucun TF-IDF et aucun backend de réponse par template ne sont utilisés.

## Architecture

- `app/openagenda.py` : récupération des données réelles, pagination `/records`, bascule automatique vers `/exports/csv` au-delà de la fenêtre de 10 000, lecture streaming, déduplication et filtre de récence.
- `app/embeddings.py` : embeddings Mistral par petits lots avec retry.
- `app/indexer.py` : chunking, construction progressive FAISS, sauvegarde atomique.
- `app/rag.py` : retrieval, score de pertinence, garde genre/date, génération Mistral.
- `app/main.py` : `/health`, `/ask`, `/rebuild`, Swagger `/docs`.
- `scripts/evaluate_rag.py` : évaluation automatisée des cas positifs/négatifs.
- `tests/` : tests unitaires sans appel réseau réel.

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Renseigner au minimum :

```text
MISTRAL_API_KEY=...
REBUILD_API_KEY=...
```

Lancer l'API :

```bash
uvicorn app.main:app --reload --port 7860
```

Swagger : `http://localhost:7860/docs`

## Reconstruction

### Via l'API

`POST /rebuild` avec l'en-tête :

```text
X-Rebuild-Key: valeur_de_REBUILD_API_KEY
```

L'endpoint répond immédiatement `202 Accepted`. Suivre ensuite :

```text
GET /health
```

Quand la reconstruction est terminée :

```json
{
  "index_ready": true,
  "events_indexed": 1234,
  "documents_indexed": 1500
}
```

Les nombres sont calculés réellement ; aucune valeur n'est codée en dur.

### En local

```bash
python scripts/rebuild_index.py
```

## Recherche et seuil

`MIN_RELEVANCE_SCORE=0.55` est la valeur initiale. Elle doit être recalibrée avec le jeu d'évaluation.

Le service récupère plus de candidats (`CANDIDATE_K=30`), applique :
1. le seuil sémantique ;
2. un contrôle sur un genre explicitement demandé (ex. reggae) ;
3. un filtre temporel simple (`cette semaine`, `aujourd'hui`, mois).

Puis il conserve au maximum `TOP_K=5`.

Le cas négatif « Y a-t-il des concerts de reggae à Paris ? » doit donc retourner aucun résultat si aucun événement reggae pertinent n'est présent.

## Évaluation

Après reconstruction :

```bash
python scripts/evaluate_rag.py
```

Le résultat est écrit dans `reports/evaluation.json` avec :
- accuracy globale ;
- accuracy des cas positifs ;
- accuracy des cas négatifs.

## Tests

```bash
python -m pytest
```

Les tests n'appellent ni OpenAgenda ni Mistral sur Internet.

## Docker

```bash
docker build -t puls-events-rag .
docker run --env-file .env -p 7860:7860 puls-events-rag
```

## Render

Configuration recommandée :

**Build command**

```bash
pip install -r requirements.txt
```

**Start command**

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Variables indispensables :
- `PYTHON_VERSION=3.11.9`
- `MISTRAL_API_KEY`
- `REBUILD_API_KEY`
- `MISTRAL_CHAT_MODEL=mistral-small-latest`
- `MISTRAL_EMBED_MODEL=mistral-embed`
- `MIN_RELEVANCE_SCORE=0.55`
- `OPENAGENDA_CITY=Paris`
- `OPENAGENDA_MAX_EVENTS=0`

Les anciennes variables `TF-IDF`, `EMBEDDING_BACKEND`, `GENERATION_BACKEND`,
`MAX_OPENAGENDA_EVENTS` et `MISTRAL_MODEL` ne sont pas utilisées.

### Important sur le stockage Render

Un service Render sans disque persistant utilise un système de fichiers éphémère.
Un index construit via `/rebuild` peut donc être perdu après un redéploiement ou
un redémarrage. Pour la soutenance gratuite, reconstruire l'index avant la démo.
Pour une persistance réelle, utiliser un disque Render sur un plan compatible.

## Démo soutenance

1. `/health`
2. `/docs`
3. `POST /rebuild`
4. attendre `index_ready=true`
5. `POST /ask`
6. tester notamment :
   - `Quels événements culturels à Paris cette semaine ?`
   - `Y a-t-il des concerts de reggae à Paris ?`
7. lancer `python scripts/evaluate_rag.py`
