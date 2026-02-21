import asyncio
import os
from services.instagram_service import instagram_service
from dotenv import load_dotenv

load_dotenv()

async def test_search():
    token = os.getenv("APIFY_API_TOKEN")
    print(f"Token loaded: {'Yes' if token else 'No'}")
    
    if not token:
        print("Please add APIFY_API_TOKEN to .env")
        return

    print("Executing search for #luxury...")
    try:
        results = instagram_service.search_by_hashtag("luxury", count=3)
        print(f"Found {len(results)} results.")
        for r in results:
             print(f"- {r['platform_id']}: {r['author']} ({r['views']} views, ER: {r['engagement_rate']}%)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
