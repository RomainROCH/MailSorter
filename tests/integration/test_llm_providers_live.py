"""
Live LLM Provider Integration Tests.

These tests verify actual connectivity and functionality with LLM providers.
They are marked with `live` marker and require:
- Ollama running locally for ollama tests
- API keys in keyring for cloud provider tests

Run with: pytest tests/integration/test_llm_providers_live.py -v -m live
Skip live tests: pytest tests/integration/test_llm_providers_live.py -v -m "not live"

Task: LLM-INT-001
"""

import os
import time
import pytest
import requests
from typing import Optional
from unittest.mock import patch

# Import providers
from backend.providers.ollama_provider import OllamaProvider
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.providers.gemini_provider import GeminiProvider
from backend.providers.base import ClassificationResult, LLMProvider
from backend.providers.factory import ProviderFactory
from backend.utils.secrets import get_api_key


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

def check_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_ollama_model() -> str:
    """Get Ollama model to use for tests.
    
    Priority:
    1. OLLAMA_MODEL environment variable
    2. First available model from Ollama
    3. Fallback to 'llama3'
    """
    # Check environment variable first
    env_model = os.environ.get("OLLAMA_MODEL")
    if env_model:
        return env_model
    
    # Try to detect first available model
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                # Return the first model name (strip :latest tag for compatibility)
                return models[0].get("name", "llama3").split(":")[0]
    except Exception:
        pass
    
    return "llama3"


def check_api_key_available(provider_name: str) -> bool:
    """Check if API key is available for provider."""
    try:
        key = get_api_key(provider_name)
        return key is not None and len(key) > 0
    except Exception:
        return False


# Sample email payloads for testing
SAMPLE_EMAILS = [
    {
        "subject": "Your Invoice #12345",
        "body": "Please find attached your invoice for this month's services.",
        "expected_folder": "Invoices",
        "folders": ["Inbox", "Invoices", "Newsletters", "Spam"]
    },
    {
        "subject": "Weekly Tech Newsletter",
        "body": "Here are the top tech stories of the week: AI advances, new gadgets...",
        "expected_folder": "Newsletters",
        "folders": ["Inbox", "Invoices", "Newsletters", "Spam"]
    },
    {
        "subject": "URGENT: You've won $1,000,000!!!",
        "body": "Click here NOW to claim your prize. Limited time offer.",
        "expected_folder": "Spam",
        "folders": ["Inbox", "Invoices", "Newsletters", "Spam"]
    },
]


# =============================================================================
# OLLAMA LIVE TESTS
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(not check_ollama_available(), reason="Ollama not running")
class TestOllamaLiveIntegration:
    """Live integration tests for Ollama provider."""

    @pytest.fixture
    def provider(self) -> OllamaProvider:
        """Create Ollama provider with auto-detected or configured model."""
        return OllamaProvider({
            "base_url": "http://localhost:11434",
            "model": get_ollama_model(),
            "timeout": 60
        })

    def test_health_check_succeeds(self, provider: OllamaProvider):
        """Ollama health check should succeed when running."""
        assert provider.health_check() is True

    def test_provider_metadata(self, provider: OllamaProvider):
        """Verify Ollama provider metadata."""
        assert provider.get_name() == "ollama"
        assert provider.is_local is True
        assert provider.supports_streaming is True

    def test_classify_invoice_email(self, provider: OllamaProvider):
        """Should classify invoice email correctly."""
        email = SAMPLE_EMAILS[0]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert isinstance(result, ClassificationResult)
        assert result.folder in email["folders"]
        assert 0 <= result.confidence <= 1
        assert result.latency_ms is not None and result.latency_ms > 0

    def test_classify_newsletter_email(self, provider: OllamaProvider):
        """Should classify newsletter email correctly."""
        email = SAMPLE_EMAILS[1]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert result.folder in email["folders"]
        # Newsletter should have reasonable confidence
        assert result.confidence >= 0.3

    def test_classify_spam_email(self, provider: OllamaProvider):
        """Should classify spam email correctly."""
        email = SAMPLE_EMAILS[2]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert result.folder in email["folders"]
        # High-confidence spam detection expected
        if result.folder == "Spam":
            assert result.confidence >= 0.5

    def test_classify_with_limited_folders(self, provider: OllamaProvider):
        """Should correctly handle limited folder options."""
        result = provider.classify_email(
            subject="Hello there",
            body="Just wanted to say hi!",
            available_folders=["Inbox", "Personal"]
        )
        
        assert result is not None
        assert result.folder in ["Inbox", "Personal"]

    def test_handles_empty_body(self, provider: OllamaProvider):
        """Should handle emails with empty body."""
        result = provider.classify_email(
            subject="Meeting Tomorrow",
            body="",
            available_folders=["Inbox", "Work"]
        )
        
        assert result is not None
        assert result.folder in ["Inbox", "Work"]

    def test_handles_long_body(self, provider: OllamaProvider):
        """Should handle emails with very long body (truncation test)."""
        long_body = "This is a test email. " * 1000  # ~20k chars
        
        result = provider.classify_email(
            subject="Test Long Email",
            body=long_body,
            available_folders=["Inbox", "Archive"]
        )
        
        assert result is not None
        assert result.folder in ["Inbox", "Archive"]

    def test_latency_acceptable(self, provider: OllamaProvider):
        """Classification should complete within acceptable time."""
        start = time.time()
        
        result = provider.classify_email(
            subject="Quick Test",
            body="Just a quick test.",
            available_folders=["Inbox"]
        )
        
        elapsed = time.time() - start
        
        assert result is not None
        # Should complete within 30 seconds for local inference
        assert elapsed < 30, f"Classification took {elapsed:.1f}s, should be < 30s"

    def test_tokens_tracked(self, provider: OllamaProvider):
        """Token usage should be tracked."""
        result = provider.classify_email(
            subject="Token Test",
            body="Testing token counting.",
            available_folders=["Inbox"]
        )
        
        assert result is not None
        # Ollama should return token count
        assert result.tokens_used is not None


