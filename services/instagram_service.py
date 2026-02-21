import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

class InstagramService:
    """Service for interacting with Instagram data via Apify."""
    
    def __init__(self):
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            print("WARNING: APIFY_API_TOKEN is missing. Scraper will return mock data.")
            self.client = None
        else:
            print("Apify Client Initialized")
            self.client = ApifyClient(self.api_token)
            
    def _is_within_timeframe(self, timestamp_str: str, days: Optional[int]) -> bool:
        """Helper to check if a post is within the requested timeframe."""
        if not days or not timestamp_str:
            return True
            
        try:
            # Apify returns timestamps like '2023-10-25T14:30:00.000Z'
            post_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            return post_time >= cutoff
        except Exception:
            return True
        
    def search_by_hashtag(self, hashtag: str, count: int = 15, timeframe_days: int = None, sort_by: str = "views") -> List[Dict[str, Any]]:
        """
        Searches Instagram via Apify for a specific hashtag.
        """
        if not self.client:
             print("Apify token not configured. Returning empty list.")
             return []

        # Clean hashtag
        clean_target = hashtag.replace("#", "")
        
        # Prepare the Actor input based on apify/instagram-hashtag-scraper schema
        run_input = {
            "hashtags": [clean_target],
            "resultsLimit": count * 5,
            "resultsType": "reels",  # CRITICAL: Force scraper to target the Reels feed
        }
        
        print(f"Starting Apify Hashtag Scraper for #{clean_target}...")
        results = []
        try:
            # Run the Actor and wait for it to finish
            run = self.client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
            
            # Fetch and process results from the dataset
            dataset_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            
            for post_item in dataset_items:
                if not isinstance(post_item, dict):
                    continue
                    
                # We only want Reels (Videos) as requested by user
                item_type = post_item.get("type", "")
                is_video = post_item.get("isVideo", False)
                if not is_video and item_type != "Video":
                    continue
                
                # Timestamp parsing
                timestamp_str = post_item.get("timestamp")
                if not timestamp_str:
                    timestamp_str = datetime.now().isoformat()
                    
                # Timeframe Filter
                if not self._is_within_timeframe(timestamp_str, timeframe_days):
                    continue
                    
                # Process engagement metrics
                likes = post_item.get("likesCount", 0)
                comments = post_item.get("commentsCount", 0)
                
                # Try to get views, fallback to extrapolated likes if image or missing
                views = post_item.get("videoViewCount", post_item.get("videoPlayCount", likes * 3))
                
                # Approximate ER
                er = round(((likes + comments) / views * 100), 2) if views and views > 0 else 0.0

                results.append({
                    "platform_id": post_item.get("id", ""),
                    "platform": "instagram",
                    "title": post_item.get("caption", f"Post for #{clean_target}") or f"Post for #{clean_target}",
                    "author": post_item.get("ownerUsername", "unknown"),
                    "views": views,
                    "likes": likes,
                    "engagement_rate": er,
                    "thumbnail_url": post_item.get("displayUrl", ""),
                    "video_url": post_item.get("url", f"https://www.instagram.com/p/{post_item.get('shortCode')}/"),
                    "published_at": timestamp_str,
                    "transcript": post_item.get("caption", "") or "", # Use caption as transcript fallback
                })
                
                if len(results) >= count:
                    break
        except Exception as e:
            print(f"Apify scraping error: {e}")
            return []

        # Sorting
        if sort_by == "views":
            results.sort(key=lambda x: x["views"], reverse=True)
        elif sort_by == "er":
            results.sort(key=lambda x: x["engagement_rate"], reverse=True)
        elif sort_by == "likes":
            results.sort(key=lambda x: x["likes"], reverse=True)
            
        print(f"Extracted {len(results)} valid Reels from Apify.")
        return results

# Global instance
instagram_service = InstagramService()

