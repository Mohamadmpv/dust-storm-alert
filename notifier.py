def get_all_chat_ids():
    """دریافت همه Chat IDها از Gist + Secrets"""
    chat_ids = []

    # 1. از Gist
    try:
        import requests
        gist_id = os.getenv("GIST_ID")
        gh_pat = os.getenv("GH_PAT")
        if gist_id and gh_pat:
            url = "https://api.github.com/gists/" + gist_id
            headers = {"Authorization": "token " + gh_pat}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            content = r.json()["files"]["users.json"]["content"]
            users = json.loads(content) if content else {}
            for cid in users.keys():
                cid = str(cid).strip()
                if cid and cid not in chat_ids:
                    chat_ids.append(cid)
    except Exception as e:
        print("Gist read error:", e)

    # 2. از BALE_CHAT_IDS (Secrets)
    if BALE_CHAT_IDS:
        for cid in BALE_CHAT_IDS:
            cid = str(cid).strip()
            if cid and cid not in chat_ids:
                chat_ids.append(cid)

    # 3. از BALE_CHAT_ID
    if BALE_CHAT_ID and BALE_CHAT_ID not in chat_ids:
        chat_ids.append(BALE_CHAT_ID)

    print("DEBUG: Total chat_ids =", chat_ids)
    return chat_ids