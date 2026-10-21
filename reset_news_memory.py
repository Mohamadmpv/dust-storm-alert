import requests
import json
from config import GIST_ID, GH_PAT

url = "https://api.github.com/gists/" + str(GIST_ID)
headers = {"Authorization": "token " + str(GH_PAT)}
data = {"files": {"sent_climate_news.json": {"content": "[]"}}}
r = requests.patch(url, headers=headers, json=data, timeout=30)
print("News memory reset!" if r.status_code == 200 else "Error!")