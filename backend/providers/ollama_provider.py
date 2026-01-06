"""
Ollama provider for local LLM inference.

Uses Ollama's HTTP API for email classification with structured output.
This is the primary provider for cost-free local inference.
"""

import json
import re
import time
from typing import Dict, List, Optional

import requests

from .base import ClassificationResult, LLMProvider
from ..utils.logger import logger


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference.
    
    Features:
    - Zero cloud cost (runs locally)
    - Supports various models (llama3, mistral, gemma, etc.)
    - Structured output with confidence extraction
    - Anti-hallucination post-processing
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Ollama provider.
        
        Args:
            config: Provider configuration dict with:
                - base_url: Ollama API URL (default: http://localhost:11434)
                - model: Model name (default: llama3)
                - timeout: Request timeout in seconds (default: 30)
        """
        config = config or {}
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3")
        self.timeout = config.get("timeout", 30)
        self.api_endpoint = f"{self.base_url}/api/generate"

    def get_name(self) -> str:
        return "ollama"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return True

    def health_check(self) -> bool:
        """
        Check if Ollama is running and the model is available.
        Uses the /api/tags endpoint to verify connectivity.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                logger.warning(f"Ollama health check returned status {response.status_code}")
                return False
            
            # Verify the configured model is available
            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            
            if self.model not in models and f"{self.model}:latest" not in [m.get("name", "") for m in data.get("models", [])]:
                logger.warning(f"Model '{self.model}' not found in Ollama. Available: {models}")
                # Still return True if Ollama is running, just warn about model
            
            return True
        except requests.exceptions.Timeout:
            logger.warning("Ollama health check timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to Ollama - is it running?")
            return False
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def classify_email(
        self, 
        subject: str, 
        body: str, 
        available_folders: List[str],
        prompt_template: Optional[str] = None
    ) -> Optional[ClassificationResult]:
        """
        Classify email using Ollama with structured output.
        
        Uses JSON mode to extract both folder and confidence score.
        """
        start_time = time.time()
        
        # Build prompt
        if prompt_template:
            prompt = prompt_template
        else:
            prompt = self._build_default_prompt(subject, body, available_folders)
        
        payload = {
            "model": self.model, 
            "prompt": prompt, 
            "stream": False,
            "format": "json"  # Request JSON output from Ollama
        }

        try:
            response = requests.post(self.api_endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            raw_response = result.get("response", "").strip()
            
            # Parse structured response
            classification = self._parse_response(raw_response, available_folders)
            
            if classification:
                classification.latency_ms = latency_ms
                classification.tokens_used = result.get("eval_count", 0)
                return classification
            
            return None

        except requests.exceptions.Timeout:
            logger.error("Ollama timeout - falling back to Inbox")
            return None
        except Exception as e:
            logger.error(f"Ollama inference error: {e}")
            return None

    def _build_default_prompt(self, subject: str, body: str, folders: List[str]) -> str:
        """Build the default classification prompt with JSON output."""
        folders_str = json.dumps(folders)
        
        return f"""You are an email classification assistant. Analyze the email and determine the best folder.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{{"folder": "folder_name", "confidence": 0.85, "reasoning": "brief explanation"}}

Rules:
1. "folder" must be EXACTLY one of: {folders_str}
2. "confidence" must be a number between 0.0 and 1.0
3. If unsure, use "Inbox" with low confidence (0.3-0.5)
4. "reasoning" is a brief explanation (optional but helpful)

Email Subject: {subject}
Email Body: {body[:1500] if body else "(no body)"}

Your JSON response:"""

    def _parse_response(self, response: str, available_folders: List[str]) -> Optional[ClassificationResult]:
        """
        Parse LLM response and validate folder selection.
        
        Handles both JSON and plain text responses.
        """
        # Try parsing as JSON first
        try:
            data = json.loads(response)
            folder = data.get("folder", "").strip()
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning")
            
            # Validate folder
            if folder in available_folders:
                return ClassificationResult(
                    folder=folder,
                    confidence=min(max(confidence, 0.0), 1.0),  # Clamp to 0-1
                    reasoning=reasoning,
                    source="llm"
                )
            elif "Inbox" in available_folders:
                logger.warning(f"Hallucination detected: '{folder}' not in available folders")
                return ClassificationResult(
                    folder="Inbox",
                    confidence=0.3,
                    reasoning=f"Fallback: LLM suggested '{folder}' which is not available",
                    source="llm"
                )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        
        # Fallback: Try to extract folder name from plain text
        response_clean = response.strip().strip('"\'')
        
        # Check if response exactly matches a folder
        if response_clean in available_folders:
            return ClassificationResult(
                folder=response_clean,
                confidence=0.6,  # Lower confidence for plain text response
                reasoning="Extracted from plain text response",
                source="llm"
            )
        
        # Check if any folder name appears in response
        for folder in available_folders:
            if folder.lower() in response.lower():
                return ClassificationResult(
                    folder=folder,
                    confidence=0.5,
                    reasoning=f"Matched '{folder}' in response",
                    source="llm"
                )
        
        # Fallback to Inbox
        if "Inbox" in available_folders:
            return ClassificationResult(
                folder="Inbox",
                confidence=0.3,
                reasoning="Unable to parse LLM response",
                source="llm"
            )
        
        logger.warning(f"Could not parse Ollama response: {response[:100]}")
        return None
