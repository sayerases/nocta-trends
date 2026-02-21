import os
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "instagram120.p.rapidapi.com"

HEADERS = {
    "Content-Type": "application/json",
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY,
}

# Massively expanded seed accounts to guarantee 100-200+ Reels per fetch
HASHTAG_TO_ACCOUNTS = {
    # Luxury / Fashion / Lifestyle
    "luxury": ["thelaferrari", "rollsroyce", "lamborghini", "louisvuitton", "chanel", "rolex", "bugatti", "porsche", "ferrari", "mansion", "billionaire_lifestyle", "luxurylifestyle", "bentley", "richkids", "yacht"],
    "fashion": ["zara", "hm", "gucci", "dior", "prada", "vogue", "balenciaga", "versace", "burberry", "givenchy", "fendi", "armani", "dolcegabbana", "calvinklein", "tommyhilfiger"],
    "style": ["voguerunway", "fashionnova", "gq", "hypebeast", "highsnobiety", "mensfashion", "ootd", "streetwear", "snobshots"],
    # Business / Marketing
    "business": ["forbes", "entrepreneur", "incmagazine", "garyvee", "grantcardone", "tonyrobbins", "businessinsider", "hbr", "wsj", "bloomberg", "successmagazine", "millionaire_mentor", "investopedia"],
    "marketing": ["forbes", "entrepreneur", "garyvee", "socialmediamarketing", "digitalmarketing", "marketing", "businessinsider"],
    "finance": ["wsj", "bloomberg", "investopedia", "cnbc", "financialtimes", "yahoo_finance"],
    # Art / Creative
    "art": ["art", "artist", "drawing", "painting", "procreate", "digitalart", "artstationhq", "dailyart"],
    "design": ["designboom", "dezeen", "archdigest", "interiordesign", "graphicdesign", "logodesign"],
    # Gaming / Entertainment
    "gaming": ["ign", "gamespot", "polygon", "kotaku", "gamer", "gaming", "playstation", "xbox", "nintendo"],
    # Tech / Future
    "tech": ["mkbhd", "apple", "googlenews", "verge", "wired", "techcrunch", "engadget", "cnet", "mashable", "gadgetmactv", "unboxtherapy", "mrwhosetheboss", "linustech", "marquesbrownlee", "ijustine"],
    "ai": ["openai", "midjourney", "chatgpt", "artificialintelligence", "machinelearning", "deeplearning"],
    "crypto": ["cryptotraderz", "binance", "coinbase", "ethereum", "bitcoin", "crypto", "nft", "web3", "cryptonews"],
    # Fitness / Health
    "fitness": ["nike", "gymshark", "adidas", "underarmour", "reebok", "pumaperformance", "crossfit", "menshealth", "womenshealth", "bodybuilding", "fitnessmotivation", "gym", "workout", "chrisbumstead", "davidlaid"],
    "gym": ["gymshark", "alphalete", "ryderwear", "goldsgym", "planetfitness", "equinox"],
    # Food / Cooking
    "food": ["tasty", "buzzfeedtasty", "foodnetwork", "gordonramsay", "jamieoliver", "food52", "eater", "bonappetit", "seriouseats", "tastemade", "foodporn", "instafood", "yummy"],
    "cooking": ["tasty", "nytfood", "bbcgoodfood", "chefsteps", "epicurious"],
    # Travel / Nature
    "travel": ["natgeo", "earthpix", "beautifuldestinations", "lonelyplanet", "cntraveler", "travelchannel", "natgeotravel", "bucketlist", "wonderful_places", "bestvacations", "travelgram", "wanderlust", "roamtheplanet"],
    "nature": ["natgeowild", "discoverearth", "nature", "earthfocus", "ourplanetdaily", "wildlifeplanet"],
    # Business / Motivation
    "business": ["forbes", "entrepreneur", "incmagazine", "garyvee", "grantcardone", "tonyrobbins", "businessinsider", "hbr", "wsj", "bloomberg", "successmagazine", "millionaire_mentor", "investopedia"],
    "motivation": ["foundrmagazine", "quotes", "mindset", "hustle", "grind", "wealth", "leadership"],
    # Default (General Viral)
    "default": ["instagram", "creators", "9gag", "pubity", "complex", "meme", "viral", "trending", "tiktok", "reels", "funny", "comedy", "lmao", "epic", "wow"],
}

def _pick_accounts(query: str, max_accounts=15) -> List[str]:
    """Pick up to max_accounts seed accounts based on the search query."""
    q = query.lower().replace("#", "").strip()
    accounts = []
    
    # Check words in query
    for key, accs in HASHTAG_TO_ACCOUNTS.items():
        if key in q or q in key:
            accounts.extend(accs)
            
    if not accounts:
        accounts = HASHTAG_TO_ACCOUNTS["default"]
        
    import random
    # Return a random sample of max_accounts to ensure variety across searches
    return random.sample(accounts, min(len(accounts), max_accounts))

def _is_within_timeframe(taken_at: Optional[int], days: Optional[int]) -> bool:
    if not days or not taken_at:
        return True
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        post_time = datetime.fromtimestamp(taken_at, tz=timezone.utc)
        return post_time >= cutoff
    except Exception:
        return True

