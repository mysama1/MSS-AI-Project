#!/usr/bin/env python3
"""
MSS-VDP 速率限制器 + 健康检查中间件
用于 skill_api.py (FastAPI on port 53000)
"""
import time, threading
from collections import defaultdict
from typing import Dict, Tuple


class TokenBucket:
    """令牌桶速率限制器"""
    
    def __init__(self, rate: float, burst: int):
        self.rate = rate          # tokens per second
        self.burst = burst        # max burst size
        self.tokens = burst
        self.last = time.monotonic()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter:
    """IP-based rate limiting middleware for FastAPI"""
    
    def __init__(self, 
                 default_rate: float = 10.0,    # 10 req/s default
                 default_burst: int = 20,       # burst 20
                 scan_rate: float = 1.0,         # 1 scan/s (expensive)
                 scan_burst: int = 3):
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.scan_rate = scan_rate
        self.scan_burst = scan_burst
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()
        # Track stats
        self.total_requests = 0
        self.blocked_requests = 0
        self.start_time = time.monotonic()
    
    def _get_bucket(self, key: str, rate: float, burst: int) -> TokenBucket:
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(rate, burst)
            return self.buckets[key]
    
    def check(self, client_ip: str, endpoint_type: str = "default") -> Tuple[bool, dict]:
        """Returns (allowed, stats_dict)"""
        self.total_requests += 1
        
        if endpoint_type in ("scan", "audit", "pipeline"):
            bucket = self._get_bucket(client_ip, self.scan_rate, self.scan_burst)
        else:
            bucket = self._get_bucket(client_ip, self.default_rate, self.default_burst)
        
        allowed = bucket.consume(1)
        if not allowed:
            self.blocked_requests += 1
        
        uptime = time.monotonic() - self.start_time
        return allowed, {
            "total_requests": self.total_requests,
            "blocked": self.blocked_requests,
            "uptime_sec": round(uptime, 0),
            "avg_rps": round(self.total_requests / max(1, uptime), 2),
        }
    
    def status(self) -> dict:
        uptime = time.monotonic() - self.start_time
        active_ips = len(self.buckets)
        return {
            "enabled": True,
            "active_clients": active_ips,
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "uptime_hours": round(uptime / 3600, 2),
            "avg_rps": round(self.total_requests / max(1, uptime), 2),
            "default_burst": self.default_burst,
            "scan_burst": self.scan_burst,
        }


# ── FastAPI middleware integration ──

_limiter: RateLimiter = None

def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


# Usage in skill_api.py:
#   from rate_limiter import get_limiter
#   limiter = get_limiter()
#
#   @app.get("/vdp/status")
#   async def vdp_status(request: Request):
#       allowed, stats = limiter.check(request.client.host, "default")
#       if not allowed:
#           raise HTTPException(429, "Rate limit exceeded")
#       return {"status": "ok", **stats}
