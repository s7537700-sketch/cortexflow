"""Tests for LLM providers."""

import pytest
from providers.base import BaseLLMProvider, ProviderConfig, ProviderType, ChatResponse
from providers.factory import ProviderFactory
from providers.mimo import MiMoProvider
from providers.anthropic import AnthropicProvider
from providers.openai import OpenAIProvider
from providers.google import GoogleProvider
from providers.ollama import OllamaProvider


class TestProviderFactory:
    def test_create_mimo_provider(self):
        config = ProviderConfig(
            provider_type=ProviderType.MIMO,
            api_key="test",
            model="mimo-v2.5",
        )
        provider = ProviderFactory.create(config)
        assert isinstance(provider, MiMoProvider)

    def test_create_anthropic_provider(self):
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="test",
            model="claude-sonnet-4.5",
        )
        provider = ProviderFactory.create(config)
        assert isinstance(provider, AnthropicProvider)

    def test_from_dict(self):
        provider = ProviderFactory.from_dict({
            "provider_type": "openai",
            "api_key": "test",
            "model": "gpt-4o",
        })
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            ProviderFactory.from_dict({"provider_type": "nonexistent", "api_key": "x"})


class TestProviderPricing:
    def test_mimo_pricing(self):
        config = ProviderConfig(
            provider_type=ProviderType.MIMO,
            api_key="test",
            model="mimo-v2.5",
        )
        provider = MiMoProvider(config)
        cost = provider.estimate_cost(1_000_000, 100_000)
        # $0.14 per 1M input + $0.56 per 1M output * 0.1
        expected = 0.14 + (0.56 * 0.1)
        assert abs(cost - expected) < 0.001

    def test_anthropic_pricing(self):
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            api_key="test",
            model="claude-sonnet-4.5",
        )
        provider = AnthropicProvider(config)
        cost = provider.estimate_cost(1_000_000, 1_000_000)
        # $3.0 input + $15.0 output
        assert abs(cost - 18.0) < 0.001

    def test_ollama_pricing_is_free(self):
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            api_key="local",
            model="llama3.3:70b",
        )
        provider = OllamaProvider(config)
        cost = provider.estimate_cost(10_000_000, 1_000_000)
        assert cost == 0.0


class TestChatResponse:
    def test_total_tokens_property(self):
        response = ChatResponse(
            content="hello",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert response.total_tokens == 150


class TestProviderInfo:
    def test_get_info(self, mock_provider_config):
        provider = ProviderFactory.create(mock_provider_config)
        info = provider.get_info()
        assert info["provider"] == "mimo"
        assert info["model"] == "mimo-v2.5"
        assert "pricing" in info
