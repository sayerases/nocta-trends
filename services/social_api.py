import asyncio
from typing import List, Dict, Any
from services import rapidapi_service

class SocialAPIWrapper:
    """Simplified wrapper that just passes through to the new massive concurrent fetcher."""
    def __init__(self):
        self.rapidapi = rapidapi_service

    async def search_trends(self, query: str, timeframe: str = "all", sort_by: str = "views") -> List[Dict[str, Any]]:
        days = None
        if timeframe in ["24h", "1d"]: days = 1
        elif timeframe == "3d": days = 3
        elif timeframe in ["7d", "week"]: days = 7
        elif timeframe in ["30d", "month"]: days = 30
        
        # Call the new async concurrent function directly, fetch up to 100 reels
        results = await self.rapidapi.search_reels_by_keyword_async(
            query, 
            count=100, 
            timeframe_days=days, 
            sort_by=sort_by
        )
        return results
