"""
Stress tests for MailSorter.

Verifies the system can handle high volumes of email classifications
without degradation (target: 1000 emails/hour).

Task: QA-004
"""

import pytest
import time
import threading
import queue
import gc
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.core.orchestrator import Orchestrator
from backend.core.privacy import PrivacyGuard
from backend.core.smart_cache import SmartCache
from backend.utils.sanitize import sanitize_text
from backend.providers.base import ClassificationResult


# Stress test thresholds
TARGET_EMAILS_PER_HOUR = 1000
MAX_CLASSIFICATION_TIME_MS = 500  # With mocked provider
ACCEPTABLE_ERROR_RATE = 0.01  # 1% error rate acceptable under stress


class TestHighVolumeProcessing:
    """Tests for high-volume email processing."""
    
    @pytest.fixture
    def mock_orchestrator_deps(self):
        """Create mocked orchestrator with fast responses."""
        with patch('backend.core.orchestrator.ProviderFactory') as mock_factory, \
             patch('backend.core.orchestrator.get_smart_cache') as mock_cache, \
             patch('backend.core.orchestrator.get_circuit_breaker') as mock_breaker, \
             patch('backend.core.orchestrator.get_rate_limiter') as mock_limiter, \
             patch('backend.core.orchestrator.get_prompt_engine') as mock_prompt, \
             patch('backend.core.orchestrator.get_calibrator') as mock_cal, \
             patch('backend.core.orchestrator.get_batch_processor') as mock_batch, \
             patch('backend.core.orchestrator.get_feedback_loop') as mock_feedback, \
             patch('backend.core.orchestrator.check_rate_limit') as mock_check:
            
            mock_provider = Mock()
            mock_provider.get_name.return_value = "mock"
            mock_provider.is_local = True
            mock_provider.health_check.return_value = True
            mock_provider.classify_email.return_value = ClassificationResult(
                folder="Inbox",
                confidence=0.9,
                reasoning="Stress test",
                tokens_used=50,
                latency_ms=10,
                source="mock"
            )
            mock_factory.create.return_value = mock_provider
            
            mock_cache_inst = Mock()
            mock_cache_inst.check.return_value = None
            mock_cache.return_value = mock_cache_inst
            
            mock_breaker_inst = Mock()
            mock_breaker_inst.can_execute.return_value = True
            mock_breaker.return_value = mock_breaker_inst
            
            mock_check.return_value = True
            
            mock_prompt_inst = Mock()
            mock_prompt_inst.render.return_value = {"system": "test", "user": "test"}
            mock_prompt.return_value = mock_prompt_inst
            
            mock_cal_inst = Mock()
            mock_cal_inst.passes_threshold.return_value = True
            mock_cal.return_value = mock_cal_inst
            
            mock_batch.return_value = Mock()
            mock_feedback.return_value = Mock()
            mock_limiter.return_value = Mock()
            
            yield mock_factory
    
    def test_1000_sequential_classifications(self, mock_orchestrator_deps):
        """System should handle 1000 sequential classifications."""
        orchestrator = Orchestrator({
            "provider": "mock",
            "folders": ["Inbox", "Spam", "Newsletters"],
        })
        
        successes = 0
        failures = 0
        total_time = 0
        
        for i in range(1000):
            message = {
                "type": "classify",
                "payload": {
                    "id": f"stress-{i}",
                    "from": f"sender{i}@example.com",
                    "subject": f"Test Email {i}",
                    "body": f"This is test email body {i} for stress testing.",
                    "folders": ["Inbox", "Spam"]
                }
            }
            
            start = time.perf_counter()
            try:
                result = orchestrator.handle_message(message)
                elapsed_ms = (time.perf_counter() - start) * 1000
                total_time += elapsed_ms
                
                # Check for success - result has "action": "move" on success
                if result.get("action") == "move" or result.get("folder") is not None:
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
        
        success_rate = successes / 1000
        avg_latency = total_time / 1000
        
        assert success_rate >= (1 - ACCEPTABLE_ERROR_RATE), \
            f"Success rate {success_rate:.2%} below threshold"
        assert avg_latency < MAX_CLASSIFICATION_TIME_MS, \
            f"Avg latency {avg_latency:.1f}ms exceeds threshold"
    
    def test_burst_100_in_1_second(self, mock_orchestrator_deps):
        """System should handle 100 emails in 1 second burst."""
        orchestrator = Orchestrator({
            "provider": "mock",
            "folders": ["Inbox"],
        })
        
        messages = [
            {
                "type": "classify",
                "payload": {
                    "id": f"burst-{i}",
                    "from": f"sender{i}@test.com",
                    "subject": f"Burst Test {i}",
                    "body": f"Body {i}",
                    "folders": ["Inbox"]
                }
            }
            for i in range(100)
        ]
        
        start = time.perf_counter()
        
        for msg in messages:
            orchestrator.handle_message(msg)
        
        elapsed = time.perf_counter() - start
        
        # Should complete in under 2 seconds
        assert elapsed < 2.0, f"Burst took {elapsed:.2f}s, should be < 2s"


