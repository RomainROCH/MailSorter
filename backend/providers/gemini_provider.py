"""
Google Gemini provider for cloud LLM inference.

Implements V5-020: Gemini API support with structured output.
Uses Gemini's native JSON mode for reliable classification.
"""

import json
import time
from typing import Dict, List, Optional

import requests

from .base import ClassificationResult, LLMProvider
from ..utils.logger import logger
from ..utils.secrets import get_api_key


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider for cloud LLM inference.

    Features:
    - Gemini 2.0 Flash (fast/cheap) and Pro support
    - Structured JSON output with confidence scores
    - Token usage tracking for cost monitoring
    - Automatic API key retrieval from keyring

    Cost Optimization:
    - Uses gemini-2.0-flash by default (cheapest Gemini model)
    - Low max_tokens for classification
    - Structured prompting for consistent output
    """

    # System instruction for structured classification
    SYSTEM_INSTRUCTION = """You are an email classification assistant. Analyze emails and categorize them into folders.

You MUST respond with valid JSON only, no other text. Format:
{"folder": "exact_folder_name", "confidence": 0.85, "reasoning": "brief explanation"}

Rules:
1. "folder" MUST be exactly one of the provided folder names
2. "confidence" is a number between 0.0 (uncertain) and 1.0 (certain)
3. If no folder fits well, use "Inbox" with low confidence
4. Keep "reasoning" brief (under 50 words)"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Gemini provider.

        Args:
            config: Provider configuration with:
                - model: Model name (default: gemini-2.0-flash)
                - api_key: API key (or retrieved from keyring)
                - timeout: Request timeout in seconds
                - max_tokens: Maximum response tokens
        """
        config = config or {}
        self.model = config.get("model", "gemini-2.0-flash")
        self.api_key = config.get("api_key") or get_api_key("gemini")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 150)

        # Gemini API endpoint
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        if not self.api_key:
            raise ValueError(
                "Gemini API key not configured. "
                "Set it via keyring: python -c \"from backend.utils.secrets import set_api_key; set_api_key('gemini', 'AIza...')\""
            )

    def get_name(self) -> str:
        return "gemini"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return False

    def health_check(self) -> bool:
        """
        Check if Gemini API is accessible.
        Uses the models list endpoint for a lightweight check.
        """
        try:
            response = requests.get(
                f"{self.base_url}/models?key={self.api_key}", timeout=10
            )

            if response.status_code == 400 or response.status_code == 403:
                logger.error("Gemini API key is invalid")
                return False

            if response.status_code == 429:
                logger.warning("Gemini rate limit hit during health check")
                return True  # API is reachable, just rate limited

            return response.status_code == 200
        except requests.exceptions.Timeout:
            logger.warning("Gemini health check timed out")
            return False
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False

    def classify_email(
        self,
        subject: str,
        body: str,
        available_folders: List[str],
        prompt_template: Optional[str] = None,
    ) -> Optional[ClassificationResult]:
        """
        Classify email using Gemini with structured JSON output.
        """
        start_time = time.time()

        # Build user message
        user_message = self._build_user_message(
            subject, body, available_folders, prompt_template
        )

        try:
            endpoint = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

            response = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": self.SYSTEM_INSTRUCTION}]},
                    "contents": [{"parts": [{"text": user_message}]}],
                    "generationConfig": {
                        "maxOutputTokens": self.max_tokens,
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=self.timeout,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 429:
                logger.warning("Gemini rate limit exceeded")
                return None

            response.raise_for_status()
            data = response.json()

            # Extract response content
            candidates = data.get("candidates", [])
            if not candidates:
                logger.error("No candidates in Gemini response")
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                logger.error("No parts in Gemini response")
                return None

            text = parts[0].get("text", "")

            # Get token usage
            usage = data.get("usageMetadata", {})
            tokens_used = usage.get("promptTokenCount", 0) + usage.get(
                "candidatesTokenCount", 0
            )

            # Parse JSON response
            return self._parse_response(
                text, available_folders, tokens_used, latency_ms
            )

        except requests.exceptions.Timeout:
            logger.error("Gemini request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Gemini HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini error: {e}")
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
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            # Try to find JSON in response
            import re

            json_match = re.search(r"\{[^}]+\}", content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Gemini response: {content[:200]}")
                    return None
            else:
                logger.error(f"No JSON found in Gemini response: {content[:200]}")
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
                            f"Gemini suggested invalid folder '{folder}', using Inbox"
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
            logger.error(f"Failed to process Gemini response: {e}")
            return None
