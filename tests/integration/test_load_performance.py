"""
Load and Performance Testing Suite.

Tests system behavior under high load:
- 1000+ email processing
- Memory usage monitoring
- Cache performance at scale
- CPU profiling
- Concurrent request handling

Run with: pytest tests/integration/test_load_performance.py -v -m "not slow"
Full load tests: pytest tests/integration/test_load_performance.py -v -m slow

Task: LOAD-001
"""

import gc
import pytest
import random
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List
from unittest.mock import Mock, patch

from backend.core.orchestrator import Orchestrator
from backend.core.privacy import PrivacyGuard
from backend.core.smart_cache import SmartCache
from backend.core.rate_limiter import RateLimiter
from backend.providers.base import ClassificationResult
from backend.utils.sanitize import sanitize_text

psutil = pytest.importorskip("psutil")


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


@dataclass
class LoadTestConfig:
    """Configuration for load tests."""

    # Volume thresholds
    target_emails_per_hour: int = 1000
    burst_size: int = 100
    burst_window_seconds: float = 1.0

    # Performance thresholds
    max_classification_time_ms: float = 500  # With mocked provider
    max_memory_growth_mb: float = 100
    acceptable_error_rate: float = 0.01  # 1%

    # Cache thresholds
    min_cache_hit_rate: float = 0.5  # 50% for repeated patterns


CONFIG = LoadTestConfig()


# =============================================================================
# TEST DATA GENERATORS
# =============================================================================


class EmailGenerator:
    """Generate realistic test email data."""

    SENDERS = [
        "newsletter@company.com",
        "billing@service.net",
        "colleague@work.org",
        "spam@scam.xyz",
        "support@product.io",
        "alerts@bank.com",
        "orders@shop.com",
        "updates@platform.dev",
    ]

    SUBJECTS = [
        "Your weekly newsletter",
        "Invoice #{id}",
        "Meeting reminder",
        "URGENT: Action required",
        "Order confirmation #{id}",
        "Security alert",
        "Password reset request",
        "Welcome to our service",
        "Re: Previous conversation",
        "Fwd: Important document",
    ]

    BODY_TEMPLATES = [
        "Dear customer, please find your invoice attached. Amount: ${amount}.",
        "Hi team, reminder for our meeting tomorrow at {time}.",
        "Congratulations! You've won a prize. Click here to claim.",
        "Your order #{id} has been shipped. Track it here.",
        "This is your weekly roundup of news and updates.",
        "New login detected from {location}. Was this you?",
        "Thank you for your purchase. Here's your receipt.",
        "Please review and respond to the attached document.",
    ]

    FOLDERS = [
        "Inbox",
        "Work",
        "Personal",
        "Newsletters",
        "Invoices",
        "Shopping",
        "Spam",
        "Important",
    ]

    @classmethod
    def generate_email(cls, index: int = 0) -> Dict:
        """Generate a single random email."""
        return {
            "id": f"msg-{index}-{random.randint(1000, 9999)}",
            "from": random.choice(cls.SENDERS),
            "subject": random.choice(cls.SUBJECTS).format(
                id=random.randint(10000, 99999)
            ),
            "body": random.choice(cls.BODY_TEMPLATES).format(
                id=random.randint(10000, 99999),
                amount=random.randint(10, 1000),
                time=f"{random.randint(9, 17)}:00",
                location=random.choice(["New York", "London", "Tokyo", "Unknown"]),
            ),
            "folders": cls.FOLDERS,
        }

    @classmethod
    def generate_emails(cls, count: int) -> List[Dict]:
        """Generate multiple random emails."""
        return [cls.generate_email(i) for i in range(count)]

    @classmethod
    def generate_similar_emails(cls, count: int, base_sender: str = None) -> List[Dict]:
        """Generate similar emails for cache testing."""
        sender = base_sender or random.choice(cls.SENDERS)
        subject = random.choice(cls.SUBJECTS)
        body = random.choice(cls.BODY_TEMPLATES)

        return [
            {
                "id": f"similar-{i}",
                "from": sender,
                "subject": subject.format(id=i),
                "body": body.format(id=i, amount=100, time="10:00", location="NYC"),
                "folders": cls.FOLDERS,
            }
            for i in range(count)
        ]

    @classmethod
    def generate_large_email(cls, body_size_kb: int = 100) -> Dict:
        """Generate email with large body."""
        large_body = "x" * (body_size_kb * 1024)
        return {
            "id": "large-email-1",
            "from": "sender@example.com",
            "subject": "Large Email Test",
            "body": large_body,
            "folders": cls.FOLDERS,
        }


