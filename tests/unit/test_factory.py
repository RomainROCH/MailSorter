"""
Unit tests for provider factory (INT-001).
"""

import pytest

from backend.providers.factory import ProviderFactory
from backend.providers.base import ClassificationResult
from backend.providers.ollama_provider import OllamaProvider


class TestProviderFactory:
    """Tests for ProviderFactory pattern."""

    def setup_method(self):
        """Reset factory state before each test."""
        ProviderFactory.clear_cache()

    def test_list_providers(self):
        """Should list all registered providers."""
        providers = ProviderFactory.list_providers()

        assert "ollama" in providers
        assert isinstance(providers, list)

    def test_create_ollama_provider(self):
        """Should create Ollama provider successfully."""
        provider = ProviderFactory.create(
            "ollama", {"base_url": "http://localhost:11434", "model": "llama3"}
        )

        assert provider is not None
        assert isinstance(provider, OllamaProvider)
        assert provider.get_name() == "ollama"
        assert provider.is_local is True

    def test_create_with_cache(self):
        """Should return cached instance for same name."""
        provider1 = ProviderFactory.create("ollama")
        provider2 = ProviderFactory.create("ollama")

        assert provider1 is provider2

    def test_create_without_cache(self):
        """Should create new instance when cache disabled."""
        provider1 = ProviderFactory.create("ollama", use_cache=False)
        provider2 = ProviderFactory.create("ollama", use_cache=False)

        assert provider1 is not provider2

    def test_unknown_provider_raises(self):
        """Should raise ValueError for unknown provider."""
        with pytest.raises(ValueError) as excinfo:
            ProviderFactory.create("unknown_provider")

        assert "Unknown provider" in str(excinfo.value)
        assert "unknown_provider" in str(excinfo.value)

    def test_is_registered(self):
        """Should check if provider is registered."""
        assert ProviderFactory.is_registered("ollama") is True
        assert ProviderFactory.is_registered("unknown") is False

    def test_get_local_providers(self):
        """Should return only local providers."""
        local = ProviderFactory.get_local_providers()

        assert "ollama" in local

    def test_clear_cache(self):
        """Should clear all cached instances."""
        provider1 = ProviderFactory.create("ollama")
        ProviderFactory.clear_cache()
        provider2 = ProviderFactory.create("ollama")

        assert provider1 is not provider2


class TestOllamaProvider:
    """Tests for Ollama provider implementation."""

    def test_initialization(self):
        """Should initialize with default config."""
        provider = OllamaProvider()

        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "llama3"
        assert provider.timeout == 30

    def test_initialization_with_config(self):
        """Should initialize with custom config."""
        provider = OllamaProvider(
            {"base_url": "http://custom:11434", "model": "mistral", "timeout": 60}
        )

        assert provider.base_url == "http://custom:11434"
        assert provider.model == "mistral"
        assert provider.timeout == 60

    def test_get_name(self):
        """Should return provider name."""
        provider = OllamaProvider()
        assert provider.get_name() == "ollama"

    def test_is_local(self):
        """Should indicate local provider."""
        provider = OllamaProvider()
        assert provider.is_local is True

    def test_supports_streaming(self):
        """Should support streaming."""
        provider = OllamaProvider()
        assert provider.supports_streaming is True


class TestClassificationResult:
    """Tests for ClassificationResult dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = ClassificationResult(folder="Inbox")

        assert result.folder == "Inbox"
        assert result.confidence == 0.5
        assert result.reasoning is None
        assert result.tokens_used == 0
        assert result.latency_ms == 0
        assert result.source == "llm"

    def test_custom_values(self):
        """Should accept custom values."""
        result = ClassificationResult(
            folder="Invoices",
            confidence=0.95,
            reasoning="Contains invoice keywords",
            tokens_used=50,
            latency_ms=150,
            source="cache",
        )

        assert result.folder == "Invoices"
        assert result.confidence == 0.95
        assert result.reasoning == "Contains invoice keywords"
        assert result.tokens_used == 50
        assert result.latency_ms == 150
        assert result.source == "cache"
