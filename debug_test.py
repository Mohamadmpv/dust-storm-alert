from config import * 
import requests, json 
print("BALE_TOKEN:", "OK" if BALE_TOKEN else "MISSING") 
print("TELEGRAM_TOKEN:", "OK" if TELEGRAM_TOKEN else "MISSING") 
print("GIST_ID:", GIST_ID) 
print("GH_PAT:", "OK" if GH_PAT else "MISSING") 
r = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers={"Authorization": f"token {GH_PAT}"}) 
users = json.loads(r.json()["files"]["users.json"]["content"]) if "users.json" in r.json()["files"] else {} 
print("Users in Gist:", len(users), users) 
