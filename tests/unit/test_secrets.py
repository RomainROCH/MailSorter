"""
Unit tests for Secrets Manager module.

Tests secure storage of API keys using system keyring.
All tests mock the keyring to avoid system dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestKeyringAvailability:
    """Tests for keyring availability detection."""
    
    def test_is_keyring_available_when_imported(self):
        """is_keyring_available returns True when keyring is available."""
        with patch.dict('sys.modules', {'keyring': MagicMock()}):
            # Force re-import to pick up mocked keyring
            import importlib
            import backend.utils.secrets as secrets_module
            
            # Mock the KEYRING_AVAILABLE flag
            with patch.object(secrets_module, 'KEYRING_AVAILABLE', True):
                assert secrets_module.is_keyring_available() is True
    
    def test_is_keyring_available_when_not_imported(self):
        """is_keyring_available returns False when keyring unavailable."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            assert secrets_module.is_keyring_available() is False


class TestGetApiKey:
    """Tests for API key retrieval."""
    
    def test_get_api_key_success(self):
        """Successfully retrieves API key from keyring."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "sk-test-key-123"
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.get_api_key("openai")
            
            assert result == "sk-test-key-123"
            mock_keyring.get_password.assert_called_once_with(
                "mailsorter", "openai_api_key"
            )
    
    def test_get_api_key_not_found(self):
        """Returns None when API key not in keyring."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = None
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.get_api_key("nonexistent")
            
            assert result is None
    
    def test_get_api_key_keyring_unavailable(self):
        """Returns None when keyring not available."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            result = secrets_module.get_api_key("openai")
            
            assert result is None
    
    def test_get_api_key_handles_exception(self):
        """Returns None and logs error on exception."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = Exception("Keyring error")
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.get_api_key("openai")
            
            assert result is None


class TestSetApiKey:
    """Tests for API key storage."""
    
    def test_set_api_key_success(self):
        """Successfully stores API key in keyring."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.set_api_key("anthropic", "ant-key-456")
            
            assert result is True
            mock_keyring.set_password.assert_called_once_with(
                "mailsorter", "anthropic_api_key", "ant-key-456"
            )
    
    def test_set_api_key_keyring_unavailable(self):
        """Returns False when keyring not available."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            result = secrets_module.set_api_key("openai", "key")
            
            assert result is False
    
    def test_set_api_key_handles_exception(self):
        """Returns False and logs error on exception."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.set_password.side_effect = Exception("Storage error")
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.set_api_key("openai", "key")
            
            assert result is False


class TestDeleteApiKey:
    """Tests for API key deletion."""
    
    def test_delete_api_key_success(self):
        """Successfully deletes API key from keyring."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.delete_api_key("gemini")
            
            assert result is True
            mock_keyring.delete_password.assert_called_once_with(
                "mailsorter", "gemini_api_key"
            )
    
    def test_delete_api_key_keyring_unavailable(self):
        """Returns False when keyring not available."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            result = secrets_module.delete_api_key("openai")
            
            assert result is False
    
    def test_delete_api_key_not_found(self):
        """Returns False when key doesn't exist."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.errors = MagicMock()
        mock_keyring.errors.PasswordDeleteError = Exception
        mock_keyring.delete_password.side_effect = mock_keyring.errors.PasswordDeleteError()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.delete_api_key("nonexistent")
            
            assert result is False


class TestHmacSecret:
    """Tests for HMAC secret management."""
    
    def test_get_hmac_secret_success(self):
        """Successfully retrieves HMAC secret."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "hmac-secret-xyz"
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.get_hmac_secret()
            
            assert result == "hmac-secret-xyz"
            mock_keyring.get_password.assert_called_with(
                "mailsorter", "hmac_secret"
            )
    
    def test_get_hmac_secret_keyring_unavailable(self):
        """Returns None when keyring not available."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            result = secrets_module.get_hmac_secret()
            
            assert result is None
    
    def test_set_hmac_secret_success(self):
        """Successfully stores HMAC secret."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            result = secrets_module.set_hmac_secret("new-hmac-secret")
            
            assert result is True
            mock_keyring.set_password.assert_called_with(
                "mailsorter", "hmac_secret", "new-hmac-secret"
            )
    
    def test_set_hmac_secret_keyring_unavailable(self):
        """Returns False when keyring not available."""
        import backend.utils.secrets as secrets_module
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', False):
            result = secrets_module.set_hmac_secret("secret")
            
            assert result is False


class TestGenerateHmacSecret:
    """Tests for HMAC secret generation."""
    
    def test_generate_hmac_secret_length(self):
        """Generated secret has correct length (64 hex chars = 32 bytes)."""
        from backend.utils.secrets import generate_hmac_secret
        
        secret = generate_hmac_secret()
        
        assert len(secret) == 64  # 32 bytes = 64 hex chars
    
    def test_generate_hmac_secret_hex_format(self):
        """Generated secret is valid hexadecimal."""
        from backend.utils.secrets import generate_hmac_secret
        
        secret = generate_hmac_secret()
        
        # Should only contain hex chars
        assert all(c in "0123456789abcdef" for c in secret)
    
    def test_generate_hmac_secret_unique(self):
        """Each generated secret is unique."""
        from backend.utils.secrets import generate_hmac_secret
        
        secrets = [generate_hmac_secret() for _ in range(10)]
        
        # All should be unique
        assert len(set(secrets)) == 10
    
    def test_generate_hmac_secret_cryptographically_random(self):
        """Secret generation uses secure random."""
        from backend.utils.secrets import generate_hmac_secret
        
        # Generate many secrets and verify they don't have obvious patterns
        secrets = [generate_hmac_secret() for _ in range(100)]
        
        # Check for some entropy - first chars should be diverse
        first_chars = [s[0] for s in secrets]
        unique_first = len(set(first_chars))
        
        # Should have reasonable diversity (at least 5 different first chars)
        assert unique_first >= 5


class TestServiceName:
    """Tests for service name constant."""
    
    def test_service_name_defined(self):
        """SERVICE_NAME constant is defined."""
        from backend.utils.secrets import SERVICE_NAME
        
        assert SERVICE_NAME == "mailsorter"
    
    def test_service_name_used_consistently(self):
        """All functions use the same service name."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            secrets_module.get_api_key("test")
            secrets_module.set_api_key("test", "key")
            secrets_module.get_hmac_secret()
            secrets_module.set_hmac_secret("secret")
            
            # All calls should use "mailsorter" as service name
            for call in mock_keyring.get_password.call_args_list:
                assert call[0][0] == "mailsorter"
            for call in mock_keyring.set_password.call_args_list:
                assert call[0][0] == "mailsorter"


class TestProviderNameFormatting:
    """Tests for provider name handling in key names."""
    
    def test_api_key_name_format(self):
        """API key name follows {provider}_api_key format."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            secrets_module.get_api_key("openai")
            
            call_args = mock_keyring.get_password.call_args
            assert call_args[0][1] == "openai_api_key"
    
    def test_various_provider_names(self):
        """Different provider names handled correctly."""
        import backend.utils.secrets as secrets_module
        
        mock_keyring = MagicMock()
        
        providers = ["openai", "anthropic", "gemini", "ollama"]
        
        with patch.object(secrets_module, 'KEYRING_AVAILABLE', True), \
             patch.object(secrets_module, 'keyring', mock_keyring):
            
            for provider in providers:
                mock_keyring.reset_mock()
                secrets_module.get_api_key(provider)
                
                call_args = mock_keyring.get_password.call_args
                assert call_args[0][1] == f"{provider}_api_key"
