"""
MSS Symbolic Engine v4.0 - Query Cache
Simple LRU cache for query results
"""

from collections import OrderedDict
from typing import Dict, Any, Optional
import hashlib
import json

class QueryCache:
    """LRU cache for query results"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hit_count = 0
        self.miss_count = 0
    
    def _make_key(self, query_type: str, params: Dict) -> str:
        """Create cache key from query parameters"""
        key_data = json.dumps({"type": query_type, "params": params}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query_type: str, params: Dict) -> Optional[Any]:
        """Get cached result"""
        key = self._make_key(query_type, params)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hit_count += 1
            return self.cache[key]
        
        self.miss_count += 1
        return None
    
    def set(self, query_type: str, params: Dict, result: Any):
        """Cache result"""
        key = self._make_key(query_type, params)
        
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = result
        self.cache.move_to_end(key)
    
    def invalidate(self, query_type: str = None):
        """Invalidate cache entries"""
        if query_type:
            # Remove entries for specific query type
            keys_to_remove = [
                k for k, v in self.cache.items()
                if json.loads(v).get("type") == query_type
            ]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Clear all
            self.cache.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 3)
        }
