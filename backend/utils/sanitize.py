"""
Input sanitization utilities for MailSorter.

Provides protection against prompt injection and malformed inputs
before sending data to LLM providers.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum lengths to prevent resource exhaustion
MAX_SUBJECT_LENGTH = 500
MAX_BODY_LENGTH = 2000
MAX_FOLDER_NAME_LENGTH = 100
MAX_FOLDERS_COUNT = 50

# Patterns that could be used for prompt injection
INJECTION_PATTERNS = [
    # Instruction override attempts
    r'(?i)ignore\s+(previous|all|above)\s+(instructions?|prompts?)',
    r'(?i)disregard\s+(previous|all|above)',
    r'(?i)forget\s+(everything|all|previous)',
    r'(?i)new\s+instructions?:',
    r'(?i)system\s*:\s*',
    r'(?i)assistant\s*:\s*',
    r'(?i)user\s*:\s*',
    # Role manipulation
    r'(?i)you\s+are\s+now',
    r'(?i)pretend\s+(to\s+be|you\s+are)',
    r'(?i)act\s+as\s+(if|a)',
    # Delimiter injection
    r'```system',
    r'<\|im_start\|>',
    r'<\|im_end\|>',
    r'\[INST\]',
    r'\[/INST\]',
]

# Compiled patterns for efficiency
_compiled_patterns = [re.compile(p) for p in INJECTION_PATTERNS]


def sanitize_text(text: str, max_length: int = MAX_BODY_LENGTH) -> str:
    """
    Sanitize text input for safe LLM processing.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Convert to string if needed
    if not isinstance(text, str):
        text = str(text)
    
    # Remove null bytes and control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize unicode to prevent homograph attacks
    try:
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
    except Exception:
        pass
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length] + "..."
        logger.debug(f"Text truncated to {max_length} characters")
    
    # Detect and neutralize injection patterns
    injection_found = False
    for pattern in _compiled_patterns:
        if pattern.search(text):
            injection_found = True
            text = pattern.sub('[FILTERED]', text)
    
    if injection_found:
        logger.warning("Potential prompt injection detected and neutralized")
    
    return text


def sanitize_subject(subject: str) -> str:
    """Sanitize email subject line."""
    return sanitize_text(subject, MAX_SUBJECT_LENGTH)


def sanitize_body(body: str) -> str:
    """Sanitize email body text."""
    return sanitize_text(body, MAX_BODY_LENGTH)


def sanitize_folder_name(name: str) -> str:
    """
    Sanitize folder name for safe use.
    
    Args:
        name: Folder name to sanitize
    
    Returns:
        Sanitized folder name
    """
    if not name:
        return ""
    
    # Remove control characters
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    
    # Remove path traversal attempts
    name = name.replace('..', '')
    name = name.replace('/', '')
    name = name.replace('\\', '')
    
    # Truncate
    if len(name) > MAX_FOLDER_NAME_LENGTH:
        name = name[:MAX_FOLDER_NAME_LENGTH]
    
    return name.strip()


def sanitize_folder_list(folders: list) -> list:
    """
    Sanitize list of folder names.
    
    Args:
        folders: List of folder names
    
    Returns:
        Sanitized list with valid folder names only
    """
    if not folders or not isinstance(folders, list):
        return []
    
    # Limit number of folders
    folders = folders[:MAX_FOLDERS_COUNT]
    
    # Sanitize each folder name
    sanitized = []
    for folder in folders:
        if isinstance(folder, str):
            clean = sanitize_folder_name(folder)
            if clean:
                sanitized.append(clean)
    
    return sanitized


def sanitize_email_payload(payload: dict) -> dict:
    """
    Sanitize entire email classification payload.
    
    Args:
        payload: Dictionary with subject, body, folders, etc.
    
    Returns:
        Sanitized payload
    """
    if not isinstance(payload, dict):
        logger.warning("Invalid payload type, returning empty dict")
        return {}
    
    sanitized = {}
    
    # Preserve message ID (validate it's a reasonable value)
    if "id" in payload:
        msg_id = payload["id"]
        if isinstance(msg_id, (int, str)):
            sanitized["id"] = msg_id
    
    # Sanitize text fields
    if "subject" in payload:
        sanitized["subject"] = sanitize_subject(str(payload["subject"]))
    
    if "body" in payload:
        sanitized["body"] = sanitize_body(str(payload["body"]))
    
    if "from" in payload:
        # Email addresses - basic sanitization
        from_addr = str(payload["from"])[:200]
        sanitized["from"] = re.sub(r'[\x00-\x1f\x7f]', '', from_addr)
    
    if "folders" in payload:
        sanitized["folders"] = sanitize_folder_list(payload["folders"])
    
    return sanitized


def is_safe_for_llm(text: str) -> bool:
    """
    Check if text appears safe for LLM processing.
    
    Args:
        text: Text to check
    
    Returns:
        True if no injection patterns detected
    """
    if not text:
        return True
    
    for pattern in _compiled_patterns:
        if pattern.search(text):
            return False
    
    return True
