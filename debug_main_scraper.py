import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

def debug_main_scraper(hashtag):
    # Trying the main instagram-scraper which is more robust
    run_input = {
        "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag}/"],
        "resultsLimit": 5,
        "resultsType": "posts"
    }
    
    print(f"Running main scraper for # {hashtag}...")
    # This might take longer but results are usually better
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)
    
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if items:
        print(f"Found {len(items)} items.")
        print("First item full JSON:")
        print(json.dumps(items[0], indent=2))
    else:
        print("No items found.")

if __name__ == "__main__":
    debug_main_scraper("luxury")
