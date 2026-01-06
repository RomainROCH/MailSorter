"""
Secrets management for MailSorter using system keyring.

Provides secure storage for API keys and sensitive configuration.
Uses the `keyring` library which supports:
- Windows Credential Manager
- macOS Keychain
- Linux Secret Service (GNOME Keyring, KWallet)

Falls back to warning if keyring is unavailable.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Service name for keyring entries
SERVICE_NAME = "mailsorter"

# Try to import keyring, but don't fail if unavailable
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning(
        "keyring package not installed. API keys will not be stored securely. "
        "Install with: pip install keyring"
    )


def is_keyring_available() -> bool:
    """Check if secure keyring storage is available."""
    return KEYRING_AVAILABLE


def get_api_key(provider: str) -> Optional[str]:
    """
    Retrieve API key for a provider from secure storage.
    
    Args:
        provider: Provider name (e.g., 'openai', 'anthropic', 'gemini')
    
    Returns:
        API key string or None if not found
    """
    if not KEYRING_AVAILABLE:
        logger.warning(f"Keyring unavailable. Cannot retrieve API key for {provider}")
        return None
    
    try:
        key = keyring.get_password(SERVICE_NAME, f"{provider}_api_key")
        if key:
            logger.debug(f"Retrieved API key for {provider} from keyring")
        return key
    except Exception as e:
        logger.error(f"Failed to retrieve API key for {provider}: {e}")
        return None


def set_api_key(provider: str, api_key: str) -> bool:
    """
    Store API key for a provider in secure storage.
    
    Args:
        provider: Provider name (e.g., 'openai', 'anthropic', 'gemini')
        api_key: The API key to store
    
    Returns:
        True if successful, False otherwise
    """
    if not KEYRING_AVAILABLE:
        logger.error(
            f"Keyring unavailable. Cannot store API key for {provider}. "
            "Install keyring package for secure storage."
        )
        return False
    
    try:
        keyring.set_password(SERVICE_NAME, f"{provider}_api_key", api_key)
        logger.info(f"Stored API key for {provider} in keyring")
        return True
    except Exception as e:
        logger.error(f"Failed to store API key for {provider}: {e}")
        return False


def delete_api_key(provider: str) -> bool:
    """
    Remove API key for a provider from secure storage.
    
    Args:
        provider: Provider name
    
    Returns:
        True if successful, False otherwise
    """
    if not KEYRING_AVAILABLE:
        return False
    
    try:
        keyring.delete_password(SERVICE_NAME, f"{provider}_api_key")
        logger.info(f"Deleted API key for {provider} from keyring")
        return True
    except keyring.errors.PasswordDeleteError:
        logger.warning(f"No API key found for {provider} to delete")
        return False
    except Exception as e:
        logger.error(f"Failed to delete API key for {provider}: {e}")
        return False


def get_hmac_secret() -> Optional[str]:
    """
    Retrieve HMAC signing secret from secure storage.
    
    Returns:
        HMAC secret string or None if not found
    """
    if not KEYRING_AVAILABLE:
        return None
    
    try:
        return keyring.get_password(SERVICE_NAME, "hmac_secret")
    except Exception as e:
        logger.error(f"Failed to retrieve HMAC secret: {e}")
        return None


def set_hmac_secret(secret: str) -> bool:
    """
    Store HMAC signing secret in secure storage.
    
    Args:
        secret: The HMAC secret to store
    
    Returns:
        True if successful, False otherwise
    """
    if not KEYRING_AVAILABLE:
        logger.error("Keyring unavailable. Cannot store HMAC secret.")
        return False
    
    try:
        keyring.set_password(SERVICE_NAME, "hmac_secret", secret)
        logger.info("Stored HMAC secret in keyring")
        return True
    except Exception as e:
        logger.error(f"Failed to store HMAC secret: {e}")
        return False


def generate_hmac_secret() -> str:
    """
    Generate a cryptographically secure HMAC secret.
    
    Returns:
        A 32-byte hex-encoded secret
    """
    import secrets
    return secrets.token_hex(32)
