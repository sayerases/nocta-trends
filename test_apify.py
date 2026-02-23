import asyncio
from services.instagram_service import InstagramService

def run():
    svc = InstagramService()
    res = svc.search_by_hashtag("#motiondesign", count=5, timeframe_days=30)
    print(f"Found {len(res)} reels.")
    if res:
        print(res[0].get("title"))

run()
