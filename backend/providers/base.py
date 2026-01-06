"""
Base provider interface for LLM classification.

This module defines the abstract base class and data structures
for all LLM providers (Ollama, OpenAI, Anthropic, Gemini).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ClassificationResult:
    """
    Structured result from LLM classification.
    
    Attributes:
        folder: Target folder name
        confidence: 0.0-1.0 self-assessed confidence score
        reasoning: Optional explanation (for debugging/logging)
        tokens_used: Token count for cost tracking
        latency_ms: Response time in milliseconds
        source: Classification source (llm, cache, rule)
    """
    folder: str
    confidence: float = 0.5
    reasoning: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    source: str = "llm"


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers (Model Agnostic).
    
    Phase 4 updates:
    - Returns ClassificationResult with confidence scores
    - Supports externalized prompt templates
    - Provides metadata for cost/performance tracking
    """

    @abstractmethod
    def classify_email(
        self, 
        subject: str, 
        body: str, 
        available_folders: List[str],
        prompt_template: Optional[str] = None
    ) -> Optional[ClassificationResult]:
        """
        Classify an email and return the most appropriate folder.
        
        Args:
            subject: Email subject (sanitized)
            body: Email body (sanitized, may be empty for headers-only mode)
            available_folders: List of valid folder names
            prompt_template: Optional externalized prompt (from prompt engine)
        
        Returns:
            ClassificationResult with folder and confidence, or None for fallback.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the provider service is available.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Return provider identifier for logging and metrics.
        """
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming responses."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether provider runs locally (no cloud costs)."""
        pass