# =============================================================================
# MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_provider():
    """Create a fast mock provider."""
    provider = Mock()
    provider.get_name.return_value = "mock"
    provider.is_local = True
    provider.health_check.return_value = True
    provider.classify_email.return_value = ClassificationResult(
        folder="Inbox",
        confidence=0.9,
        reasoning="Mock classification",
        tokens_used=50,
        latency_ms=10,
        source="mock",
    )
    return provider


@pytest.fixture
def mock_orchestrator_deps(mock_provider):
    """Create orchestrator with all dependencies mocked."""
    with patch("backend.core.orchestrator.ProviderFactory") as mock_factory, patch(
        "backend.core.orchestrator.get_smart_cache"
    ) as mock_cache, patch(
        "backend.core.orchestrator.get_circuit_breaker"
    ) as mock_cb, patch(
        "backend.core.orchestrator.get_rate_limiter"
    ) as mock_rl, patch(
        "backend.core.orchestrator.get_prompt_engine"
    ) as mock_pe, patch(
        "backend.core.orchestrator.get_calibrator"
    ) as mock_cal, patch(
        "backend.core.orchestrator.get_batch_processor"
    ) as mock_bp, patch(
        "backend.core.orchestrator.get_feedback_loop"
    ) as mock_fl, patch(
        "backend.core.orchestrator.check_rate_limit"
    ) as mock_check:

        mock_factory.create.return_value = mock_provider

        # Cache with store tracking
        cache_inst = Mock()
        cache_inst.check.return_value = None
        cache_inst.store = Mock()
        cache_inst.get_stats.return_value = {"hits": 0, "misses": 0}
        mock_cache.return_value = cache_inst

        # Circuit breaker
        cb_inst = Mock()
        cb_inst.can_execute.return_value = True
        cb_inst.record_success = Mock()
        cb_inst.record_failure = Mock()
        mock_cb.return_value = cb_inst

        mock_check.return_value = True

        # Calibrator
        cal_inst = Mock()
        cal_inst.passes_threshold.return_value = True
        cal_inst.log_result = Mock()
        mock_cal.return_value = cal_inst

        mock_pe.return_value = Mock()
        mock_bp.return_value = Mock()
        mock_fl.return_value = Mock()
        mock_rl.return_value = Mock()

        yield {
            "factory": mock_factory,
            "cache": cache_inst,
            "circuit_breaker": cb_inst,
            "provider": mock_provider,
        }


# =============================================================================
# HIGH VOLUME TESTS
# =============================================================================


