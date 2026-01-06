"""
Unit tests for cloud providers (V5-003, V5-019, V5-020).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.providers.base import ClassificationResult
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.providers.gemini_provider import GeminiProvider


# Keyring is imported in backend.utils.secrets, not in provider modules
KEYRING_PATCH = 'backend.utils.secrets.keyring'


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
    
    @patch(KEYRING_PATCH)
    def test_init_with_explicit_key(self, mock_keyring):
        """Should use explicit API key."""
        provider = OpenAIProvider(self.config)
        
        assert provider.api_key == "test-key"
        mock_keyring.get_password.assert_not_called()
    
    @patch(KEYRING_PATCH)
    def test_init_with_keyring(self, mock_keyring):
        """Should get API key from keyring."""
        mock_keyring.get_password.return_value = "keyring-key"
        
        config = {"model": "gpt-4o-mini"}
        provider = OpenAIProvider(config)
        
        assert provider.api_key == "keyring-key"
    
    def test_get_name(self):
        """Should return provider name."""
        with patch(KEYRING_PATCH):
            provider = OpenAIProvider(self.config)
            assert provider.get_name() == "openai"
    
    def test_is_not_local(self):
        """Should not be marked as local."""
        with patch(KEYRING_PATCH):
            provider = OpenAIProvider(self.config)
            assert provider.is_local is False
    
    @patch('backend.providers.openai_provider.requests')
    @patch(KEYRING_PATCH)
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
        result = provider.classify_email(
            subject="Your Invoice",
            body="Please find attached your invoice.",
            available_folders=["Inbox", "Invoices"]
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.folder == "Invoices"
        assert result.confidence == 0.92
        assert result.tokens_used == 100
    
    @patch('backend.providers.openai_provider.requests')
    @patch(KEYRING_PATCH)
    def test_classify_api_error(self, mock_keyring, mock_requests):
        """Should handle API errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.post.return_value = mock_response
        
        provider = OpenAIProvider(self.config)
        
        with pytest.raises(Exception):
            provider.classify_email(
                subject="Test",
                body="Test",
                available_folders=["Inbox"]
            )
    
    @patch('backend.providers.openai_provider.requests')
    @patch(KEYRING_PATCH)
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
        
        # Should handle gracefully and return None when JSON is invalid
        result = provider.classify_email(
            subject="Test",
            body="Test",
            available_folders=["Inbox"]
        )
        assert result is None


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
    
    @patch(KEYRING_PATCH)
    def test_get_name(self, mock_keyring):
        """Should return provider name."""
        provider = AnthropicProvider(self.config)
        assert provider.get_name() == "anthropic"
    
    @patch(KEYRING_PATCH)
    def test_is_not_local(self, mock_keyring):
        """Should not be marked as local."""
        provider = AnthropicProvider(self.config)
        assert provider.is_local is False
    
    @patch('backend.providers.anthropic_provider.requests')
    @patch(KEYRING_PATCH)
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
        result = provider.classify_email(
            subject="Weekly Newsletter",
            body="Here's your weekly update.",
            available_folders=["Inbox", "Newsletters"]
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.folder == "Newsletters"
        assert result.confidence == 0.85
        assert result.tokens_used == 80
    
    @patch('backend.providers.anthropic_provider.requests')
    @patch(KEYRING_PATCH)
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
        provider.classify_email("Test", "Test", ["Inbox"])
        
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
    
    @patch(KEYRING_PATCH)
    def test_get_name(self, mock_keyring):
        """Should return provider name."""
        provider = GeminiProvider(self.config)
        assert provider.get_name() == "gemini"
    
    @patch(KEYRING_PATCH)
    def test_is_not_local(self, mock_keyring):
        """Should not be marked as local."""
        provider = GeminiProvider(self.config)
        assert provider.is_local is False
    
    @patch('backend.providers.gemini_provider.requests')
    @patch(KEYRING_PATCH)
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
                "promptTokenCount": 50,
                "candidatesTokenCount": 25
            }
        }
        mock_requests.post.return_value = mock_response
        
        provider = GeminiProvider(self.config)
        result = provider.classify_email(
            subject="Your order has shipped",
            body="Your package is on the way.",
            available_folders=["Inbox", "Shopping"]
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
    @patch(KEYRING_PATCH)
    def test_supports_streaming(self, mock_keyring, provider_class, config):
        """All providers should support streaming."""
        provider = provider_class(config)
        # Cloud providers support streaming
        assert provider.supports_streaming is True
    
    @pytest.mark.parametrize("provider_class,config,expected_name", [
        (OpenAIProvider, {"api_key": "test"}, "openai"),
        (AnthropicProvider, {"api_key": "test"}, "anthropic"),
        (GeminiProvider, {"api_key": "test"}, "gemini"),
    ])
    @patch(KEYRING_PATCH)
    def test_provider_names(self, mock_keyring, provider_class, config, expected_name):
        """Each provider should have correct name."""
        provider = provider_class(config)
        assert provider.get_name() == expected_name
