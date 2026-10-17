import os

token = os.getenv("BALE_TOKEN")
print("BALE_TOKEN is:", repr(token))
print("Length:", len(token) if token else 0)
print("Is None:", token is None)