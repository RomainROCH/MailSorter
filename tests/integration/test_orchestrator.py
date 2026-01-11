"""
Integration tests for the orchestrator with Phase 4 components.
"""

import pytest
from unittest.mock import Mock, patch

from backend.core.orchestrator import Orchestrator
from backend.providers.base import ClassificationResult


class TestOrchestratorIntegration:
    """Integration tests for Orchestrator."""

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    def setup_method(self, method, mock_rate_limiter, mock_circuit, mock_factory):
        """Setup orchestrator with mocked dependencies."""
        # Mock provider
        self.mock_provider = Mock()
        self.mock_provider.get_name.return_value = "ollama"
        self.mock_provider.is_local = True
        self.mock_provider.classify.return_value = ClassificationResult(
            folder="Inbox",
            confidence=0.85,
            reasoning="Test classification",
            tokens_used=100,
            latency_ms=50,
            source="ollama",
        )

        mock_factory.create.return_value = self.mock_provider

        # Mock circuit breaker
        self.mock_breaker = Mock()
        self.mock_breaker.is_available.return_value = True
        mock_circuit.return_value = self.mock_breaker

        # Mock rate limiter
        self.mock_limiter = Mock()
        self.mock_limiter.acquire.return_value = True
        mock_rate_limiter.return_value = self.mock_limiter

        self.config = {
            "provider": "ollama",
            "folders": ["Inbox", "Invoices", "Newsletters", "Spam"],
            "privacy": {"redact_emails": True},
            "intelligence": {
                "smart_cache": {"enabled": False},
                "circuit_breaker": {"enabled": True},
            },
        }

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    @patch("backend.core.orchestrator.PromptEngine")
    @patch("backend.core.orchestrator.get_calibrator")
    def test_classify_basic_flow(
        self,
        mock_calibrator,
        mock_prompt,
        mock_limiter,
        mock_breaker_fn,
        mock_cache,
        mock_factory,
    ):
        """Should classify email through full pipeline."""
        # Setup mocks
        mock_provider = Mock()
        mock_provider.get_name.return_value = "ollama"
        mock_provider.is_local = True
        mock_provider.classify.return_value = ClassificationResult(
            folder="Invoices",
            confidence=0.92,
            reasoning="Contains invoice",
            tokens_used=80,
            latency_ms=100,
            source="ollama",
        )
        mock_factory.create.return_value = mock_provider

        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = True
        mock_breaker_fn.return_value = mock_breaker

        mock_limiter_instance = Mock()
        mock_limiter_instance.acquire.return_value = True
        mock_limiter.return_value = mock_limiter_instance

        mock_prompt_instance = Mock()
        mock_prompt_instance.build_prompt.return_value = {
            "system": "System prompt",
            "user": "User prompt",
            "language": "en",
        }
        mock_prompt.return_value = mock_prompt_instance

        mock_cal = Mock()
        mock_cal.passes_threshold.return_value = True
        mock_calibrator.return_value = mock_cal

        # Create orchestrator
        orchestrator = Orchestrator(self.config)

        # Classify
        result = orchestrator.classify(
            sender="invoice@company.com",
            subject="Your Invoice #12345",
            body="Please find attached your monthly invoice.",
        )

        # Verify
        assert result["folder"] == "Invoices"
        assert result["confidence"] == 0.92
        assert "signature" in result

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    def test_cache_hit_skips_llm(
        self, mock_limiter, mock_breaker_fn, mock_cache, mock_factory
    ):
        """Should skip LLM call on cache hit."""
        # Setup cache hit
        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = {
            "folder": "Cached",
            "confidence": 0.95,
            "source": "sender_cache",
        }
        mock_cache.return_value = mock_cache_instance

        mock_provider = Mock()
        mock_factory.create.return_value = mock_provider

        # Create orchestrator
        orchestrator = Orchestrator(self.config)

        # Classify
        result = orchestrator.classify(
            sender="known@sender.com", subject="Test", body="Test body"
        )

        # Provider should NOT be called
        mock_provider.classify.assert_not_called()

        # Should return cached result
        assert result["folder"] == "Cached"
        assert result["source"] == "sender_cache"

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    def test_circuit_breaker_blocks(
        self, mock_limiter, mock_breaker_fn, mock_cache, mock_factory
    ):
        """Should block when circuit is open."""
        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = False  # Circuit OPEN
        mock_breaker_fn.return_value = mock_breaker

        mock_factory.create.return_value = Mock()

        orchestrator = Orchestrator(self.config)

        # Should raise or return error
        with pytest.raises(Exception) as exc_info:
            orchestrator.classify(sender="test@test.com", subject="Test", body="Test")

        assert (
            "circuit" in str(exc_info.value).lower()
            or "unavailable" in str(exc_info.value).lower()
        )

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    def test_rate_limit_blocks(
        self, mock_limiter, mock_breaker_fn, mock_cache, mock_factory
    ):
        """Should block when rate limited."""
        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = True
        mock_breaker_fn.return_value = mock_breaker

        mock_limiter_instance = Mock()
        mock_limiter_instance.acquire.return_value = False  # Rate limited
        mock_limiter.return_value = mock_limiter_instance

        mock_factory.create.return_value = Mock()

        orchestrator = Orchestrator(self.config)

        # Should raise or return error
        with pytest.raises(Exception) as exc_info:
            orchestrator.classify(sender="test@test.com", subject="Test", body="Test")

        assert "rate" in str(exc_info.value).lower()

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    @patch("backend.core.orchestrator.PromptEngine")
    @patch("backend.core.orchestrator.get_calibrator")
    def test_low_confidence_returns_inbox(
        self,
        mock_calibrator,
        mock_prompt,
        mock_limiter,
        mock_breaker_fn,
        mock_cache,
        mock_factory,
    ):
        """Should return Inbox when confidence below threshold."""
        mock_provider = Mock()
        mock_provider.get_name.return_value = "ollama"
        mock_provider.is_local = True
        mock_provider.classify.return_value = ClassificationResult(
            folder="Invoices",
            confidence=0.3,  # Low confidence
            reasoning="Uncertain",
            tokens_used=50,
            latency_ms=100,
            source="ollama",
        )
        mock_factory.create.return_value = mock_provider

        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = True
        mock_breaker_fn.return_value = mock_breaker

        mock_limiter_instance = Mock()
        mock_limiter_instance.acquire.return_value = True
        mock_limiter.return_value = mock_limiter_instance

        mock_prompt_instance = Mock()
        mock_prompt_instance.build_prompt.return_value = {
            "system": "System",
            "user": "User",
            "language": "en",
        }
        mock_prompt.return_value = mock_prompt_instance

        mock_cal = Mock()
        mock_cal.passes_threshold.return_value = False  # Below threshold
        mock_calibrator.return_value = mock_cal

        config = dict(self.config)
        config["default_folder"] = "Inbox"

        orchestrator = Orchestrator(config)
        result = orchestrator.classify(
            sender="test@test.com", subject="Test", body="Test"
        )

        # Should fallback to default
        assert result["folder"] == "Inbox"
        assert result["confidence_passed"] is False


