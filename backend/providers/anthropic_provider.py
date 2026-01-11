"""
Anthropic provider for Claude LLM inference.

Implements V5-019: Claude 3 support with structured output.
Uses Claude's native JSON mode for reliable classification.
"""

import json
import time
from typing import Dict, List, Optional

import requests

from .base import ClassificationResult, LLMProvider
from ..utils.logger import logger
from ..utils.secrets import get_api_key


class AnthropicProvider(LLMProvider):
    """
    Anthropic provider for Claude LLM inference.

    Features:
    - Claude 3 Haiku (fastest/cheapest) and Sonnet support
    - Structured JSON output with confidence scores
    - Token usage tracking for cost monitoring
    - Automatic API key retrieval from keyring

    Cost Optimization:
    - Uses claude-3-haiku by default (cheapest Claude model)
    - Low max_tokens for classification
    - Structured prompting for consistent output
    """

    # System prompt for structured classification
    SYSTEM_PROMPT = """You are an email classification assistant. Analyze emails and categorize them into folders.

You MUST respond with valid JSON only, no other text. Format:
{"folder": "exact_folder_name", "confidence": 0.85, "reasoning": "brief explanation"}

Rules:
1. "folder" MUST be exactly one of the provided folder names
2. "confidence" is a number between 0.0 (uncertain) and 1.0 (certain)
3. If no folder fits well, use "Inbox" with low confidence
4. Keep "reasoning" brief (under 50 words)"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with:
                - model: Model name (default: claude-3-haiku-20240307)
                - api_key: API key (or retrieved from keyring)
                - timeout: Request timeout in seconds
                - max_tokens: Maximum response tokens
        """
        config = config or {}
        self.model = config.get("model", "claude-3-haiku-20240307")
        self.api_key = config.get("api_key") or get_api_key("anthropic")
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 150)

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Set it via keyring: python -c \"from backend.utils.secrets import set_api_key; set_api_key('anthropic', 'sk-ant-...')\""
            )

    def get_name(self) -> str:
        return "anthropic"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return False

    def health_check(self) -> bool:
        """
        Check if Anthropic API is accessible.
        Uses a minimal message request to verify connectivity.
        """
        try:
            # Anthropic doesn't have a dedicated health endpoint
            # We do a minimal API call to check authentication
            response = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                timeout=10,
            )

            if response.status_code == 401:
                logger.error("Anthropic API key is invalid")
                return False

            if response.status_code == 429:
                logger.warning("Anthropic rate limit hit during health check")
                return True  # API is reachable, just rate limited

            return response.status_code == 200
        except requests.exceptions.Timeout:
            logger.warning("Anthropic health check timed out")
            return False
        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False

    def classify_email(
        self,
        subject: str,
        body: str,
        available_folders: List[str],
        prompt_template: Optional[str] = None,
    ) -> Optional[ClassificationResult]:
        """
        Classify email using Anthropic Claude with structured output.
        """
        start_time = time.time()

        # Build user message
        user_message = self._build_user_message(
            subject, body, available_folders, prompt_template
        )

        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": self.SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}],
                },
                timeout=self.timeout,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 429:
                logger.warning("Anthropic rate limit exceeded")
                return None

            response.raise_for_status()
            data = response.json()

            # Extract response content
            content_blocks = data.get("content", [])
            if not content_blocks:
                logger.error("Empty response from Anthropic")
                return None

            content = content_blocks[0].get("text", "")

            # Calculate tokens (Anthropic uses input_tokens + output_tokens)
            usage = data.get("usage", {})
            tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            # Parse JSON response
            return self._parse_response(
                content, available_folders, tokens_used, latency_ms
            )

        except requests.exceptions.Timeout:
            logger.error("Anthropic request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Anthropic HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return None

    def _build_user_message(
        self,
        subject: str,
        body: str,
        folders: List[str],
        template: Optional[str] = None,
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
        latency_ms: int,
    ) -> Optional[ClassificationResult]:
        """Parse and validate the JSON response."""
        # Try to extract JSON from response (Claude sometimes adds explanation)
        try:
            # First try direct parse
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            # Try to find JSON in response
            import re

            json_match = re.search(r"\{[^}]+\}", content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Anthropic response: {content[:200]}")
                    return None
            else:
                logger.error(f"No JSON found in Anthropic response: {content[:200]}")
                return None

        try:
            folder = str(data.get("folder", "")).strip()
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning")

            # Validate folder exists
            if folder not in available_folders:
                folder_lower = folder.lower()
                for f in available_folders:
                    if f.lower() == folder_lower:
                        folder = f
                        break
                else:
                    if "Inbox" in available_folders:
                        logger.warning(
                            f"Anthropic suggested invalid folder '{folder}', using Inbox"
                        )
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
                source="llm",
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to process Anthropic response: {e}")
            return None
