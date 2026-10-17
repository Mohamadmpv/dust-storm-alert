import os

token = os.getenv("BALE_TOKEN")

if not token:
    print("BALE_TOKEN is EMPTY or NOT SET")
elif ":" not in token:
    print("BALE_TOKEN has NO COLON (:)")
    print("Length:", len(token))
    print("First 10:", token[:10])
elif len(token) < 20:
    print("BALE_TOKEN is TOO SHORT")
    print("Length:", len(token))
    print("First 10:", token[:10])
else:
    parts = token.split(":")
    print("BALE_TOKEN looks valid")
    print("Length:", len(token))
    print("Part 1 (ID):", parts[0])
    print("Part 2 length:", len(parts[1]))
    print("First 5 of part 1:", parts[0][:5])