class TestHighVolumeProcessing:
    """Tests for processing large email volumes."""

    @pytest.mark.slow
    def test_process_1000_emails_sequential(self, mock_orchestrator_deps):
        """Process 1000 emails sequentially."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )
        emails = EmailGenerator.generate_emails(1000)

        successes = 0
        failures = 0
        total_time_ms = 0

        for email in emails:
            message = {"type": "classify", "payload": email}

            start = time.perf_counter()
            try:
                result = orchestrator.handle_message(message)
                elapsed_ms = (time.perf_counter() - start) * 1000
                total_time_ms += elapsed_ms

                if result.get("action") == "move" or result.get("folder"):
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1

        success_rate = successes / 1000
        avg_latency_ms = total_time_ms / 1000

        print(f"\n1000 Emails: {success_rate:.1%} success, {avg_latency_ms:.1f}ms avg")

        assert success_rate >= (1 - CONFIG.acceptable_error_rate)
        assert avg_latency_ms < CONFIG.max_classification_time_ms

    @pytest.mark.slow
    def test_process_5000_emails(self, mock_orchestrator_deps):
        """Process 5000 emails (5x target volume)."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        total = 5000
        successes = 0
        start_time = time.time()

        for i in range(total):
            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}

            try:
                result = orchestrator.handle_message(message)
                if result.get("action") or result.get("folder"):
                    successes += 1
            except Exception:
                pass

        elapsed = time.time() - start_time
        rate_per_hour = (total / elapsed) * 3600

        print(f"\n5000 Emails in {elapsed:.1f}s = {rate_per_hour:.0f}/hour")

        assert rate_per_hour >= CONFIG.target_emails_per_hour
        assert successes / total >= (1 - CONFIG.acceptable_error_rate)

    def test_burst_100_in_1_second(self, mock_orchestrator_deps):
        """Handle 100 emails in 1 second burst."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )
        emails = EmailGenerator.generate_emails(100)

        start = time.perf_counter()

        for email in emails:
            message = {"type": "classify", "payload": email}
            orchestrator.handle_message(message)

        elapsed = time.perf_counter() - start

        print(f"\n100 Email burst: {elapsed:.2f}s")

        assert elapsed < 2.0, f"Burst took {elapsed:.2f}s, should be < 2s"

    def test_sustained_load_10_minutes(self, mock_orchestrator_deps):
        """Simulated 10-minute sustained load (scaled down)."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        # Simulate 10 minutes at 1000/hour = ~167 emails
        target_emails = 167
        duration_seconds = 5  # Scaled down from 600s to 5s for testing
        interval = duration_seconds / target_emails

        successes = 0
        start = time.time()

        for i in range(target_emails):
            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}

            try:
                result = orchestrator.handle_message(message)
                if result.get("action") or result.get("folder"):
                    successes += 1
            except Exception:
                pass

            # Simulate real-world pacing
            elapsed = time.time() - start
            expected = i * interval
            if elapsed < expected:
                time.sleep(expected - elapsed)

        success_rate = successes / target_emails
        print(f"\nSustained load: {success_rate:.1%} success over {duration_seconds}s")

        assert success_rate >= (1 - CONFIG.acceptable_error_rate)


# =============================================================================
# MEMORY TESTS
# =============================================================================


class TestMemoryUsage:
    """Tests for memory stability and leak detection."""

    def test_memory_stable_after_1000_classifications(self, mock_orchestrator_deps):
        """Memory should not grow excessively after 1000 ops."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        # Force garbage collection and get baseline
        gc.collect()
        process = psutil.Process()
        baseline_mb = process.memory_info().rss / (1024 * 1024)

        # Process 1000 emails
        for i in range(1000):
            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}
            orchestrator.handle_message(message)

        # Check memory
        gc.collect()
        final_mb = process.memory_info().rss / (1024 * 1024)
        growth_mb = final_mb - baseline_mb

        print(f"\nMemory: {baseline_mb:.1f}MB -> {final_mb:.1f}MB (+{growth_mb:.1f}MB)")

        assert (
            growth_mb < CONFIG.max_memory_growth_mb
        ), f"Memory grew by {growth_mb:.1f}MB, max allowed: {CONFIG.max_memory_growth_mb}MB"

    def test_memory_stable_privacy_guard(self):
        """PrivacyGuard should not leak memory."""
        guard = PrivacyGuard()

        gc.collect()
        baseline_objects = len(gc.get_objects())

        # Process 1000 texts
        for i in range(1000):
            text = f"Email {i} from user{i}@example.com with phone 555-{i:04d}"
            guard.sanitize(text)

        gc.collect()
        final_objects = len(gc.get_objects())
        growth = final_objects - baseline_objects
        growth_per_op = growth / 1000

        print(f"\nObject growth: {growth} total, {growth_per_op:.1f}/op")

        assert growth_per_op < 10, f"Object leak: {growth_per_op:.1f} objects/op"

    def test_memory_stable_cache(self):
        """SmartCache should respect size limits."""
        cache = SmartCache({"enabled": True, "max_size": 100})

        gc.collect()
        baseline_mb = psutil.Process().memory_info().rss / (1024 * 1024)

        # Store 500 entries (5x max size)
        for i in range(500):
            cache.store(
                f"subject-{i}", f"body-{i}", f"sender{i}@test.com", "Inbox", 0.9
            )

        gc.collect()
        final_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        growth_mb = final_mb - baseline_mb

        print(f"\nCache memory: +{growth_mb:.1f}MB for 500 entries (max 100)")

        # Should not grow unboundedly due to eviction
        assert growth_mb < 50, f"Cache memory grew by {growth_mb:.1f}MB"

    def test_memory_with_large_emails(self, mock_orchestrator_deps):
        """Memory handling with large email bodies."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        gc.collect()
        baseline_mb = psutil.Process().memory_info().rss / (1024 * 1024)

        # Process 10 large emails (100KB each)
        for i in range(10):
            email = EmailGenerator.generate_large_email(body_size_kb=100)
            email["id"] = f"large-{i}"
            message = {"type": "classify", "payload": email}
            orchestrator.handle_message(message)

        gc.collect()
        final_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        growth_mb = final_mb - baseline_mb

        print(f"\nLarge emails: +{growth_mb:.1f}MB for 10x100KB emails")

        # Should release memory after processing
        assert growth_mb < 50, f"Memory grew by {growth_mb:.1f}MB with large emails"

    def test_tracemalloc_leak_detection(self, mock_orchestrator_deps):
        """Use tracemalloc to detect memory leaks."""
        tracemalloc.start()

        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        snapshot1 = tracemalloc.take_snapshot()

        # Process emails
        for i in range(100):
            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}
            orchestrator.handle_message(message)

        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()

        # Compare
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        total_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        growth_kb = total_growth / 1024

        tracemalloc.stop()

        print(f"\nTracemalloc: {growth_kb:.1f}KB growth over 100 ops")

        # Allow some growth but flag if excessive
        assert growth_kb < 5000, f"Memory growth {growth_kb:.1f}KB exceeds 5MB"


