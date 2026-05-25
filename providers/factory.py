"""Provider factory - creates the right provider based on configuration."""

import logging
from typing import Optional

from .base import BaseLLMProvider, ProviderConfig, ProviderType
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .google import GoogleProvider
from .mimo import MiMoProvider
from .ollama import OllamaProvider

logger = logging.getLogger("cortexflow.providers.factory")


_PROVIDER_REGISTRY = {
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.GOOGLE: GoogleProvider,
    ProviderType.MIMO: MiMoProvider,
    ProviderType.OLLAMA: OllamaProvider,
}


class ProviderFactory:
    """Factory for instantiating LLM providers from configuration."""

    @staticmethod
    def create(config: ProviderConfig) -> BaseLLMProvider:
        """Create a provider instance based on the config."""
        provider_class = _PROVIDER_REGISTRY.get(config.provider_type)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {config.provider_type}")
        return provider_class(config)

    @staticmethod
    def from_dict(data: dict) -> BaseLLMProvider:
        """Create a provider from a dict configuration.

        Example:
            {
                "provider_type": "mimo",
                "api_key": "sk-...",
                "model": "mimo-v2.5-pro",
                "base_url": "https://token-plan-sgp.xiaomimimo.com/v1"
            }
        """
        provider_type = ProviderType(data["provider_type"])
        config = ProviderConfig(
            provider_type=provider_type,
            api_key=data["api_key"],
            base_url=data.get("base_url"),
            model=data.get("model", ""),
            max_tokens=data.get("max_tokens", 4096),
            temperature=data.get("temperature", 0.7),
            timeout=data.get("timeout", 300),
            extra_headers=data.get("extra_headers", {}),
        )
        return ProviderFactory.create(config)


_default_provider = None


def get_provider(config: Optional[ProviderConfig] = None) -> BaseLLMProvider:
    """Get a singleton default provider, or create one with custom config."""
    global _default_provider
    if config is not None:
        return ProviderFactory.create(config)
    if _default_provider is None:
        raise RuntimeError("No default provider configured. Pass a ProviderConfig.")
    return _default_provider


def set_default_provider(provider: BaseLLMProvider):
    """Set the singleton default provider."""
    global _default_provider
    _default_provider = provider
