"""
Unit tests for Rate Limiter.

Tests the token bucket algorithm, blocking behavior, and timeout handling.
Critical: Tests must not block - all use timeouts and non-blocking mode.
"""

import pytest
import time
import threading

from backend.core.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    check_rate_limit,
    DEFAULT_LIMITS,
)


class TestRateLimiterBasics:
    """Basic rate limiter functionality tests."""

    def test_init_default_limits(self):
        """Rate limiter initializes with default limits."""
        limiter = RateLimiter()

        assert limiter.limits["ollama"] == 60
        assert limiter.limits["openai"] == 10
        assert limiter.limits["default"] == 10

    def test_init_custom_limits(self):
        """Rate limiter accepts custom limits."""
        limiter = RateLimiter({"test_provider": 100})

        assert limiter.limits["test_provider"] == 100
        assert limiter.limits["openai"] == 10  # Still has defaults

    def test_acquire_immediately_available(self):
        """First request should be immediately available."""
        limiter = RateLimiter({"test": 10})

        result = limiter.acquire("test", block=False)

        assert result is True

    def test_acquire_multiple_within_limit(self):
        """Multiple requests within limit succeed."""
        limiter = RateLimiter({"test": 10})

        for i in range(5):
            result = limiter.acquire("test", block=False)
            assert result is True, f"Request {i+1} should succeed"

    def test_acquire_exceeds_limit_non_blocking(self):
        """Requests exceeding limit return False in non-blocking mode."""
        limiter = RateLimiter({"test": 3})

        # Exhaust tokens
        for _ in range(3):
            limiter.acquire("test", block=False)

        # Should be rate limited
        result = limiter.acquire("test", block=False)
        assert result is False


class TestTokenBucketAlgorithm:
    """Tests for the token bucket algorithm mechanics."""

    def test_tokens_refill_over_time(self):
        """Tokens should refill based on elapsed time."""
        limiter = RateLimiter({"test": 60})  # 1 token per second

        # Exhaust all tokens
        for _ in range(60):
            limiter.acquire("test", block=False)

        # Should be empty
        assert limiter.acquire("test", block=False) is False

        # Wait for 1+ token to refill
        time.sleep(1.1)

        # Should have at least 1 token now
        assert limiter.acquire("test", block=False) is True

    def test_refill_rate_calculation(self):
        """Refill rate should be tokens per second."""
        limiter = RateLimiter({"test": 120})  # 2 tokens per second
        bucket = limiter._get_bucket("test")

        assert bucket["refill_rate"] == 2.0  # 120/60 = 2

    def test_tokens_capped_at_max(self):
        """Tokens should not exceed max even with long idle time."""
        limiter = RateLimiter({"test": 10})

        # Simulate time passing
        bucket = limiter._get_bucket("test")
        bucket["last_update"] = time.time() - 3600  # 1 hour ago

        # Refill
        limiter._refill_tokens(bucket)

        # Should be capped at max
        assert bucket["tokens"] == 10


