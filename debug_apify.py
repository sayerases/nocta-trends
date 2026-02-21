import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

def debug_scraper(hashtag):
    run_input = {
        "hashtags": [hashtag],
        "resultsLimit": 10,
    }
    
    print(f"Running scraper for #{hashtag}...")
    run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
    print(f"Run finished. Dataset ID: {run['defaultDatasetId']}")
    
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    for i, item in enumerate(items):
        print(f"Item {i}: type={item.get('type')}, isVideo={item.get('isVideo')}, caption={item.get('caption', '')[:30]}...")

if __name__ == "__main__":
    debug_scraper("reels")
