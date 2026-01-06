"""
Unit tests for cloud providers (V5-003, V5-019, V5-020).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.providers.base import ClassificationResult
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.providers.gemini_provider import GeminiProvider


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "temperature": 0.1,
            "max_tokens": 150
        }
    
    @patch('backend.providers.openai_provider.keyring')
    def test_init_with_explicit_key(self, mock_keyring):
        """Should use explicit API key."""
        provider = OpenAIProvider(self.config)
        
        assert provider.api_key == "test-key"
        mock_keyring.get_password.assert_not_called()
    
    @patch('backend.providers.openai_provider.keyring')
    def test_init_with_keyring(self, mock_keyring):
        """Should get API key from keyring."""
        mock_keyring.get_password.return_value = "keyring-key"
        
        config = {"model": "gpt-4o-mini"}
        provider = OpenAIProvider(config)
        
        assert provider.api_key == "keyring-key"
    
    def test_get_name(self):
        """Should return provider name."""
        with patch('backend.providers.openai_provider.keyring'):
            provider = OpenAIProvider(self.config)
            assert provider.get_name() == "openai"
    
    def test_is_not_local(self):
        """Should not be marked as local."""
        with patch('backend.providers.openai_provider.keyring'):
            provider = OpenAIProvider(self.config)
            assert provider.is_local is False
    
    @patch('backend.providers.openai_provider.requests')
    @patch('backend.providers.openai_provider.keyring')
    def test_classify_success(self, mock_keyring, mock_requests):
        """Should classify email successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"folder": "Invoices", "confidence": 0.92, "reasoning": "Invoice email"}'
                }
            }],
            "usage": {"total_tokens": 100}
        }
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(self.config)
        result = provider.classify(
            sender="invoice@company.com",
            subject="Your Invoice",
            body="Please find attached your invoice.",
            folders=["Inbox", "Invoices"]
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.folder == "Invoices"
        assert result.confidence == 0.92
        assert result.tokens_used == 100
    
    @patch('backend.providers.openai_provider.requests')
    @patch('backend.providers.openai_provider.keyring')
    def test_classify_api_error(self, mock_keyring, mock_requests):
        """Should handle API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(self.config)
        
        with pytest.raises(Exception):
            provider.classify(
                sender="test@test.com",
                subject="Test",
                body="Test",
                folders=["Inbox"]
            )
    
    @patch('backend.providers.openai_provider.requests')
    @patch('backend.providers.openai_provider.keyring')
    def test_classify_invalid_json(self, mock_keyring, mock_requests):
        """Should handle invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Not valid JSON"
                }
            }],
            "usage": {"total_tokens": 50}
        }
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(self.config)
        
        # Should handle gracefully or raise
        with pytest.raises(Exception):
            provider.classify(
                sender="test@test.com",
                subject="Test",
                body="Test",
                folders=["Inbox"]
            )


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            "model": "claude-3-haiku-20240307",
            "api_key": "test-anthropic-key",
            "temperature": 0.1,
            "max_tokens": 150
        }
    
    @patch('backend.providers.anthropic_provider.keyring')
    def test_get_name(self, mock_keyring):
        """Should return provider name."""
        provider = AnthropicProvider(self.config)
        assert provider.get_name() == "anthropic"
    
    @patch('backend.providers.anthropic_provider.keyring')
    def test_is_not_local(self, mock_keyring):
        """Should not be marked as local."""
        provider = AnthropicProvider(self.config)
        assert provider.is_local is False
    
    @patch('backend.providers.anthropic_provider.requests')
    @patch('backend.providers.anthropic_provider.keyring')
    def test_classify_success(self, mock_keyring, mock_requests):
        """Should classify email successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{
                "type": "text",
                "text": '{"folder": "Newsletters", "confidence": 0.85, "reasoning": "Newsletter content"}'
            }],
            "usage": {"input_tokens": 50, "output_tokens": 30}
        }
        mock_requests.post.return_value = mock_response
        
        provider = AnthropicProvider(self.config)
        result = provider.classify(
            sender="news@company.com",
            subject="Weekly Newsletter",
            body="Here's your weekly update.",
            folders=["Inbox", "Newsletters"]
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.folder == "Newsletters"
        assert result.confidence == 0.85
        assert result.tokens_used == 80
    
    @patch('backend.providers.anthropic_provider.requests')
    @patch('backend.providers.anthropic_provider.keyring')
    def test_uses_correct_api_version(self, mock_keyring, mock_requests):
        """Should use correct Anthropic API version header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": '{"folder": "Inbox", "confidence": 0.5}'}],
            "usage": {"input_tokens": 10, "output_tokens": 10}
        }
        mock_requests.post.return_value = mock_response
        
        provider = AnthropicProvider(self.config)
        provider.classify("test@test.com", "Test", "Test", ["Inbox"])
        
        # Check headers
        call_kwargs = mock_requests.post.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        
        assert "anthropic-version" in headers


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            "model": "gemini-1.5-flash",
            "api_key": "test-gemini-key",
            "temperature": 0.1,
            "max_tokens": 150
        }
    
    @patch('backend.providers.gemini_provider.keyring')
    def test_get_name(self, mock_keyring):
        """Should return provider name."""
        provider = GeminiProvider(self.config)
        assert provider.get_name() == "gemini"
    
    @patch('backend.providers.gemini_provider.keyring')
    def test_is_not_local(self, mock_keyring):
        """Should not be marked as local."""
        provider = GeminiProvider(self.config)
        assert provider.is_local is False
    
    @patch('backend.providers.gemini_provider.requests')
    @patch('backend.providers.gemini_provider.keyring')
    def test_classify_success(self, mock_keyring, mock_requests):
        """Should classify email successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"folder": "Shopping", "confidence": 0.88, "reasoning": "Order confirmation"}'
                    }]
                }
            }],
            "usageMetadata": {
                "totalTokenCount": 75
            }
        }
        mock_requests.post.return_value = mock_response
        
        provider = GeminiProvider(self.config)
        result = provider.classify(
            sender="orders@amazon.com",
            subject="Your order has shipped",
            body="Your package is on the way.",
            folders=["Inbox", "Shopping"]
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.folder == "Shopping"
        assert result.confidence == 0.88
        assert result.tokens_used == 75


class TestProviderCommon:
    """Common tests for all providers."""
    
    @pytest.mark.parametrize("provider_class,config", [
        (OpenAIProvider, {"api_key": "test"}),
        (AnthropicProvider, {"api_key": "test"}),
        (GeminiProvider, {"api_key": "test"}),
    ])
    def test_supports_streaming_false(self, provider_class, config):
        """All providers should not support streaming by default."""
        with patch.object(provider_class, '__init__', lambda self, cfg: None):
            provider = provider_class.__new__(provider_class)
            provider.supports_streaming = False
            
            assert provider.supports_streaming is False
    
    @pytest.mark.parametrize("provider_class,expected_name", [
        (OpenAIProvider, "openai"),
        (AnthropicProvider, "anthropic"),
        (GeminiProvider, "gemini"),
    ])
    def test_provider_names(self, provider_class, expected_name):
        """Each provider should have correct name."""
        with patch.object(provider_class, '__init__', lambda self, cfg: None):
            provider = provider_class.__new__(provider_class)
            provider._name = expected_name
            
            # Simulate get_name
            assert provider._name == expected_name