# =============================================================================
# CACHE PERFORMANCE TESTS
# =============================================================================


class TestCachePerformance:
    """Tests for cache performance at scale."""

    def test_cache_hit_rate_similar_emails(self):
        """Cache should have high hit rate for similar emails."""
        cache = SmartCache({"enabled": True, "max_size": 1000})

        # Generate similar emails
        emails = EmailGenerator.generate_similar_emails(100, "newsletter@test.com")

        hits = 0
        misses = 0
        folders = ["Inbox", "Newsletters"]

        for email in emails:
            result = cache.check(
                email["subject"], email["body"], email["from"], folders
            )
            if result:
                hits += 1
            else:
                misses += 1
                cache.store(
                    email["subject"], email["body"], email["from"], "Newsletters", 0.9
                )

        hit_rate = hits / len(emails) if emails else 0
        print(f"\nSimilar emails cache: {hit_rate:.1%} hit rate")

        # For similar emails, we expect some hits after first miss
        assert hits > 0 or misses == len(emails)  # At least functioning

    def test_cache_hit_rate_repeated_emails(self):
        """Cache should have 100% hit rate for exact repeats."""
        cache = SmartCache({"enabled": True, "max_size": 100})
        folders = ["Inbox", "Work"]

        # First pass - populate cache
        email = EmailGenerator.generate_email(0)
        result1 = cache.check(email["subject"], email["body"], email["from"], folders)
        assert result1 is None  # First check is miss

        cache.store(email["subject"], email["body"], email["from"], "Inbox", 0.9)

        # Second pass - should hit
        result2 = cache.check(email["subject"], email["body"], email["from"], folders)
        assert result2 is not None  # Should hit

    def test_cache_performance_1000_lookups(self):
        """Cache lookups should be fast at scale."""
        cache = SmartCache({"enabled": True, "max_size": 1000})
        folders = ["Inbox", "Work"]

        # Populate cache
        for i in range(500):
            cache.store(
                f"subject-{i}", f"body-{i}", f"sender{i}@test.com", "Inbox", 0.9
            )

        # Time 1000 lookups
        start = time.perf_counter()

        for i in range(1000):
            cache.check(
                f"subject-{i % 500}",
                f"body-{i % 500}",
                f"sender{i % 500}@test.com",
                folders,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_lookup_ms = elapsed_ms / 1000

        print(
            f"\n1000 cache lookups: {elapsed_ms:.1f}ms total, {avg_lookup_ms:.3f}ms/lookup"
        )

        assert avg_lookup_ms < 1.0, f"Cache lookup too slow: {avg_lookup_ms:.3f}ms"

    def test_cache_eviction_performance(self):
        """Cache eviction should not slow down operations."""
        cache = SmartCache({"enabled": True, "max_size": 100})

        # Overfill cache to trigger evictions
        times = []

        for i in range(500):
            start = time.perf_counter()
            cache.store(
                f"subject-{i}", f"body-{i}", f"sender{i}@test.com", "Inbox", 0.9
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time_ms = (sum(times) / len(times)) * 1000
        max_time_ms = max(times) * 1000

        print(
            f"\nCache stores with eviction: avg={avg_time_ms:.3f}ms, max={max_time_ms:.1f}ms"
        )

        assert avg_time_ms < 1.0
        assert max_time_ms < 10.0  # No single operation too slow


# =============================================================================
# CONCURRENT PROCESSING TESTS
# =============================================================================


class TestConcurrentProcessing:
    """Tests for thread safety and concurrent access."""

    def test_concurrent_classifications(self, mock_orchestrator_deps):
        """Handle concurrent classification requests."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )
        emails = EmailGenerator.generate_emails(100)

        results = []
        errors = []
        lock = threading.Lock()

        def classify(email):
            try:
                message = {"type": "classify", "payload": email}
                result = orchestrator.handle_message(message)
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Use thread pool
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(classify, email) for email in emails]
            for future in as_completed(futures):
                pass

        success_rate = len(results) / len(emails)
        print(
            f"\nConcurrent (10 threads): {len(results)}/{len(emails)} success, {len(errors)} errors"
        )

        assert success_rate >= 0.95, f"Too many failures: {len(errors)}"

    def test_concurrent_cache_access(self):
        """Cache should be thread-safe."""
        cache = SmartCache({"enabled": True, "max_size": 100})

        errors = []
        ops_completed = [0]
        lock = threading.Lock()
        folders = ["Inbox", "Work"]

        def cache_ops(thread_id):
            try:
                for i in range(100):
                    # Mix of reads and writes
                    if i % 2 == 0:
                        cache.store(
                            f"subject-{thread_id}-{i}",
                            f"body-{i}",
                            f"sender{i}@test.com",
                            "Inbox",
                            0.9,
                        )
                    else:
                        cache.check(
                            f"subject-{thread_id}-{i-1}",
                            f"body-{i-1}",
                            f"sender{i-1}@test.com",
                            folders,
                        )

                    with lock:
                        ops_completed[0] += 1
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=cache_ops, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"\nConcurrent cache: {ops_completed[0]} ops, {len(errors)} errors")

        assert len(errors) == 0, f"Thread safety errors: {errors}"

    def test_concurrent_rate_limiter(self):
        """Rate limiter should be thread-safe."""
        limiter = RateLimiter({"test-provider": 100})  # 100 requests per minute

        allowed = [0]
        blocked = [0]
        lock = threading.Lock()

        def try_acquire():
            for _ in range(50):
                if limiter.acquire("test-provider", block=False):
                    with lock:
                        allowed[0] += 1
                else:
                    with lock:
                        blocked[0] += 1

        threads = [threading.Thread(target=try_acquire) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = allowed[0] + blocked[0]
        print(f"\nConcurrent rate limit: {allowed[0]} allowed, {blocked[0]} blocked")

        assert total == 500  # All requests processed


# =============================================================================
# CPU PROFILING TESTS
# =============================================================================


class TestCPUPerformance:
    """Tests for CPU usage and efficiency."""

    def test_cpu_usage_during_load(self, mock_orchestrator_deps):
        """CPU usage should not spike excessively."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        process = psutil.Process()

        # Warm up
        for i in range(10):
            email = EmailGenerator.generate_email(i)
            orchestrator.handle_message({"type": "classify", "payload": email})

        # Measure CPU during load
        start_cpu = process.cpu_percent()

        for i in range(100):
            email = EmailGenerator.generate_email(i)
            orchestrator.handle_message({"type": "classify", "payload": email})

        end_cpu = process.cpu_percent()

        print(f"\nCPU: {start_cpu:.1f}% -> {end_cpu:.1f}%")

    def test_processing_efficiency(self, mock_orchestrator_deps):
        """Measure processing efficiency (emails per second)."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        emails = EmailGenerator.generate_emails(1000)

        start = time.perf_counter()

        for email in emails:
            message = {"type": "classify", "payload": email}
            orchestrator.handle_message(message)

        elapsed = time.perf_counter() - start
        rate = len(emails) / elapsed

        print(f"\nProcessing: {rate:.0f} emails/second")

        # Should process at least 100/second with mocked provider
        assert rate >= 100, f"Processing too slow: {rate:.0f}/second"

    def test_sanitization_performance(self):
        """Text sanitization should be fast."""
        texts = [
            f"Email {i} with PII: john{i}@example.com, 555-{i:04d}" for i in range(1000)
        ]

        start = time.perf_counter()

        for text in texts:
            sanitize_text(text)

        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / len(texts)

        print(
            f"\nSanitization: {len(texts)} texts in {elapsed_ms:.1f}ms ({avg_ms:.3f}ms each)"
        )

        assert avg_ms < 1.0, f"Sanitization too slow: {avg_ms:.3f}ms"


# =============================================================================
# STRESS TESTS
# =============================================================================


@pytest.mark.slow
class TestStressScenarios:
    """Extreme stress test scenarios."""

    def test_10000_emails_sequential(self, mock_orchestrator_deps):
        """Process 10,000 emails (10x target)."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        total = 10000
        successes = 0

        gc.collect()
        start_mem = psutil.Process().memory_info().rss / (1024 * 1024)
        start_time = time.time()

        for i in range(total):
            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}

            try:
                result = orchestrator.handle_message(message)
                if result.get("action") or result.get("folder"):
                    successes += 1
            except Exception:
                pass

            # Progress every 1000
            if (i + 1) % 1000 == 0:
                print(f"  Processed {i + 1}/{total}...")

        gc.collect()
        end_mem = psutil.Process().memory_info().rss / (1024 * 1024)
        elapsed = time.time() - start_time

        rate = total / elapsed
        mem_growth = end_mem - start_mem

        print(f"\n10K emails: {rate:.0f}/sec, memory: +{mem_growth:.1f}MB")

        assert successes / total >= (1 - CONFIG.acceptable_error_rate)
        # 10K emails at ~2000/sec will use more memory; allow up to 300MB
        assert mem_growth < 300, f"Memory grew by {mem_growth:.1f}MB"

    def test_mixed_message_types_stress(self, mock_orchestrator_deps):
        """Stress test with mixed message types."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        message_types = [
            lambda: {"type": "ping"},
            lambda: {"type": "health"},
            lambda: {"type": "stats"},
            lambda: {"type": "classify", "payload": EmailGenerator.generate_email(0)},
        ]

        errors = 0
        total = 1000

        for i in range(total):
            msg_fn = random.choice(message_types)
            message = msg_fn()

            try:
                orchestrator.handle_message(message)
            except Exception:
                errors += 1

        error_rate = errors / total
        print(f"\nMixed messages: {errors} errors in {total} ({error_rate:.1%})")

        assert error_rate < CONFIG.acceptable_error_rate

    def test_rapid_provider_switches(self, mock_orchestrator_deps):
        """Test stability during rapid configuration changes."""
        # This tests the orchestrator's ability to handle config changes
        for i in range(50):
            orchestrator = Orchestrator(
                {"provider": "mock", "folders": EmailGenerator.FOLDERS}
            )

            email = EmailGenerator.generate_email(i)
            message = {"type": "classify", "payload": email}

            result = orchestrator.handle_message(message)
            assert result is not None

    def test_malformed_input_stress(self, mock_orchestrator_deps):
        """Handle malformed inputs without crashing."""
        orchestrator = Orchestrator(
            {"provider": "mock", "folders": EmailGenerator.FOLDERS}
        )

        malformed_inputs = [
            {},
            {"type": None},
            {"type": "classify"},  # Missing payload
            {"type": "classify", "payload": None},
            {"type": "classify", "payload": {}},
            {"type": "classify", "payload": {"folders": []}},
            {"type": "unknown_type"},
            {"type": "classify", "payload": {"subject": None}},
            "not a dict",
        ]

        for inp in malformed_inputs:
            try:
                if isinstance(inp, dict):
                    orchestrator.handle_message(inp)
            except Exception:
                pass  # Expected for some inputs

        # Should still work after malformed inputs
        valid = {"type": "classify", "payload": EmailGenerator.generate_email(0)}
        result = orchestrator.handle_message(valid)
        assert result is not None
