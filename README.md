# Puls-Events — Système RAG de recommandation d'événements culturels

[![CI](https://github.com/fatimaadda2878/puls-events-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/fatimaadda2878/puls-events-rag/actions/workflows/ci.yml)

**Puls-Events** est un POC de système **Retrieval-Augmented Generation (RAG)** permettant d'interroger en langage naturel des événements culturels à Paris.

La chaîne principale repose sur des données OpenAgenda/OpenDataSoft, des **embeddings Mistral (`mistral-embed`)**, un index vectoriel **FAISS**, des filtres métier et temporels, puis une génération de réponse avec **Mistral Chat**. L'API est exposée avec **FastAPI** et déployée sur **Render**.

> Chaîne RAG : **OpenAgenda / OpenDataSoft → LangChain → Mistral Embeddings → FAISS → filtres et seuil de pertinence → Mistral Chat → FastAPI**

Aucun backend TF-IDF ni système de réponse par template n'est utilisé dans la chaîne RAG finale.

## Démo en ligne

- API Render : `https://puls-events-rag.onrender.com`
- Swagger : `https://puls-events-rag.onrender.com/docs`
- Health check : `https://puls-events-rag.onrender.com/health`

## Fonctionnalités

- récupération d'événements réels avec pagination ;
- embeddings via `mistral-embed` ;
- indexation et recherche vectorielle FAISS ;
- génération de réponse via Mistral ;
- filtrage temporel (`aujourd'hui`, `cette semaine`, mois explicite) ;
- contrôle de catégories / genres explicitement demandés ;
- filtrage de la gratuité ;
- seuil minimal de pertinence configurable ;
- reconstruction de l'index ;
- endpoint `/health` exposant l'état de l'indexation ;
- API documentée automatiquement avec Swagger ;
- tests automatisés et évaluation fonctionnelle sur l'API déployée.

## Architecture

```text
Question utilisateur
        │
        ▼
Analyse de la requête
        │
        ▼
Extraction des contraintes
(date • catégorie/genre • gratuité)
        │
        ▼
Filtrage des métadonnées
        │
        ▼
Embedding Mistral de la requête
        │
        ▼
Recherche vectorielle FAISS
        │
        ▼
Seuil de pertinence + garde-fous
        │
        ▼
Sélection TOP_K
        │
        ▼
Génération Mistral
        │
        ▼
Réponse FastAPI + sources
```

### Principaux modules

- `app/openagenda.py` : collecte des événements, pagination, déduplication et gestion des données.
- `app/embeddings.py` : génération des embeddings Mistral par lots avec mécanisme de retry.
- `app/indexer.py` : chunking, construction et sauvegarde de l'index FAISS.
- `app/filters.py` : contraintes temporelles et métier.
- `app/rag.py` : retrieval, scores de pertinence, garde-fous et orchestration RAG.
- `app/mistral_client.py` : communication avec Mistral.
- `app/rebuild_manager.py` : gestion de la reconstruction de l'index.
- `app/main.py` : API FastAPI et endpoints.
- `scripts/evaluate_rag.py` : évaluation fonctionnelle du système.
- `tests/` : tests automatisés sans appels réseau réels.

## Structure du dépôt

```text
puls-events-rag/
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── embeddings.py
│   ├── filters.py
│   ├── indexer.py
│   ├── main.py
│   ├── mistral_client.py
│   ├── openagenda.py
│   ├── rag.py
│   └── rebuild_manager.py
├── data/
│   └── eval_dataset.json
├── docs/
│   ├── evaluation_finale.md
│   ├── presentation_plan.md
│   ├── presentation_soutenance.pptx
│   ├── rapport_technique.docx
│   └── rapport_technique.md
├── scripts/
│   ├── evaluate_rag.py
│   ├── rebuild_index.py
│   └── smoke_api.py
├── tests/
│   ├── test_api.py
│   ├── test_filters.py
│   ├── test_openagenda.py
│   ├── test_quality_guards.py
│   └── test_relevance.py
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── README.md
├── VALIDATION.md
├── docker-compose.yml
├── pytest.ini
├── render.yaml
└── requirements.txt
```

Les données récupérées (`data/events.json`), l'index FAISS, les rapports générés et les secrets locaux ne sont pas versionnés.

## Installation locale

Prérequis : Python compatible avec les dépendances du projet.

```bash
git clone https://github.com/fatimaadda2878/puls-events-rag.git
cd puls-events-rag

python -m venv .venv
```

Activation sous Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

Activation sous Git Bash / Linux / macOS :

```bash
source .venv/Scripts/activate
# Linux/macOS : source .venv/bin/activate
```

Installation :

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Créer ensuite le fichier `.env` à partir de `.env.example` et renseigner au minimum :

```env
MISTRAL_API_KEY=...
REBUILD_API_KEY=...
```

Ne jamais versionner le fichier `.env`.

## Configuration principale

Exemple de configuration :

```env
MISTRAL_CHAT_MODEL=mistral-small-latest
MISTRAL_EMBED_MODEL=mistral-embed
MISTRAL_EMBED_BATCH_SIZE=16
MISTRAL_MAX_RETRIES=5

OPENAGENDA_CITY=Paris
OPENAGENDA_PAGE_SIZE=100
OPENAGENDA_MAX_EVENTS=0

INDEX_BATCH_SIZE=32
CHUNK_SIZE=1400
CHUNK_OVERLAP=150
MAX_CHUNKS_PER_EVENT=2

MIN_RELEVANCE_SCORE=0.55
TOP_K=5
CANDIDATE_K=30

AUTO_REBUILD_ON_START=false
```

`OPENAGENDA_MAX_EVENTS=0` permet de ne pas imposer de limite artificielle au nombre d'événements récupérés.

## Lancement local

```bash
uvicorn app.main:app --reload --port 7860
```

Puis ouvrir :

```text
http://localhost:7860/docs
```

## Reconstruction de l'index

En local :

```bash
python scripts/rebuild_index.py
```

Via l'API :

```text
POST /rebuild
X-Rebuild-Key: <REBUILD_API_KEY>
```

La reconstruction est asynchrone. Son état peut être suivi avec :

```text
GET /health
```

Le health check expose notamment l'état de l'index et les compteurs calculés lors de la reconstruction.

## Endpoints

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | État de l'API et de l'index |
| `POST` | `/ask` | Question en langage naturel |
| `POST` | `/rebuild` | Reconstruction de l'index |
| `GET` | `/docs` | Swagger / documentation interactive |

Exemple de requête :

```json
{
  "question": "Quels événements sont proposés à Paris en septembre 2026 ?"
}
```

La réponse contient le texte généré, les sources retenues ainsi que des informations sur le backend et le retrieval.

## Tests automatisés

Lancer la suite :

```bash
python -m pytest -v
```

Les tests couvrent notamment :

- API FastAPI ;
- récupération et traitement OpenAgenda ;
- filtres temporels ;
- pertinence ;
- garde-fous qualité.

Les tests unitaires sont conçus pour ne pas dépendre d'appels réseau réels vers OpenAgenda ou Mistral.

## Évaluation fonctionnelle

L'évaluation finale peut être exécutée directement contre l'API Render :

```bash
py scripts/evaluate_rag.py
```

ou :

```bash
python scripts/evaluate_rag.py
```

Jeu d'évaluation actuel : **10 requêtes**, comprenant des cas positifs et négatifs.

Résultat observé lors de la validation finale :

| Métrique | Résultat |
|---|---:|
| Score global | **100 % (10/10)** |
| Cas positifs | **100 %** |
| Cas négatifs | **100 %** |
| Latence moyenne observée | **2,507 s** |
| Backend | `mistral` |
| Retrieval | `faiss+mistral-embed` |

Ces résultats décrivent uniquement ce jeu d'évaluation de 10 requêtes et ne constituent pas une garantie de performance générale du système.

## CI/CD

Le dépôt contient un workflow GitHub Actions :

```text
.github/workflows/ci.yml
```

Il permet d'automatiser les contrôles du projet à chaque évolution du code selon la configuration du workflow.

## Docker

Construction :

```bash
docker build -t puls-events-rag .
```

Exécution :

```bash
docker run --env-file .env -p 7860:7860 puls-events-rag
```

## Déploiement Render

Le dépôt contient `render.yaml`.

Commande de démarrage :

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Variables importantes à configurer côté Render :

```text
MISTRAL_API_KEY
REBUILD_API_KEY
MISTRAL_CHAT_MODEL
MISTRAL_EMBED_MODEL
MIN_RELEVANCE_SCORE
OPENAGENDA_CITY
OPENAGENDA_MAX_EVENTS
```

### Persistance de l'index

Sur une instance Render sans disque persistant, le système de fichiers est éphémère. L'index reconstruit peut donc être perdu après un redéploiement ou un redémarrage.

Pour une démonstration, vérifier `/health` et reconstruire l'index si nécessaire avant d'utiliser `/ask`.

## Exemple de scénario de démonstration

1. Vérifier `/health`.
2. Ouvrir `/docs`.
3. Reconstruire l'index si `index_ready=false`.
4. Tester une requête positive.
5. Tester une requête négative, par exemple un genre absent.
6. Montrer les sources et scores retournés.
7. Lancer `python -m pytest -v`.
8. Lancer `py scripts/evaluate_rag.py`.

## Sécurité

- aucune clé API ne doit être commitée ;
- `.env` est ignoré par Git ;
- `/rebuild` est protégé par `REBUILD_API_KEY` ;
- les secrets de production doivent rester dans les variables d'environnement Render / GitHub.

## Limites et pistes d'amélioration

Ce projet est un POC. Les évolutions possibles comprennent :

- élargissement du jeu d'évaluation ;
- calibration plus robuste du seuil de pertinence ;
- métriques RAG plus complètes ;
- stockage persistant de l'index ;
- observabilité et monitoring ;
- optimisation de la latence ;
- amélioration des filtres sémantiques et temporels.

## Auteur

**Fatima Adda**

Projet réalisé dans le cadre de la formation **OpenClassrooms — Data Scientist**.
