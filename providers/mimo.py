"""
Xiaomi MiMo Provider - V2.5 series with reasoning support.

MiMo features:
    - V2.5-Pro: Flagship reasoning model with chain-of-thought
    - V2.5: Multimodal, 1M context window
    - V2-Omni: Multi-modal omni model
    - TTS variants for voice synthesis

The reasoning models output two streams:
    - reasoning_content: internal chain-of-thought
    - content: final answer

CortexFlow surfaces both for full transparency.
"""

import json
import logging
from typing import Optional, AsyncIterator
import httpx

from .base import BaseLLMProvider, ProviderConfig, ChatResponse

logger = logging.getLogger("cortexflow.providers.mimo")


class MiMoProvider(BaseLLMProvider):
    """Xiaomi MiMo V2.5 series provider via OpenAI-compatible API."""

    PRICING = {
        # Approximate pricing per 1M tokens
        "input": 0.14,
        "output": 0.56,
    }

    AVAILABLE_MODELS = [
        "mimo-v2.5-pro",
        "mimo-v2.5",
        "mimo-v2-pro",
        "mimo-v2-omni",
        "mimo-v2-tts",
        "mimo-v2.5-tts",
        "mimo-v2.5-tts-voiceclone",
        "mimo-v2.5-tts-voicedesign",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.base_url:
            config.base_url = "https://token-plan-sgp.xiaomimimo.com/v1"

    async def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list] = None,
        **kwargs
    ) -> ChatResponse:
        model = model or self.config.model or "mimo-v2.5"
        max_tokens = max_tokens or max(self.config.max_tokens, 8000)
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
            **self.config.extra_headers,
        }

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        self._call_count += 1
        choice = data["choices"][0]
        msg = choice["message"]
        usage = data.get("usage", {})
        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return ChatResponse(
            content=msg.get("content") or "",
            reasoning_content=msg.get("reasoning_content"),
            model=data.get("model", model),
            provider="mimo",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=cached,
            finish_reason=choice.get("finish_reason", "stop"),
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
            raw=data,
        )

    async def stream_chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        model = model or self.config.model or "mimo-v2.5"
        max_tokens = max_tokens or max(self.config.max_tokens, 8000)
        temperature = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk_data = line[6:]
                    if chunk_data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
