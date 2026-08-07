import os, requests
base=os.getenv("API_URL","http://localhost:7860")
print(requests.get(base+"/health",timeout=10).json())
print(requests.post(base+"/ask",json={"question":"Quels événements culturels à Paris ?"},timeout=60).json())
