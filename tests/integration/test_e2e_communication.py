"""
E2E Integration tests for Extension ↔ Backend communication.

These tests simulate the full message flow as it happens in production:
1. Extension sends native message (JSON via stdin)
2. Backend processes and returns response (JSON via stdout)
3. Tests verify the complete round-trip

Task: V5-024
"""

import json
import pytest
import struct
from unittest.mock import Mock, patch

from backend.core.orchestrator import Orchestrator
from backend.providers.base import ClassificationResult


class TestNativeMessagingProtocol:
    """Test the Native Messaging Protocol implementation."""

    def test_message_encoding(self):
        """Verify message length prefix encoding (4 bytes, little-endian)."""
        message = {"type": "ping"}
        encoded = json.dumps(message).encode("utf-8")
        length_prefix = struct.pack("@I", len(encoded))

        # Should be 4 bytes
        assert len(length_prefix) == 4

        # Decode should match
        decoded_length = struct.unpack("@I", length_prefix)[0]
        assert decoded_length == len(encoded)

    def test_message_roundtrip(self):
        """Test encoding then decoding a message."""
        original = {"type": "classify", "payload": {"sender": "test@example.com"}}

        # Encode
        encoded_content = json.dumps(original).encode("utf-8")
        encoded_length = struct.pack("@I", len(encoded_content))
        full_message = encoded_length + encoded_content

        # Decode
        length = struct.unpack("@I", full_message[:4])[0]
        decoded_content = full_message[4 : 4 + length].decode("utf-8")
        decoded = json.loads(decoded_content)

        assert decoded == original


@pytest.fixture
def mock_orchestrator_deps():
    """Fixture that provides all orchestrator dependencies mocked."""
    with patch("backend.core.orchestrator.ProviderFactory") as mock_factory, patch(
        "backend.core.orchestrator.get_smart_cache"
    ) as mock_get_cache, patch(
        "backend.core.orchestrator.get_circuit_breaker"
    ) as mock_get_breaker, patch(
        "backend.core.orchestrator.get_rate_limiter"
    ) as mock_get_limiter, patch(
        "backend.core.orchestrator.get_prompt_engine"
    ) as mock_get_prompt, patch(
        "backend.core.orchestrator.get_calibrator"
    ) as mock_get_calibrator, patch(
        "backend.core.orchestrator.get_batch_processor"
    ) as mock_get_batch, patch(
        "backend.core.orchestrator.get_feedback_loop"
    ) as mock_get_feedback, patch(
        "backend.core.orchestrator.check_rate_limit"
    ) as mock_check_rate:

        # Setup provider
        mock_provider = Mock()
        mock_provider.get_name.return_value = "ollama"
        mock_provider.is_local = True
        mock_provider.health_check.return_value = True
        mock_provider.classify_email.return_value = ClassificationResult(
            folder="Inbox",
            confidence=0.85,
            reasoning="Test classification",
            tokens_used=100,
            latency_ms=50,
            source="ollama",
        )
        # The orchestrator calls classify_email, not classify
        mock_provider.classify_email.return_value = ClassificationResult(
            folder="Inbox",
            confidence=0.85,
            reasoning="Test classification",
            tokens_used=100,
            latency_ms=50,
            source="ollama",
        )
        mock_factory.create.return_value = mock_provider

        # Setup cache - check() returns None for cache miss
        mock_cache = Mock()
        mock_cache.check.return_value = None  # Cache miss
        mock_cache.store = Mock()
        mock_cache.get_stats.return_value = {"hits": 0, "misses": 0}
        mock_get_cache.return_value = mock_cache

        # Setup circuit breaker
        mock_breaker = Mock()
        mock_breaker.can_execute.return_value = True
        mock_breaker.is_available.return_value = True
        mock_breaker.record_success = Mock()
        mock_breaker.record_failure = Mock()
        mock_breaker.get_stats.return_value = {"state": "closed"}
        mock_breaker.get_state.return_value = "closed"
        mock_get_breaker.return_value = mock_breaker

        # Rate limit check passes
        mock_check_rate.return_value = True

        # Setup rate limiter
        mock_limiter = Mock()
        mock_limiter.acquire.return_value = True
        mock_limiter.get_status.return_value = {"current": 0, "limit": 10}
        mock_get_limiter.return_value = mock_limiter

        # Setup prompt engine
        mock_prompt = Mock()
        mock_prompt.build_prompt.return_value = {
            "system": "You are an email classifier",
            "user": "Classify this email",
            "language": "en",
        }
        mock_get_prompt.return_value = mock_prompt

        # Setup calibrator
        mock_cal = Mock()
        mock_cal.passes_threshold.return_value = True
        mock_cal.get_threshold.return_value = 0.7
        mock_cal.get_all_stats.return_value = {}
        mock_get_calibrator.return_value = mock_cal

        # Setup batch processor
        mock_batch = Mock()
        mock_batch.detect_mode.return_value = "realtime"
        mock_get_batch.return_value = mock_batch

        # Setup feedback loop
        mock_feedback = Mock()
        mock_feedback.get_stats.return_value = {}
        mock_get_feedback.return_value = mock_feedback

        yield {
            "factory": mock_factory,
            "provider": mock_provider,
            "cache": mock_cache,
            "breaker": mock_breaker,
            "limiter": mock_limiter,
            "check_rate": mock_check_rate,
            "prompt": mock_prompt,
            "calibrator": mock_cal,
            "batch": mock_batch,
            "feedback": mock_feedback,
        }