class TestAcquireBlocking:
    """Tests for blocking acquire behavior."""

    @pytest.mark.timeout(5)
    def test_acquire_blocks_until_tokens(self):
        """Acquire with block=True waits for tokens."""
        limiter = RateLimiter({"test": 60})  # 1 token/sec

        # Use all tokens
        for _ in range(60):
            limiter.acquire("test", block=False)

        # Should block briefly then succeed
        start = time.time()
        result = limiter.acquire("test", block=True, timeout=2.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.5  # Should have waited
        assert elapsed < 2.0  # But not timed out

    @pytest.mark.timeout(3)
    def test_acquire_timeout_exceeded(self):
        """Acquire returns False when timeout exceeded."""
        # Very slow refill rate
        limiter = RateLimiter({"test": 1})  # 1 token per 60 seconds!

        # Use the only token
        limiter.acquire("test", block=False)

        # Should timeout - note: the code checks if elapsed + wait_time > timeout
        # before sleeping, so it may return immediately if wait time is too long
        result = limiter.acquire("test", block=True, timeout=0.5)

        assert result is False  # Rate limited due to timeout


class TestGetWaitTime:
    """Tests for wait time estimation."""

    def test_get_wait_time_immediate(self):
        """Wait time is 0 when tokens available."""
        limiter = RateLimiter({"test": 10})

        wait = limiter.get_wait_time("test")

        assert wait == 0.0

    def test_get_wait_time_after_exhausted(self):
        """Wait time calculated correctly when exhausted."""
        limiter = RateLimiter({"test": 60})  # 1 token/sec

        # Exhaust tokens
        for _ in range(60):
            limiter.acquire("test", block=False)

        wait = limiter.get_wait_time("test")

        # Should need to wait ~1 second for 1 token
        assert 0.5 < wait <= 2.0


class TestGetStatus:
    """Tests for status reporting."""

    def test_get_status_full_bucket(self):
        """Status shows full bucket for new provider."""
        limiter = RateLimiter({"test": 10})

        status = limiter.get_status("test")

        assert status["provider"] == "test"
        assert status["available_tokens"] == 10
        assert status["max_tokens"] == 10
        assert status["requests_per_minute"] == 10
        assert status["wait_time_seconds"] == 0.0

    def test_get_status_partial_bucket(self):
        """Status shows correct values after some usage."""
        limiter = RateLimiter({"test": 10})

        # Use 3 tokens
        for _ in range(3):
            limiter.acquire("test", block=False)

        status = limiter.get_status("test")

        assert status["available_tokens"] == 7

    def test_get_status_no_deadlock(self):
        """get_status should not cause deadlock (regression test)."""
        limiter = RateLimiter({"test": 10})

        # This previously caused deadlock because get_status called get_wait_time
        # which tried to acquire the same lock
        status = limiter.get_status("test")

        assert "wait_time_seconds" in status


class TestSetLimit:
    """Tests for dynamic limit updates."""

    def test_set_limit_new_provider(self):
        """Can set limit for new provider."""
        limiter = RateLimiter()

        limiter.set_limit("new_provider", 50)

        assert limiter.limits["new_provider"] == 50

    def test_set_limit_updates_existing_bucket(self):
        """Setting limit updates existing bucket."""
        limiter = RateLimiter({"test": 10})

        # Create bucket
        limiter.acquire("test", block=False)

        # Update limit
        limiter.set_limit("test", 20)

        bucket = limiter._get_bucket("test")
        assert bucket["max_tokens"] == 20
        assert bucket["refill_rate"] == 20 / 60.0

    def test_set_limit_reduces_current_tokens(self):
        """Reducing limit doesn't exceed new max."""
        limiter = RateLimiter({"test": 100})

        # Create bucket
        limiter.acquire("test", block=False)

        # Reduce limit significantly
        limiter.set_limit("test", 5)

        status = limiter.get_status("test")
        assert status["available_tokens"] <= 5


class TestReset:
    """Tests for reset functionality."""

    def test_reset_single_provider(self):
        """Can reset a single provider."""
        limiter = RateLimiter({"test": 10})

        # Use some tokens
        for _ in range(5):
            limiter.acquire("test", block=False)

        # Reset
        limiter.reset("test")

        # Bucket should be fresh
        status = limiter.get_status("test")
        assert status["available_tokens"] == 10

    def test_reset_all_providers(self):
        """Can reset all providers."""
        limiter = RateLimiter()

        # Use tokens from multiple providers
        limiter.acquire("openai", block=False)
        limiter.acquire("ollama", block=False)

        # Reset all
        limiter.reset()

        # All should be fresh
        assert limiter.get_status("openai")["available_tokens"] == 10
        assert limiter.get_status("ollama")["available_tokens"] == 60


class TestThreadSafety:
    """Tests for thread-safe operation."""

    @pytest.mark.timeout(5)
    def test_concurrent_acquire(self):
        """Multiple threads can acquire safely."""
        limiter = RateLimiter({"test": 1000})
        success_count = [0]
        lock = threading.Lock()

        def worker():
            for _ in range(100):
                if limiter.acquire("test", block=False):
                    with lock:
                        success_count[0] += 1

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 500 should succeed (limit is 1000)
        assert success_count[0] == 500

    @pytest.mark.timeout(5)
    def test_concurrent_mixed_operations(self):
        """Mixed operations don't cause race conditions."""
        limiter = RateLimiter({"test": 100})
        errors = []

        def acquire_worker():
            try:
                for _ in range(50):
                    limiter.acquire("test", block=False)
            except Exception as e:
                errors.append(e)

        def status_worker():
            try:
                for _ in range(50):
                    limiter.get_status("test")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=acquire_worker),
            threading.Thread(target=acquire_worker),
            threading.Thread(target=status_worker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestGlobalRateLimiter:
    """Tests for global rate limiter singleton."""

    def test_get_rate_limiter_singleton(self):
        """get_rate_limiter returns same instance."""
        # Reset global state
        import backend.core.rate_limiter as module

        module._rate_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_check_rate_limit_convenience(self):
        """check_rate_limit convenience function works."""
        import backend.core.rate_limiter as module

        module._rate_limiter = None

        result = check_rate_limit("test", block=False)

        assert result is True


class TestDefaultLimits:
    """Tests for default limit configuration."""

    def test_default_limits_exist(self):
        """All expected providers have default limits."""
        assert "ollama" in DEFAULT_LIMITS
        assert "openai" in DEFAULT_LIMITS
        assert "anthropic" in DEFAULT_LIMITS
        assert "gemini" in DEFAULT_LIMITS
        assert "default" in DEFAULT_LIMITS

    def test_ollama_has_higher_limit(self):
        """Ollama (local) has higher limit than cloud providers."""
        assert DEFAULT_LIMITS["ollama"] > DEFAULT_LIMITS["openai"]

    def test_fallback_to_default(self):
        """Unknown providers use default limit."""
        limiter = RateLimiter()

        status = limiter.get_status("unknown_provider")

        assert status["requests_per_minute"] == DEFAULT_LIMITS["default"]