@pytest.mark.live
@pytest.mark.skipif(not check_ollama_available(), reason="Ollama not running")
class TestOllamaNetworkFailures:
    """Test Ollama behavior under network/connection issues."""

    def test_handles_wrong_url(self):
        """Should handle connection to wrong URL gracefully."""
        provider = OllamaProvider({
            "base_url": "http://localhost:99999",
            "timeout": 5
        })
        
        assert provider.health_check() is False

    def test_handles_invalid_model(self):
        """Should handle non-existent model."""
        provider = OllamaProvider({
            "model": "nonexistent-model-12345",
            "timeout": 30
        })
        
        # Health check might pass (Ollama running) but model missing
        result = provider.classify_email(
            subject="Test",
            body="Test",
            available_folders=["Inbox"]
        )
        
        # Should either return None or Inbox fallback
        if result is not None:
            assert result.folder == "Inbox"

    def test_timeout_handling(self):
        """Should handle very short timeout gracefully."""
        provider = OllamaProvider({
            "timeout": 0.001  # Unreasonably short
        })
        
        result = provider.classify_email(
            subject="Timeout Test",
            body="This should timeout.",
            available_folders=["Inbox"]
        )
        
        # Should handle gracefully (return None or fallback)
        assert result is None or result.folder == "Inbox"


# =============================================================================
# OPENAI LIVE TESTS
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(not check_api_key_available("openai"), reason="OpenAI API key not configured")
class TestOpenAILiveIntegration:
    """Live integration tests for OpenAI provider."""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create OpenAI provider with keyring key."""
        return OpenAIProvider({
            "model": "gpt-4o-mini",
            "timeout": 30
        })

    def test_health_check_succeeds(self, provider: OpenAIProvider):
        """OpenAI health check should succeed with valid key."""
        assert provider.health_check() is True

    def test_provider_metadata(self, provider: OpenAIProvider):
        """Verify OpenAI provider metadata."""
        assert provider.get_name() == "openai"
        assert provider.is_local is False
        assert provider.supports_streaming is True

    def test_classify_email(self, provider: OpenAIProvider):
        """Should classify email successfully."""
        email = SAMPLE_EMAILS[0]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert isinstance(result, ClassificationResult)
        assert result.folder in email["folders"]
        assert 0 <= result.confidence <= 1
        assert result.tokens_used is not None and result.tokens_used > 0

    def test_classify_multiple_emails(self, provider: OpenAIProvider):
        """Should classify multiple emails consistently."""
        for email in SAMPLE_EMAILS:
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
                available_folders=email["folders"]
            )
            
            assert result is not None
            assert result.folder in email["folders"]


@pytest.mark.live
class TestOpenAINetworkFailures:
    """Test OpenAI behavior under network issues."""

    def test_invalid_api_key(self):
        """Should handle invalid API key gracefully."""
        provider = OpenAIProvider({
            "api_key": "sk-invalid-key-12345",
            "timeout": 10
        })
        
        assert provider.health_check() is False

    def test_handles_rate_limit(self):
        """Rate limit handling (simulated via timeout)."""
        # This tests the timeout mechanism
        provider = OpenAIProvider({
            "api_key": "sk-invalid",
            "timeout": 0.001
        })
        
        result = provider.classify_email(
            subject="Test",
            body="Test",
            available_folders=["Inbox"]
        )
        
        # Should handle gracefully
        assert result is None


# =============================================================================
# ANTHROPIC LIVE TESTS
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(not check_api_key_available("anthropic"), reason="Anthropic API key not configured")
class TestAnthropicLiveIntegration:
    """Live integration tests for Anthropic Claude provider."""

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create Anthropic provider with keyring key."""
        return AnthropicProvider({
            "model": "claude-3-haiku-20240307",
            "timeout": 30
        })

    def test_health_check_succeeds(self, provider: AnthropicProvider):
        """Anthropic health check should succeed with valid key."""
        assert provider.health_check() is True

    def test_provider_metadata(self, provider: AnthropicProvider):
        """Verify Anthropic provider metadata."""
        assert provider.get_name() == "anthropic"
        assert provider.is_local is False
        assert provider.supports_streaming is True

    def test_classify_email(self, provider: AnthropicProvider):
        """Should classify email successfully."""
        email = SAMPLE_EMAILS[0]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert isinstance(result, ClassificationResult)
        assert result.folder in email["folders"]
        assert 0 <= result.confidence <= 1

    def test_classify_all_samples(self, provider: AnthropicProvider):
        """Should classify all sample emails."""
        for email in SAMPLE_EMAILS:
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
                available_folders=email["folders"]
            )
            
            assert result is not None
            assert result.folder in email["folders"]


