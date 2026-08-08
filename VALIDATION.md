# Validation avant livraison

- Tous les fichiers Python passent `compileall`.
- Les tests de pagination OpenAgenda et de filtrage temporel/genre ont été exécutés localement : 6/6 passent.
- Les tests FastAPI/FAISS/Mistral sont prévus dans `tests/` et seront exécutés par GitHub Actions après installation de `requirements.txt`.
- Aucun appel réseau réel vers OpenAgenda ou Mistral n'est effectué dans la CI.
- La version Python est fixée à 3.11 (`.python-version`) afin d'éviter le changement de runtime Render observé en Python 3.14.
- L'import Mistral est compatible SDK v1 et v2.
- `/rebuild` répond 202 immédiatement et lance la reconstruction dans un thread séparé.
- La récupération OpenDataSoft utilise `/records` tant que la pagination est sûre puis `/exports/csv` en streaming au-delà de 10 000 résultats.
- L'index est construit par lots et remplacé atomiquement uniquement après succès complet.
