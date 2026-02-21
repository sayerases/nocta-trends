import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

def debug_scraper(hashtag):
    run_input = {
        "hashtags": [hashtag],
        "resultsLimit": 5,
    }
    
    print(f"Running scraper for #{hashtag}...")
    run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
    
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if items:
        print("First item keys:", items[0].keys())
        print("First item full JSON:")
        print(json.dumps(items[0], indent=2))
    else:
        print("No items found.")

if __name__ == "__main__":
    debug_scraper("luxury")
