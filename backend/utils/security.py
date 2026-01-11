"""
Security utilities for MailSorter.

Provides HMAC signing and verification for classification results,
preventing tampering with email sorting metadata.
"""

import hashlib
import hmac
import logging
from typing import Optional, Tuple

from .secrets import get_hmac_secret, set_hmac_secret, generate_hmac_secret

logger = logging.getLogger(__name__)


def _ensure_secret() -> Optional[str]:
    """Ensure HMAC secret exists, generating if necessary."""
    secret = get_hmac_secret()
    if not secret:
        logger.info("No HMAC secret found. Generating new secret...")
        secret = generate_hmac_secret()
        if set_hmac_secret(secret):
            return secret
        else:
            logger.warning("Could not store HMAC secret. Signatures will not persist.")
            return secret  # Use ephemeral secret for this session
    return secret


def sign_classification(
    category: str, score: float, message_id: str = ""
) -> Optional[str]:
    """
    Create HMAC signature for classification result.

    Args:
        category: The predicted folder/category
        score: Confidence score (0.0 to 1.0)
        message_id: Optional message identifier for binding

    Returns:
        Hex-encoded HMAC-SHA256 signature or None if signing fails
    """
    secret = _ensure_secret()
    if not secret:
        logger.warning("Cannot sign: no HMAC secret available")
        return None

    # Create deterministic message to sign
    message = f"{category}|{score:.4f}|{message_id}"

    try:
        signature = hmac.new(
            secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature
    except Exception as e:
        logger.error(f"Failed to create signature: {e}")
        return None


def verify_signature(
    category: str, score: float, signature: str, message_id: str = ""
) -> bool:
    """
    Verify HMAC signature for classification result.

    Args:
        category: The predicted folder/category
        score: Confidence score
        signature: The signature to verify
        message_id: Optional message identifier

    Returns:
        True if signature is valid, False otherwise
    """
    secret = get_hmac_secret()
    if not secret:
        logger.warning("Cannot verify: no HMAC secret available")
        return False

    # Recreate the message
    message = f"{category}|{score:.4f}|{message_id}"

    try:
        expected = hmac.new(
            secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"Failed to verify signature: {e}")
        return False


def create_signed_result(message_id: str, category: str, score: float) -> dict:
    """
    Create a classification result with HMAC signature.

    Returns:
        Dictionary with category, score, and signature
    """
    signature = sign_classification(category, score, message_id)

    return {
        "id": message_id,
        "category": category,
        "score": round(score, 4),
        "signature": signature,
        "signed": signature is not None,
    }


def verify_signed_result(result: dict) -> Tuple[bool, str]:
    """
    Verify a signed classification result.

    Args:
        result: Dictionary with category, score, signature, and id

    Returns:
        Tuple of (is_valid, reason)
    """
    required_keys = ["category", "score", "signature", "id"]
    for key in required_keys:
        if key not in result:
            return False, f"Missing required field: {key}"

    if result.get("signature") is None:
        return False, "No signature present"

    is_valid = verify_signature(
        result["category"], result["score"], result["signature"], result.get("id", "")
    )

    if is_valid:
        return True, "Signature valid"
    else:
        return False, "Signature verification failed - possible tampering"