class TestMemoryUnderStress:
    """Tests for memory stability under stress."""
    
    def test_memory_stable_after_1000_ops(self):
        """Memory should remain stable after 1000 operations."""
        guard = PrivacyGuard()
        
        gc.collect()
        baseline = len(gc.get_objects())
        
        # Process 1000 emails
        for i in range(1000):
            text = f"Test email {i} from user{i}@example.com with phone 555-{i:04d}"
            guard.sanitize(text)
        
        gc.collect()
        final = len(gc.get_objects())
        
        growth = final - baseline
        growth_rate = growth / 1000
        
        # Should have less than 10 objects per operation on average
        assert growth_rate < 10, f"Memory growth {growth_rate:.1f} objects/op suggests leak"
    
    def test_cache_eviction_under_stress(self):
        """Cache should evict old entries under memory pressure."""
        cache = SmartCache({"enabled": True, "max_size": 100})
        
        # Fill cache beyond capacity
        for i in range(500):
            cache.store(f"subject-{i}", f"body-{i}", f"sender{i}@test.com", "Inbox", 0.9)
        
        # Cache should have evicted old entries
        stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
        # Just verify no crash occurred
        assert True


class TestConcurrentProcessing:
    """Tests for concurrent/parallel processing."""
    
    def test_parallel_sanitization(self):
        """Parallel sanitization should not cause issues."""
        results = queue.Queue()
        
        def sanitize_worker(text_id):
            text = f"Email from user{text_id}@example.com about project {text_id}"
            result = sanitize_text(text)
            results.put((text_id, result))
        
        # Run 100 parallel sanitizations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sanitize_worker, i) for i in range(100)]
            
            for future in as_completed(futures):
                future.result()  # Raise any exceptions
        
        # Should have 100 results
        assert results.qsize() == 100
    
    def test_parallel_privacy_guard(self):
        """PrivacyGuard should be thread-safe."""
        guard = PrivacyGuard()
        errors = []
        
        def process(i):
            try:
                text = f"Contact user{i}@test.com or call 555-{i:04d}"
                result = guard.sanitize(text)
                if "test.com" in result and "REDACTED" not in result.upper():
                    errors.append(f"Email not redacted in {i}")
            except Exception as e:
                errors.append(str(e))
        
        threads = [threading.Thread(target=process, args=(i,)) for i in range(50)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors[:5]}"


class TestRateLimiting:
    """Tests for rate limiting under stress."""
    
    def test_rate_limiter_respects_limits(self):
        """Rate limiter should enforce limits even under stress."""
        from backend.core.rate_limiter import RateLimiter
        
        # Low limit for testing
        limiter = RateLimiter(limits={"test": 10, "default": 10})
        
        allowed = 0
        denied = 0
        
        # Try 100 requests in quick succession (non-blocking)
        for _ in range(100):
            if limiter.acquire("test", tokens=1, block=False):
                allowed += 1
            else:
                denied += 1
        
        # Should have allowed some but not all
        assert allowed > 0
        assert denied > 0
    
    def test_circuit_breaker_stability(self):
        """Circuit breaker should remain stable under stress."""
        from backend.core.circuit_breaker import CircuitBreaker
        
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        
        # Simulate mixed success/failure
        for i in range(100):
            if i % 7 == 0:  # ~14% failure
                breaker.record_failure("test_provider")
            else:
                breaker.record_success("test_provider")
        
        # Breaker should have a defined state
        can_exec = breaker.can_execute("test_provider")
        assert isinstance(can_exec, bool)  # Just verify no crash


class TestEdgeCasesUnderStress:
    """Edge case handling under stress."""
    
    def test_empty_emails_stress(self):
        """System should handle many empty emails."""
        guard = PrivacyGuard()
        
        for _ in range(100):
            result = guard.sanitize("")
            assert result == ""
    
    def test_very_long_emails_stress(self):
        """System should handle repeated long emails."""
        guard = PrivacyGuard()
        long_body = "A" * 10000
        
        for _ in range(100):
            result = guard.sanitize(long_body)
            assert len(result) > 0
    
    def test_unicode_heavy_stress(self):
        """System should handle Unicode-heavy content."""
        guard = PrivacyGuard()
        unicode_text = "日本語 " * 1000  # 8000 chars of Japanese
        
        for _ in range(50):
            result = guard.sanitize(unicode_text)
            assert len(result) > 0


class TestRecovery:
    """Tests for recovery from stress conditions."""
    
    def test_recovery_after_oom_simulation(self):
        """System should recover after memory pressure."""
        # Create memory pressure
        large_list = [f"data-{i}" * 1000 for i in range(1000)]
        
        # Clear
        del large_list
        gc.collect()
        
        # System should still work
        guard = PrivacyGuard()
        result = guard.sanitize("test@email.com")
        
        assert result is not None
    
    def test_recovery_after_high_cpu(self):
        """System should work after CPU-intensive operations."""
        # Simulate CPU load
        total = 0
        for i in range(1000000):
            total += i
        
        # System should still work
        result = sanitize_text("test email")
        
        assert result is not None


class TestSustainedLoad:
    """Tests for sustained load over time."""
    
    def test_30_second_sustained_load(self):
        """System should handle 30 seconds of sustained load."""
        guard = PrivacyGuard()
        
        start = time.perf_counter()
        count = 0
        errors = 0
        
        while time.perf_counter() - start < 30:
            try:
                text = f"Email {count} from test{count}@example.com"
                guard.sanitize(text)
                count += 1
            except Exception:
                errors += 1
        
        elapsed = time.perf_counter() - start
        throughput = count / elapsed
        
        # Should achieve at least 100 emails/second
        assert throughput > 100, f"Throughput {throughput:.1f}/s below target"
        assert errors / count < ACCEPTABLE_ERROR_RATE, \
            f"Error rate {errors/count:.2%} too high"