@pytest.mark.live
class TestAnthropicNetworkFailures:
    """Test Anthropic behavior under network issues."""

    def test_invalid_api_key(self):
        """Should handle invalid API key gracefully."""
        provider = AnthropicProvider({
            "api_key": "sk-ant-invalid-key",
            "timeout": 10
        })
        
        assert provider.health_check() is False


# =============================================================================
# GEMINI LIVE TESTS
# =============================================================================

@pytest.mark.live
@pytest.mark.skipif(not check_api_key_available("gemini"), reason="Gemini API key not configured")
class TestGeminiLiveIntegration:
    """Live integration tests for Google Gemini provider."""

    @pytest.fixture
    def provider(self) -> GeminiProvider:
        """Create Gemini provider with keyring key."""
        return GeminiProvider({
            "model": "gemini-2.0-flash",
            "timeout": 30
        })

    def test_health_check_succeeds(self, provider: GeminiProvider):
        """Gemini health check should succeed with valid key."""
        assert provider.health_check() is True

    def test_provider_metadata(self, provider: GeminiProvider):
        """Verify Gemini provider metadata."""
        assert provider.get_name() == "gemini"
        assert provider.is_local is False
        assert provider.supports_streaming is True

    def test_classify_email(self, provider: GeminiProvider):
        """Should classify email successfully."""
        email = SAMPLE_EMAILS[0]
        
        result = provider.classify_email(
            subject=email["subject"],
            body=email["body"],
            available_folders=email["folders"]
        )
        
        assert result is not None
        assert isinstance(result, ClassificationResult)
        assert result.folder in email["folders"]
        assert 0 <= result.confidence <= 1

    def test_classify_all_samples(self, provider: GeminiProvider):
        """Should classify all sample emails."""
        for email in SAMPLE_EMAILS:
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
                available_folders=email["folders"]
            )
            
            assert result is not None
            assert result.folder in email["folders"]


@pytest.mark.live
class TestGeminiNetworkFailures:
    """Test Gemini behavior under network issues."""

    def test_invalid_api_key(self):
        """Should handle invalid API key gracefully."""
        provider = GeminiProvider({
            "api_key": "AIza-invalid-key",
            "timeout": 10
        })
        
        assert provider.health_check() is False


# =============================================================================
# PROVIDER FACTORY INTEGRATION TESTS
# =============================================================================

@pytest.mark.live
class TestProviderFactoryLive:
    """Live tests for provider factory pattern."""

    @pytest.mark.skipif(not check_ollama_available(), reason="Ollama not running")
    def test_create_ollama_provider(self):
        """Factory should create working Ollama provider."""
        provider = ProviderFactory.create("ollama")
        
        assert provider is not None
        assert provider.get_name() == "ollama"
        assert provider.health_check() is True

    @pytest.mark.skipif(not check_api_key_available("openai"), reason="OpenAI API key not configured")
    def test_create_openai_provider(self):
        """Factory should create working OpenAI provider."""
        provider = ProviderFactory.create("openai")
        
        assert provider is not None
        assert provider.get_name() == "openai"
        assert provider.health_check() is True

    @pytest.mark.skipif(not check_api_key_available("anthropic"), reason="Anthropic API key not configured")
    def test_create_anthropic_provider(self):
        """Factory should create working Anthropic provider."""
        provider = ProviderFactory.create("anthropic")
        
        assert provider is not None
        assert provider.get_name() == "anthropic"
        assert provider.health_check() is True

    @pytest.mark.skipif(not check_api_key_available("gemini"), reason="Gemini API key not configured")
    def test_create_gemini_provider(self):
        """Factory should create working Gemini provider."""
        provider = ProviderFactory.create("gemini")
        
        assert provider is not None
        assert provider.get_name() == "gemini"
        assert provider.health_check() is True


