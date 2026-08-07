# Rapport technique — Assistant intelligent de recommandation d’événements culturels

## 1. Objectifs du projet
Puls-Events souhaite démontrer la faisabilité d'un assistant capable de répondre à des questions sur des événements réels. Le POC cible Paris et les événements récents (moins d'un an) ou à venir. La valeur du RAG est de limiter la génération aux données récupérées plutôt que de laisser le LLM répondre de mémoire.

## 2. Architecture du système
OpenAgenda → pagination/nettoyage → Documents LangChain → `mistral-embed` → FAISS → recherche sémantique + seuil → Mistral Chat → FastAPI.
Technologies : Python 3.11, requests, LangChain, FAISS CPU, SDK Mistral, FastAPI, pytest, Docker.

## 3. Préparation et vectorisation des données
La source est l'API publique OpenAgenda via OpenDataSoft. Le script pagine jusqu'au `total_count`/épuisement, déduplique les événements et filtre ceux terminés depuis plus d'un an. Chaque document contient titre, description, mots-clés, ville, adresse et dates. Les embeddings sont produits par `mistral-embed` par lots et stockés dans FAISS.

## 4. Choix du modèle NLP
La génération utilise `mistral-small-latest` par défaut, configurable. Le choix privilégie une API Mistral native, une latence/coût adaptés au POC et une bonne intégration Python. Le prompt impose de répondre uniquement depuis le contexte et de ne pas inventer d'événement.

## 5. Construction de la base vectorielle
FAISS est utilisé via LangChain avec normalisation L2. L'index est persisté dans `index/faiss/`; `metadata.json` indique le nombre d'événements/documents indexés. Les métadonnées gardent identifiant, titre, ville, adresse, dates et URL.

## 6. API et endpoints exposés
FastAPI expose `GET /health`, `POST /ask`, `POST /rebuild` et Swagger `/docs`. `/rebuild` est protégé par `X-Rebuild-Key`. Les questions vides sont rejetées par validation Pydantic.

## 7. Évaluation du système
Le jeu `data/eval_dataset.json` comprend des cas positifs et négatifs, notamment « Y a-t-il des concerts de reggae à Paris ? ». Le script mesure un taux de réussite global et un taux spécifique aux cas négatifs. Les résultats réels doivent être générés après construction de l'index et copiés ici avant soutenance : **ne pas inventer de métriques**.

## 8. Recommandations et perspectives
Points forts : chaîne réellement sémantique, données réelles, seuil anti-hors-sujet, API testable, Docker. Limites : coût API, calibration du seuil, interprétation temporelle, dépendance réseau lors d'une reconstruction. Perspectives : filtres structurés de dates, reranking, cache, monitoring et reconstruction asynchrone.

## 9. Organisation du dépôt GitHub
Voir `README.md`. Le code métier est séparé de l'API, les scripts de livraison sont isolés, les secrets restent dans l'environnement et les tests sont automatisés par CI.

## 10. Annexes
Prompt : répondre uniquement depuis le contexte récupéré. Exemple négatif : reggae à Paris → aucun résultat si aucun document ne franchit le seuil. Exemple de démo : `/health`, puis `/ask`, puis consultation des sources et scores de pertinence.
