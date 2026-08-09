# Résultats finaux d'évaluation

L'évaluation a été exécutée contre l'API Render déployée.

- Questions évaluées : 10
- Score global : 100 %
- Cas positifs : 100 %
- Cas négatifs : 100 %
- Latence moyenne : 2,155 s
- Backend : Mistral
- Retrieval : FAISS + mistral-embed

## Interprétation

Validation finale effectuée après reconstruction automatique de l’index sur Render : index_ready=true, 9 495 événements indexés, évaluation fonctionnelle 10/10 réussie.

La validation technique séparée avec pytest donne 15 tests réussis sur 15.
