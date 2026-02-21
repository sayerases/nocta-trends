import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

def debug_reels_scraper(hashtag):
    run_input = {
        "hashtags": [hashtag],
        "resultsLimit": 10,
        "resultsType": "reels"   # Correct key found!
    }
    
    print(f"Running scraper for # {hashtag} with resultsType='reels'...")
    run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
    
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if items:
        print(f"Found {len(items)} items.")
        for i, item in enumerate(items):
            print(f"Item {i}: type={item.get('type')}, productType={item.get('productType')}, shortCode={item.get('shortCode')}")
    else:
        print("No items found.")

if __name__ == "__main__":
    debug_reels_scraper("luxury")
