"""Ollama local model provider."""

from typing import Optional, AsyncIterator
import httpx
import json

from .base import BaseLLMProvider, ProviderConfig, ChatResponse


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider for offline inference."""

    PRICING = {"input": 0.0, "output": 0.0}

    AVAILABLE_MODELS = [
        "llama3.3:70b",
        "deepseek-r1:32b",
        "qwen2.5-coder:32b",
        "gemma3:27b",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.base_url:
            config.base_url = "http://localhost:11434"

    async def chat(self, messages, model=None, max_tokens=None, temperature=None, tools=None, **kwargs):
        model = model or self.config.model or "llama3.3:70b"
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        url = f"{self.config.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        self._call_count += 1
        msg = data.get("message", {})

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return ChatResponse(
            content=msg.get("content") or "",
            model=data.get("model", model),
            provider="ollama",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason="stop" if data.get("done") else "length",
            cost_usd=0.0,
            raw=data,
        )

    async def stream_chat(self, messages, model=None, max_tokens=None, temperature=None, **kwargs) -> AsyncIterator[str]:
        model = model or self.config.model or "llama3.3:70b"
        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "stream": True,
        }

        url = f"{self.config.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and chunk["message"].get("content"):
                            yield chunk["message"]["content"]
                    except json.JSONDecodeError:
                        continue
