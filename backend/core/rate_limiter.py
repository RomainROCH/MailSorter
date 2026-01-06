"""
Rate limiting for LLM API calls.

Prevents API cost explosion and respects provider rate limits.
Uses a token bucket algorithm for smooth rate limiting.
"""

import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default limits per provider (requests per minute)
DEFAULT_LIMITS = {
    "ollama": 60,      # Local, can be higher
    "openai": 10,      # Conservative for API costs
    "anthropic": 10,
    "gemini": 10,
    "default": 10,
}


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Thread-safe implementation that tracks requests per provider.
    """
    
    def __init__(self, limits: Optional[Dict[str, int]] = None):
        """
        Initialize rate limiter.
        
        Args:
            limits: Dict mapping provider names to requests per minute.
                   Falls back to DEFAULT_LIMITS for unknown providers.
        """
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self._buckets: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def _get_bucket(self, provider: str) -> Dict:
        """Get or create token bucket for provider."""
        if provider not in self._buckets:
            limit = self.limits.get(provider, self.limits["default"])
            self._buckets[provider] = {
                "tokens": limit,
                "max_tokens": limit,
                "last_update": time.time(),
                "refill_rate": limit / 60.0,  # tokens per second
            }
        return self._buckets[provider]
    
    def _refill_tokens(self, bucket: Dict) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + elapsed * bucket["refill_rate"]
        )
        bucket["last_update"] = now
    
    def acquire(self, provider: str, tokens: int = 1, block: bool = True, timeout: float = 30.0) -> bool:
        """
        Acquire tokens for an API call.
        
        Args:
            provider: Provider name
            tokens: Number of tokens to acquire (usually 1)
            block: If True, wait for tokens. If False, return immediately.
            timeout: Maximum time to wait in seconds (only if block=True)
        
        Returns:
            True if tokens acquired, False if rate limited
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                bucket = self._get_bucket(provider)
                self._refill_tokens(bucket)
                
                if bucket["tokens"] >= tokens:
                    bucket["tokens"] -= tokens
                    return True
                
                if not block:
                    logger.warning(f"Rate limit exceeded for {provider}")
                    return False
                
                # Calculate wait time
                tokens_needed = tokens - bucket["tokens"]
                wait_time = tokens_needed / bucket["refill_rate"]
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed + wait_time > timeout:
                logger.warning(f"Rate limit timeout for {provider}")
                return False
            
            # Wait and retry
            time.sleep(min(wait_time, 0.5))
    
    def get_wait_time(self, provider: str, tokens: int = 1) -> float:
        """
        Get estimated wait time for next available slot.
        
        Args:
            provider: Provider name
            tokens: Number of tokens needed
        
        Returns:
            Wait time in seconds (0 if immediately available)
        """
        with self._lock:
            bucket = self._get_bucket(provider)
            self._refill_tokens(bucket)
            
            if bucket["tokens"] >= tokens:
                return 0.0
            
            tokens_needed = tokens - bucket["tokens"]
            return tokens_needed / bucket["refill_rate"]
    
    def get_status(self, provider: str) -> Dict:
        """
        Get current rate limit status for provider.
        
        Returns:
            Dict with available tokens, max tokens, and wait time
        """
        with self._lock:
            bucket = self._get_bucket(provider)
            self._refill_tokens(bucket)
            
            return {
                "provider": provider,
                "available_tokens": int(bucket["tokens"]),
                "max_tokens": bucket["max_tokens"],
                "requests_per_minute": self.limits.get(provider, self.limits["default"]),
                "wait_time_seconds": self.get_wait_time(provider)
            }
    
    def set_limit(self, provider: str, requests_per_minute: int) -> None:
        """
        Update rate limit for a provider.
        
        Args:
            provider: Provider name
            requests_per_minute: New limit
        """
        with self._lock:
            self.limits[provider] = requests_per_minute
            if provider in self._buckets:
                bucket = self._buckets[provider]
                bucket["max_tokens"] = requests_per_minute
                bucket["refill_rate"] = requests_per_minute / 60.0
                # Don't reduce current tokens below new max
                bucket["tokens"] = min(bucket["tokens"], requests_per_minute)
        
        logger.info(f"Rate limit for {provider} set to {requests_per_minute} req/min")
    
    def reset(self, provider: Optional[str] = None) -> None:
        """
        Reset rate limiter state.
        
        Args:
            provider: If specified, reset only that provider. Otherwise reset all.
        """
        with self._lock:
            if provider:
                if provider in self._buckets:
                    del self._buckets[provider]
            else:
                self._buckets.clear()


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(provider: str, block: bool = True) -> bool:
    """
    Convenience function to check rate limit.
    
    Args:
        provider: Provider name
        block: Whether to wait for available slot
    
    Returns:
        True if allowed, False if rate limited
    """
    return get_rate_limiter().acquire(provider, block=block)
