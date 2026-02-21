import requests
from services.rapidapi_service import RAPIDAPI_HOST, HEADERS
resp = requests.post(
    f"https://{RAPIDAPI_HOST}/api/instagram/reels",
    headers=HEADERS,
    json={"username": "therock", "maxId": ""}
)
print("Status:", resp.status_code)
print("Text:", resp.text[:500])
