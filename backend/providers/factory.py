"""
Provider factory for LLM provider instantiation.

Implements INT-001: Single entry point to instantiate any provider.
Uses a registry pattern for clean provider management.
"""

import logging
from typing import Dict, List, Optional, Type

from .base import LLMProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for creating and managing LLM provider instances.

    Features:
    - Registry pattern for provider classes
    - Singleton caching for provider instances
    - Lazy loading of providers
    - Fallback handling
    """

    _providers: Dict[str, Type[LLMProvider]] = {}
    _instances: Dict[str, LLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """
        Register a provider class.

        Args:
            name: Provider identifier (e.g., 'ollama', 'openai')
            provider_class: LLMProvider subclass
        """
        cls._providers[name] = provider_class
        logger.debug(f"Registered provider: {name}")

    @classmethod
    def create(
        cls, name: str, config: Optional[Dict] = None, use_cache: bool = True
    ) -> LLMProvider:
        """
        Create or retrieve a provider instance.

        Args:
            name: Provider name (ollama, openai, anthropic, gemini)
            config: Provider-specific configuration
            use_cache: If True, return cached instance for same name

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider name is unknown
        """
        # Return cached instance if available
        cache_key = f"{name}:{hash(str(config))}" if config else name
        if use_cache and cache_key in cls._instances:
            return cls._instances[cache_key]

        # Check if provider is registered
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(f"Unknown provider: '{name}'. Available: {available}")

        # Create new instance
        try:
            instance = cls._providers[name](config or {})

            if use_cache:
                cls._instances[cache_key] = instance

            logger.info(f"Created provider instance: {name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create provider '{name}': {e}")
            raise

    @classmethod
    def get_or_fallback(
        cls, name: str, config: Optional[Dict] = None, fallback: str = "ollama"
    ) -> LLMProvider:
        """
        Get provider with fallback to another provider on failure.

        Args:
            name: Primary provider name
            config: Provider configuration
            fallback: Fallback provider name

        Returns:
            Provider instance (primary or fallback)
        """
        try:
            return cls.create(name, config)
        except Exception as e:
            logger.warning(
                f"Primary provider '{name}' failed: {e}. Falling back to '{fallback}'"
            )
            return cls.create(fallback)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def get_local_providers(cls) -> List[str]:
        """List providers that run locally (no cloud costs)."""
        local = []
        for name, provider_class in cls._providers.items():
            try:
                # Check is_local property on a temporary instance
                temp = provider_class({})
                if temp.is_local:
                    local.append(name)
            except Exception:
                pass
        return local

    @classmethod
    def get_cloud_providers(cls) -> List[str]:
        """List providers that require cloud API (paid)."""
        all_providers = set(cls._providers.keys())
        local = set(cls.get_local_providers())
        return list(all_providers - local)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider is registered."""
        return name in cls._providers

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached provider instances."""
        cls._instances.clear()
        logger.debug("Cleared provider instance cache")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a provider (mainly for testing).

        Returns:
            True if provider was unregistered
        """
        if name in cls._providers:
            del cls._providers[name]
            # Also clear any cached instances
            keys_to_remove = [k for k in cls._instances if k.startswith(name)]
            for k in keys_to_remove:
                del cls._instances[k]
            return True
        return False


def _auto_register_providers():
    """
    Auto-register all available providers.
    Called on module import.
    """
    from .ollama_provider import OllamaProvider

    ProviderFactory.register("ollama", OllamaProvider)

    # Try to import optional providers
    try:
        from .openai_provider import OpenAIProvider

        ProviderFactory.register("openai", OpenAIProvider)
    except ImportError:
        logger.debug("OpenAI provider not available")

    try:
        from .anthropic_provider import AnthropicProvider

        ProviderFactory.register("anthropic", AnthropicProvider)
    except ImportError:
        logger.debug("Anthropic provider not available")

    try:
        from .gemini_provider import GeminiProvider

        ProviderFactory.register("gemini", GeminiProvider)
    except ImportError:
        logger.debug("Gemini provider not available")


# Auto-register on import
_auto_register_providers()
