"""Anthropic Claude provider."""

import json
from typing import Optional, AsyncIterator
import httpx

from .base import BaseLLMProvider, ProviderConfig, ChatResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    PRICING = {
        "input": 3.0,
        "output": 15.0,
    }

    AVAILABLE_MODELS = [
        "claude-opus-4.5",
        "claude-sonnet-4.5",
        "claude-haiku-4.5",
        "claude-sonnet-4",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.base_url:
            config.base_url = "https://api.anthropic.com"

    async def chat(self, messages, model=None, max_tokens=None, temperature=None, tools=None, **kwargs):
        model = model or self.config.model or "claude-sonnet-4.5"
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        # Separate system from user messages
        system_msg = None
        api_messages = []
        for msg in self._convert_messages(messages):
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append(msg)

        payload = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg
        if tools:
            payload["tools"] = tools

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        url = f"{self.config.base_url}/v1/messages"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        self._call_count += 1
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)

        return ChatResponse(
            content=content,
            model=data.get("model", model),
            provider="anthropic",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=data.get("stop_reason", "end_turn"),
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
            raw=data,
        )

    async def stream_chat(self, messages, model=None, max_tokens=None, temperature=None, **kwargs) -> AsyncIterator[str]:
        # Streaming implementation simplified
        result = await self.chat(messages, model, max_tokens, temperature, **kwargs)
        yield result.content
