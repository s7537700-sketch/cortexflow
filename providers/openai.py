"""OpenAI GPT provider."""

from typing import Optional, AsyncIterator
import httpx
import json

from .base import BaseLLMProvider, ProviderConfig, ChatResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-4 / GPT-5 API provider."""

    PRICING = {
        "input": 5.0,
        "output": 15.0,
    }

    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "o1",
        "o1-mini",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.base_url:
            config.base_url = "https://api.openai.com/v1"

    async def chat(self, messages, model=None, max_tokens=None, temperature=None, tools=None, **kwargs):
        model = model or self.config.model or "gpt-4o"
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.config.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        self._call_count += 1
        choice = data["choices"][0]
        msg = choice["message"]
        usage = data.get("usage", {})

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return ChatResponse(
            content=msg.get("content") or "",
            model=data.get("model", model),
            provider="openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=choice.get("finish_reason", "stop"),
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
            raw=data,
        )

    async def stream_chat(self, messages, model=None, max_tokens=None, temperature=None, **kwargs) -> AsyncIterator[str]:
        # Simplified streaming
        result = await self.chat(messages, model, max_tokens, temperature, **kwargs)
        yield result.content