def fetch_reels_from_account_sync(username: str, timeframe_days: Optional[int]) -> List[Dict[str, Any]]:
    """Fetch reels for a single account synchronously."""
    results = []
    try:
        resp = requests.post(
            f"https://{RAPIDAPI_HOST}/api/instagram/reels",
            headers=HEADERS,
            json={"username": username, "maxId": ""},
            timeout=10, # Fast timeout to not block
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        
        edges = data.get("result", {}).get("edges", [])
        if edges:
            items = [edge.get("node", {}).get("media") or edge.get("node", {}) for edge in edges]
        else:
            items = data if isinstance(data, list) else data.get("items", data.get("data", []))
            
        if not items or not isinstance(items, list):
            return []

        for item in items:
            if not isinstance(item, dict):
                continue
                
            taken_at = item.get("taken_at") or item.get("takenAt") or item.get("device_timestamp")
            if not _is_within_timeframe(taken_at, timeframe_days):
                continue

            likes = int(item.get("like_count") or item.get("likeCount") or 0)
            comments = int(item.get("comment_count") or item.get("commentCount") or 0)
            
            # play_count might not be present, fallback to view_count
            views = item.get("play_count") or item.get("playCount") or item.get("view_count") or item.get("viewCount")
            if views is None: views = likes * 3 # rough estimate if fully missing
            views = int(views)
            
            er = round(((likes + comments) / max(views, 1)) * 100, 2)

            thumb = ""
            image_versions = item.get("image_versions2") or item.get("imageVersions2") or {}
            candidates = image_versions.get("candidates", [])
            if candidates:
                thumb = candidates[0].get("url", "")

            code = item.get("code") or item.get("shortCode") or ""
            video_url = f"https://www.instagram.com/reel/{code}/" if code else f"https://www.instagram.com/{username}/"

            published_at = ""
            if taken_at:
                try:
                    published_at = datetime.fromtimestamp(taken_at).isoformat()
                except Exception:
                    pass

            caption_data = item.get("caption") or {}
            caption_text = caption_data.get("text", "") if isinstance(caption_data, dict) else (caption_data if isinstance(caption_data, str) else "")

            results.append({
                "platform_id": str(item.get("id", "") or item.get("pk", "")),
                "platform": "instagram",
                "title": caption_text[:150] or f"Reel from @{username}",
                "author": username,
                "views": int(views),
                "likes": int(likes),
                "comments": int(comments),
                "engagement_rate": er,
                "thumbnail_url": thumb,
                "video_url": video_url,
                "published_at": published_at,
                "transcript": caption_text,
            })
    except Exception as e:
        print(f"Error fetching from @{username}: {e}")
    return results

async def search_reels_by_keyword_async(
    query: str, count: int = 100, timeframe_days: Optional[int] = None, sort_by: str = "views"
) -> List[Dict[str, Any]]:
    """
    Massive Concurrent Reels Fetcher.
    Picks ~15 seed accounts based on keyword and fetches their reels concurrently.
    Guarantees massive volume quickly.
    """
    if not RAPIDAPI_KEY:
        print("WARNING: RAPIDAPI_KEY is not set.")
        return []

    accounts = _pick_accounts(query, max_accounts=20)
    all_results = []
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Schedule all account fetches concurrently
        tasks = [
            loop.run_in_executor(executor, fetch_reels_from_account_sync, username, timeframe_days)
            for username in accounts
        ]
        
        # Wait for all to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for br in batch_results:
            if isinstance(br, list):
                all_results.extend(br)

    # Keyword post-filtering: if the query is specific, weed out irrelevant reels
    # Default tags are "viral trending wow epic". We don't filter those.
    query_lower = query.lower().strip()
    if query_lower and query_lower not in ["viral trending wow epic", "viral", "trending", "wow", "epic", ""]:
        filtered = []
        words = set(query_lower.replace("#", "").split())
        for r in all_results:
            text_corpus = ((r.get("transcript") or "") + " " + (r.get("author") or "")).lower()
            # If any word from the query is in the transcript/author
            if any(w in text_corpus for w in words):
                filtered.append(r)
        
        # If strict filtering returns almost nothing, maybe the query is conceptually matched by seed accounts,
        # so we relax it (just return all_results from seed accounts) if we have < 5 results.
        if len(filtered) >= 5:
            all_results = filtered

    # Sort the massive pool of reels
    if sort_by == "views":
        all_results.sort(key=lambda x: x["views"], reverse=True)
    elif sort_by == "er":
        all_results.sort(key=lambda x: x["engagement_rate"], reverse=True)
    elif sort_by == "likes":
        all_results.sort(key=lambda x: x["likes"], reverse=True)
    elif sort_by == "recent":
        all_results.sort(key=lambda x: x["published_at"] or "", reverse=True)

    return all_results[:count]

# Synchronous wrapper if needed anywhere else
def search_reels_by_keyword(*args, **kwargs):
    return asyncio.run(search_reels_by_keyword_async(*args, **kwargs))
