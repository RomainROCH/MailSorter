"""
LLM Providers package for MailSorter.

This package provides a unified interface for various LLM providers:
- Ollama: Local LLM inference (free, privacy-focused)
- OpenAI: GPT-4o-mini and GPT-4o (cloud)
- Anthropic: Claude 3 models (cloud)
- Gemini: Google's Gemini models (cloud)

Use the ProviderFactory for creating provider instances:
    from backend.providers import ProviderFactory
    provider = ProviderFactory.create("ollama", config)
"""

from .base import ClassificationResult, LLMProvider
from .factory import ProviderFactory
from .ollama_provider import OllamaProvider

from typing import Optional, Type

# Optional cloud providers (may not be configured)
OpenAIProvider: Optional[Type[LLMProvider]]
try:
    from .openai_provider import OpenAIProvider as _OpenAIProvider

    OpenAIProvider = _OpenAIProvider
except ImportError:
    OpenAIProvider = None

AnthropicProvider: Optional[Type[LLMProvider]]
try:
    from .anthropic_provider import AnthropicProvider as _AnthropicProvider

    AnthropicProvider = _AnthropicProvider
except ImportError:
    AnthropicProvider = None

GeminiProvider: Optional[Type[LLMProvider]]
try:
    from .gemini_provider import GeminiProvider as _GeminiProvider

    GeminiProvider = _GeminiProvider
except ImportError:
    GeminiProvider = None

__all__ = [
    "ClassificationResult",
    "LLMProvider",
    "ProviderFactory",
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
]
