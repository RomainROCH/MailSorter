"""
OpenAI provider for cloud LLM inference.

Implements V5-003: GPT-4o-mini support with structured output.
Uses OpenAI's JSON mode for reliable classification.
"""

import json
import time
from typing import Dict, List, Optional

import requests

from .base import ClassificationResult, LLMProvider
from ..utils.logger import logger
from ..utils.secrets import get_api_key


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider for cloud LLM inference.
    
    Features:
    - GPT-4o-mini (cost-effective) and GPT-4o support
    - Structured JSON output with confidence scores
    - Token usage tracking for cost monitoring
    - Automatic API key retrieval from keyring
    
    Cost Optimization:
    - Uses gpt-4o-mini by default (10x cheaper than GPT-4)
    - Low max_tokens (150) for classification
    - Low temperature (0.1) for consistency
    """

    # System prompt for structured classification
    SYSTEM_PROMPT = """You are an email classification assistant. You analyze emails and categorize them into folders.

IMPORTANT: You MUST respond with valid JSON only. No other text.

Response format:
{"folder": "exact_folder_name", "confidence": 0.85, "reasoning": "brief explanation"}

Rules:
1. "folder" MUST be exactly one of the provided folder names
2. "confidence" is a number between 0.0 (uncertain) and 1.0 (certain)
3. If no folder fits well, use "Inbox" with low confidence
4. Keep "reasoning" brief (under 50 words)"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            config: Provider configuration with:
                - model: Model name (default: gpt-4o-mini)
                - api_key: API key (or retrieved from keyring)
                - base_url: API base URL (for Azure/proxies)
                - timeout: Request timeout in seconds
                - max_tokens: Maximum response tokens
                - temperature: Sampling temperature
        """
        config = config or {}
        self.model = config.get("model", "gpt-4o-mini")
        self.api_key = config.get("api_key") or get_api_key("openai")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 150)
        self.temperature = config.get("temperature", 0.1)
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not configured. "
                "Set it via keyring: python -c \"from backend.utils.secrets import set_api_key; set_api_key('openai', 'sk-...')\""
            )

    def get_name(self) -> str:
        return "openai"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return False

    def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible.
        Uses the models endpoint for a lightweight check.
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            
            if response.status_code == 401:
                logger.error("OpenAI API key is invalid")
                return False
            
            if response.status_code == 429:
                logger.warning("OpenAI rate limit hit during health check")
                return True  # API is reachable, just rate limited
            
            return response.status_code == 200
        except requests.exceptions.Timeout:
            logger.warning("OpenAI health check timed out")
            return False
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False

    def classify_email(
        self, 
        subject: str, 
        body: str, 
        available_folders: List[str],
        prompt_template: Optional[str] = None
    ) -> Optional[ClassificationResult]:
        """
        Classify email using OpenAI with structured JSON output.
        """
        start_time = time.time()
        
        # Build user message
        user_message = self._build_user_message(subject, body, available_folders, prompt_template)
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                },
                timeout=self.timeout
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 429:
                logger.warning("OpenAI rate limit exceeded")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Extract response content
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            # Parse JSON response
            return self._parse_response(content, available_folders, tokens_used, latency_ms)
            
        except requests.exceptions.Timeout:
            logger.error("OpenAI request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenAI HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None

    def _build_user_message(
        self, 
        subject: str, 
        body: str, 
        folders: List[str],
        template: Optional[str] = None
    ) -> str:
        """Build the user message for classification."""
        if template:
            return template
        
        folders_str = json.dumps(folders)
        body_snippet = body[:1500] if body else "(no body)"
        
        return f"""Classify this email into one of the available folders.

Available folders: {folders_str}

Email Subject: {subject}
Email Body: {body_snippet}

Respond with JSON only."""

    def _parse_response(
        self, 
        content: str, 
        available_folders: List[str],
        tokens_used: int,
        latency_ms: int
    ) -> Optional[ClassificationResult]:
        """Parse and validate the JSON response."""
        try:
            data = json.loads(content)
            folder = str(data.get("folder", "")).strip()
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning")
            
            # Validate folder exists
            if folder not in available_folders:
                # Try case-insensitive match
                folder_lower = folder.lower()
                for f in available_folders:
                    if f.lower() == folder_lower:
                        folder = f
                        break
                else:
                    # Fallback to Inbox
                    if "Inbox" in available_folders:
                        logger.warning(f"OpenAI suggested invalid folder '{folder}', using Inbox")
                        folder = "Inbox"
                        confidence = min(confidence, 0.4)
                    else:
                        return None
            
            return ClassificationResult(
                folder=folder,
                confidence=min(max(confidence, 0.0), 1.0),
                reasoning=reasoning,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                source="llm"
            )
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            return None