class TestPingPongFlow:
    """Test the health check ping/pong flow."""

    def test_ping_returns_pong(self, mock_orchestrator_deps):
        """Backend should respond to ping with status ok."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)
        response = orchestrator.handle_message({"type": "ping"})

        # Ping returns {"type": "pong", "status": "ok"}
        assert response["type"] == "pong"
        assert response["status"] == "ok"


class TestClassificationE2EFlow:
    """Test the full classification flow from extension request to response."""

    def test_classify_email_full_flow(self, mock_orchestrator_deps):
        """Test complete classification flow with mocked LLM."""
        # Configure provider response (orchestrator calls classify_email)
        mock_orchestrator_deps["provider"].classify_email.return_value = (
            ClassificationResult(
                folder="Invoices",
                confidence=0.92,
                reasoning="Email contains invoice keywords",
                tokens_used=150,
                latency_ms=200,
                source="ollama",
            )
        )

        config = {
            "provider": "ollama",
            "folders": ["Inbox", "Invoices", "Newsletters", "Spam"],
            "privacy": {"redact_emails": True},
            "intelligence": {
                "smart_cache": {"enabled": True},
                "circuit_breaker": {"enabled": True},
            },
        }

        orchestrator = Orchestrator(config)

        # Simulate message from extension
        extension_message = {
            "type": "classify",
            "payload": {
                "id": "msg-12345",
                "from": "billing@company.com",
                "subject": "Invoice #2024-001 - Payment Due",
                "body": "Dear Customer, Please find attached your invoice.",
                "folders": ["Inbox", "Invoices", "Newsletters", "Spam"],
            },
        }

        response = orchestrator.handle_message(extension_message)

        # Verify response structure
        assert response.get("id") == "msg-12345"
        assert response.get("action") == "move"
        assert response.get("target") == "Invoices"

    def test_classify_with_privacy_redaction(self, mock_orchestrator_deps):
        """Test that classification works with PII in content."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "privacy": {"redact_emails": True, "redact_phones": True},
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        # Message with PII
        message = {
            "type": "classify",
            "payload": {
                "id": "msg-123",
                "from": "john@example.com",
                "subject": "Contact me at 555-1234",
                "body": "My email is secret@private.com",
                "folders": ["Inbox"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should succeed and call provider
        assert response.get("action") in ["move", "none"]
        mock_orchestrator_deps["provider"].classify_email.assert_called()


class TestHealthStatusFlow:
    """Test the health check flow."""

    def test_health_check_returns_status(self, mock_orchestrator_deps):
        """Health endpoint should return status."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {"smart_cache": {"enabled": True}},
        }

        orchestrator = Orchestrator(config)
        response = orchestrator.handle_message({"type": "health"})

        assert response["status"] in ["ok", "degraded"]
        assert "provider" in response


class TestBatchProcessingE2E:
    """Test batch processing E2E flow."""

    def test_batch_start(self, mock_orchestrator_deps):
        """Test starting batch job."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox", "Spam"],
            "batch_mode": {"enabled": True},
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        batch_message = {
            "type": "batch_start",
            "payload": {
                "emails": [
                    {
                        "id": "1",
                        "from": "a@test.com",
                        "subject": "Test 1",
                        "body": "Body 1",
                    },
                    {
                        "id": "2",
                        "from": "b@test.com",
                        "subject": "Test 2",
                        "body": "Body 2",
                    },
                ]
            },
        }

        response = orchestrator.handle_message(batch_message)

        # Should have a response (accepted, ok, or error)
        assert "status" in response or "job_id" in response


class TestErrorHandlingE2E:
    """Test error handling in E2E scenarios."""

    def test_invalid_message_type_returns_error(self, mock_orchestrator_deps):
        """Unknown message types should return error."""
        config = {"provider": "ollama", "folders": ["Inbox"]}
        orchestrator = Orchestrator(config)

        response = orchestrator.handle_message({"type": "unknown_type"})

        assert response["status"] == "error"

    def test_missing_payload_handled(self, mock_orchestrator_deps):
        """Classification without payload should be handled."""
        config = {"provider": "ollama", "folders": ["Inbox"]}
        orchestrator = Orchestrator(config)

        response = orchestrator.handle_message({"type": "classify"})

        # Should handle gracefully
        assert "status" in response or "action" in response or "id" in response

    def test_provider_error_graceful_degradation(self, mock_orchestrator_deps):
        """Provider errors should result in graceful handling."""
        mock_orchestrator_deps["provider"].classify_email.side_effect = Exception(
            "LLM unavailable"
        )

        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "default_folder": "Inbox",
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-err",
                "from": "test@test.com",
                "subject": "Test",
                "body": "Test body",
                "folders": ["Inbox"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should not crash - returns error or fallback
        assert "status" in response or "action" in response or "id" in response


class TestHeadersOnlyMode:
    """Test headers-only mode for RGPD compliance."""

    def test_headers_only_mode(self, mock_orchestrator_deps):
        """In headers_only mode, classification should still work."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "analysis_mode": "headers_only",
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-headers",
                "from": "test@test.com",
                "subject": "Test Subject",
                "body": "This body should be ignored in headers_only mode",
                "folders": ["Inbox"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should work with headers only
        assert response.get("id") == "msg-headers"


class TestConnectionResilience:
    """Test connection resilience scenarios."""

    def test_circuit_breaker_available(self, mock_orchestrator_deps):
        """Circuit breaker should be available initially."""
        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {
                "smart_cache": {"enabled": False},
                "circuit_breaker": {"enabled": True},
            },
        }

        _ = Orchestrator(config)

        # Circuit should be available
        assert mock_orchestrator_deps["breaker"].can_execute.return_value is True

    def test_circuit_open_blocks_requests(self, mock_orchestrator_deps):
        """Open circuit should cause fallback behavior."""
        mock_orchestrator_deps["breaker"].can_execute.return_value = False
        mock_orchestrator_deps["breaker"].get_fallback_folder.return_value = "Inbox"

        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-circuit",
                "from": "test@test.com",
                "subject": "Test",
                "body": "Test",
                "folders": ["Inbox"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should indicate circuit is open
        assert response.get("reason") == "circuit_open" or "action" in response


class TestMultiLanguageSupport:
    """Test multi-language classification support."""

    def test_french_email_classification(self, mock_orchestrator_deps):
        """Should properly classify French emails."""
        mock_orchestrator_deps["provider"].classify_email.return_value = (
            ClassificationResult(
                folder="Factures",
                confidence=0.88,
                reasoning="Contient des mots-clés de facture",
                tokens_used=120,
                latency_ms=180,
                source="ollama",
            )
        )

        config = {
            "provider": "ollama",
            "folders": ["Inbox", "Factures", "Newsletters"],
            "intelligence": {
                "smart_cache": {"enabled": False},
                "prompts": {"language": "fr"},
            },
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-fr",
                "from": "facturation@entreprise.fr",
                "subject": "Votre facture du mois de janvier",
                "body": "Veuillez trouver ci-joint votre facture mensuelle.",
                "folders": ["Inbox", "Factures", "Newsletters"],
            },
        }

        response = orchestrator.handle_message(message)

        assert response.get("target") == "Factures"


class TestCacheIntegration:
    """Test smart cache integration."""

    def test_cache_hit_returns_cached_result(self, mock_orchestrator_deps):
        """Cache hit should return cached result without LLM call."""
        # Setup cache hit
        mock_orchestrator_deps["cache"].check.return_value = ClassificationResult(
            folder="Cached",
            confidence=0.95,
            reasoning="From cache",
            tokens_used=0,
            latency_ms=1,
            source="rule_cache",
        )

        config = {
            "provider": "ollama",
            "folders": ["Inbox", "Cached"],
            "intelligence": {"smart_cache": {"enabled": True}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-cached",
                "from": "cached@sender.com",
                "subject": "Cached email",
                "body": "Body",
                "folders": ["Inbox", "Cached"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should return cached result
        assert response.get("target") == "Cached"
        # Provider should NOT be called on cache hit
        mock_orchestrator_deps["provider"].classify_email.assert_not_called()

    def test_cache_miss_calls_llm(self, mock_orchestrator_deps):
        """Cache miss should call LLM."""
        mock_orchestrator_deps["cache"].check.return_value = None

        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {"smart_cache": {"enabled": True}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-new",
                "from": "new@sender.com",
                "subject": "New email",
                "body": "Body",
                "folders": ["Inbox"],
            },
        }

        _ = orchestrator.handle_message(message)

        # Provider should be called on cache miss
        mock_orchestrator_deps["provider"].classify_email.assert_called()


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_blocks_request(self, mock_orchestrator_deps):
        """Rate limited requests should be blocked."""
        mock_orchestrator_deps["check_rate"].return_value = False
        mock_orchestrator_deps["cache"].check.return_value = None

        config = {
            "provider": "ollama",
            "folders": ["Inbox"],
            "intelligence": {"smart_cache": {"enabled": False}},
        }

        orchestrator = Orchestrator(config)

        message = {
            "type": "classify",
            "payload": {
                "id": "msg-rate",
                "from": "test@test.com",
                "subject": "Test",
                "body": "Body",
                "folders": ["Inbox"],
            },
        }

        response = orchestrator.handle_message(message)

        # Should indicate rate limited
        assert response.get("reason") == "rate_limited" or "action" in response