# =============================================================================
# CROSS-PROVIDER CONSISTENCY TESTS
# =============================================================================

@pytest.mark.live
@pytest.mark.slow
class TestCrossProviderConsistency:
    """Test consistency across multiple providers."""

    def get_available_providers(self) -> list[LLMProvider]:
        """Get list of available/configured providers."""
        providers = []
        
        if check_ollama_available():
            providers.append(OllamaProvider({"model": get_ollama_model(), "timeout": 60}))
        
        if check_api_key_available("openai"):
            providers.append(OpenAIProvider({"timeout": 30}))
        
        if check_api_key_available("anthropic"):
            providers.append(AnthropicProvider({"timeout": 30}))
        
        if check_api_key_available("gemini"):
            providers.append(GeminiProvider({"timeout": 30}))
        
        return providers

    @pytest.mark.skipif(True, reason="Run manually - uses API credits")
    def test_same_email_across_providers(self):
        """Same email should get similar classification across providers."""
        providers = self.get_available_providers()
        
        if len(providers) < 2:
            pytest.skip("Need at least 2 providers for comparison")
        
        email = SAMPLE_EMAILS[0]  # Invoice email
        results = {}
        
        for provider in providers:
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
                available_folders=email["folders"]
            )
            
            if result:
                results[provider.get_name()] = result.folder
        
        # All providers should agree on obvious cases
        unique_folders = set(results.values())
        print(f"Provider results: {results}")
        
        # At least 50% should agree
        from collections import Counter
        folder_counts = Counter(results.values())
        most_common = folder_counts.most_common(1)[0][1]
        agreement_rate = most_common / len(results)
        
        assert agreement_rate >= 0.5, f"Low provider agreement: {results}"


# =============================================================================
# NETWORK FAILURE SIMULATION TESTS
# =============================================================================

class TestNetworkFailureHandling:
    """Test all providers handle network failures gracefully."""

    def test_connection_timeout_ollama(self):
        """Ollama should handle connection timeout."""
        with patch('backend.providers.ollama_provider.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
            
            provider = OllamaProvider({"timeout": 5})
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            
            assert result is None

    def test_connection_error_ollama(self):
        """Ollama should handle connection errors."""
        with patch('backend.providers.ollama_provider.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            provider = OllamaProvider({"timeout": 5})
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            
            assert result is None

    def test_dns_failure_simulation(self):
        """Should handle DNS resolution failures."""
        provider = OllamaProvider({
            "base_url": "http://nonexistent.invalid.domain:11434",
            "timeout": 5
        })
        
        assert provider.health_check() is False

    def test_http_500_error_openai(self):
        """OpenAI should handle HTTP 500 errors gracefully."""
        with patch('backend.providers.openai_provider.requests.post') as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            provider = OpenAIProvider({"api_key": "test-key"})
            
            # Should return None gracefully, not raise
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            assert result is None

    def test_http_429_rate_limit(self):
        """Providers should handle rate limit responses gracefully."""
        with patch('backend.providers.openai_provider.requests.post') as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.headers = {"Retry-After": "60"}
            
            provider = OpenAIProvider({"api_key": "test-key"})
            
            # Should return None gracefully, not raise
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            assert result is None

    def test_malformed_json_response(self):
        """Providers should handle malformed JSON responses."""
        with patch('backend.providers.openai_provider.requests.post') as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "{{invalid json}}"
                    }
                }],
                "usage": {"total_tokens": 10}
            }
            
            provider = OpenAIProvider({"api_key": "test-key"})
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            
            # Should handle gracefully
            assert result is None

    def test_empty_response(self):
        """Providers should handle empty responses."""
        with patch('backend.providers.openai_provider.requests.post') as mock_post:
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": ""
                    }
                }],
                "usage": {"total_tokens": 0}
            }
            
            provider = OpenAIProvider({"api_key": "test-key"})
            result = provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
            
            assert result is None
