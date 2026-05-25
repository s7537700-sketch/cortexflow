"""
Base LLM Provider - Abstract interface for all language model providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator
from enum import Enum


class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    MIMO = "mimo"
    OLLAMA = "ollama"


@dataclass
class ChatMessage:
    """Standardized chat message across all providers."""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ChatResponse:
    """Standardized response across all providers."""
    content: str
    reasoning_content: Optional[str] = None  # MiMo, o1-style models
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    finish_reason: str = "stop"
    cost_usd: float = 0.0
    raw: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ProviderConfig:
    """Provider configuration."""
    provider_type: ProviderType
    api_key: str
    base_url: Optional[str] = None
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 300
    extra_headers: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Every concrete provider implementation must inherit from this class
    and implement at minimum chat() and stream_chat().
    """

    # Pricing per 1M tokens (USD) - subclasses override
    PRICING = {
        "input": 0.0,
        "output": 0.0,
    }

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_name = config.provider_type.value
        self._call_count = 0

    @abstractmethod
    async def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list] = None,
        **kwargs
    ) -> ChatResponse:
        """Send a chat completion request and return the response."""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a chat completion response chunk by chunk."""
        pass

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD based on token counts."""
        input_cost = (prompt_tokens / 1_000_000) * self.PRICING.get("input", 0.0)
        output_cost = (completion_tokens / 1_000_000) * self.PRICING.get("output", 0.0)
        return round(input_cost + output_cost, 6)

    def get_info(self) -> dict:
        """Return provider metadata."""
        return {
            "provider": self.provider_name,
            "model": self.config.model,
            "base_url": self.config.base_url,
            "call_count": self._call_count,
            "pricing": self.PRICING,
        }

    def _convert_messages(self, messages: list) -> list:
        """Convert ChatMessage objects to provider-specific format."""
        result = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                result.append({"role": msg.role, "content": msg.content})
            else:
                result.append(msg)
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.config.model}>"
