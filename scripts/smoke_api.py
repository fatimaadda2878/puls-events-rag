import os
import sys

import requests

BASE = os.getenv("API_URL", "http://localhost:7860").rstrip("/")

health = requests.get(f"{BASE}/health", timeout=30)
health.raise_for_status()
print("HEALTH:", health.json())

if not health.json().get("index_ready"):
    print("Index absent : /ask n'est pas testé.")
    sys.exit(0)

response = requests.post(
    f"{BASE}/ask",
    json={"question": "Quels événements culturels à Paris cette semaine ?"},
    timeout=90,
)
response.raise_for_status()
print("ASK:", response.json())