class TestOrchestratorProviderFallback:
    """Tests for provider fallback behavior."""

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    @patch("backend.core.orchestrator.PromptEngine")
    @patch("backend.core.orchestrator.get_calibrator")
    def test_fallback_on_primary_failure(
        self,
        mock_calibrator,
        mock_prompt,
        mock_limiter,
        mock_breaker_fn,
        mock_cache,
        mock_factory,
    ):
        """Should fallback to secondary provider on failure."""
        # Primary fails, secondary succeeds
        mock_primary = Mock()
        mock_primary.get_name.return_value = "openai"
        mock_primary.is_local = False
        mock_primary.classify.side_effect = Exception("API Error")

        mock_secondary = Mock()
        mock_secondary.get_name.return_value = "ollama"
        mock_secondary.is_local = True
        mock_secondary.classify.return_value = ClassificationResult(
            folder="Inbox",
            confidence=0.8,
            reasoning="Fallback",
            tokens_used=50,
            latency_ms=100,
            source="ollama",
        )

        # Factory returns different providers
        call_count = [0]

        def create_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_primary
            return mock_secondary

        mock_factory.create.side_effect = create_side_effect
        mock_factory.get_local_providers.return_value = ["ollama"]

        # Setup other mocks
        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = True
        mock_breaker.record_failure = Mock()
        mock_breaker_fn.return_value = mock_breaker

        mock_limiter_instance = Mock()
        mock_limiter_instance.acquire.return_value = True
        mock_limiter.return_value = mock_limiter_instance

        mock_prompt_instance = Mock()
        mock_prompt_instance.build_prompt.return_value = {
            "system": "System",
            "user": "User",
            "language": "en",
        }
        mock_prompt.return_value = mock_prompt_instance

        mock_cal = Mock()
        mock_cal.passes_threshold.return_value = True
        mock_calibrator.return_value = mock_cal

        config = {
            "provider": "openai",
            "fallback_provider": "ollama",
            "folders": ["Inbox", "Spam"],
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        # Should succeed via fallback
        result = orchestrator.classify(
            sender="test@test.com", subject="Test", body="Test"
        )

        assert result["folder"] == "Inbox"
        assert result["source"] == "ollama"


class TestOrchestratorBatchMode:
    """Tests for batch processing mode."""

    @patch("backend.core.orchestrator.ProviderFactory")
    @patch("backend.core.orchestrator.SmartCache")
    @patch("backend.core.orchestrator.get_circuit_breaker")
    @patch("backend.core.orchestrator.RateLimiter")
    @patch("backend.core.orchestrator.PromptEngine")
    @patch("backend.core.orchestrator.get_calibrator")
    @patch("backend.core.orchestrator.get_processor")
    def test_batch_classify(
        self,
        mock_processor_fn,
        mock_calibrator,
        mock_prompt,
        mock_limiter,
        mock_breaker_fn,
        mock_cache,
        mock_factory,
    ):
        """Should process emails in batch."""
        # Setup mocks
        mock_provider = Mock()
        mock_provider.get_name.return_value = "ollama"
        mock_provider.is_local = True
        mock_provider.classify.return_value = ClassificationResult(
            folder="Inbox",
            confidence=0.9,
            reasoning="Batch",
            tokens_used=50,
            latency_ms=50,
            source="ollama",
        )
        mock_factory.create.return_value = mock_provider

        mock_cache_instance = Mock()
        mock_cache_instance.lookup.return_value = None
        mock_cache.return_value = mock_cache_instance

        mock_breaker = Mock()
        mock_breaker.is_available.return_value = True
        mock_breaker_fn.return_value = mock_breaker

        mock_limiter_instance = Mock()
        mock_limiter_instance.acquire.return_value = True
        mock_limiter.return_value = mock_limiter_instance

        mock_prompt_instance = Mock()
        mock_prompt_instance.build_prompt.return_value = {
            "system": "System",
            "user": "User",
            "language": "en",
        }
        mock_prompt.return_value = mock_prompt_instance

        mock_cal = Mock()
        mock_cal.passes_threshold.return_value = True
        mock_calibrator.return_value = mock_cal

        # Setup batch processor mock
        mock_processor = Mock()
        mock_processor.detect_mode.return_value = "batch"
        mock_processor_fn.return_value = mock_processor

        config = {
            "provider": "ollama",
            "folders": ["Inbox", "Spam"],
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        emails = [
            {"sender": f"test{i}@test.com", "subject": f"Test {i}", "body": "Body"}
            for i in range(5)
        ]

        results = orchestrator.classify_batch(emails)

        assert len(results) == 5
        for result in results:
            assert "folder" in result
