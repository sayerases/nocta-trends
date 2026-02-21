import time
from typing import Any, Dict

class TTLCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl_seconds: int = 600):
        """Set a value in the cache with a Time-To-Live in seconds (default 10 mins)."""
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }

    def get(self, key: str) -> Any:
        """Get a value from the cache, if it exists and is not expired. Return None otherwise."""
        item = self._cache.get(key)
        if not item:
            return None
        
        if time.time() > item["expires_at"]:
            # Expired
            del self._cache[key]
            return None
            
        return item["value"]

    def clear(self):
        self._cache.clear()

# Global cache instance
app_cache = TTLCache()
