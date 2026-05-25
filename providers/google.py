"""Google Gemini provider."""

from typing import Optional, AsyncIterator
import httpx

from .base import BaseLLMProvider, ProviderConfig, ChatResponse


class GoogleProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    PRICING = {
        "input": 1.25,
        "output": 5.0,
    }

    AVAILABLE_MODELS = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.base_url:
            config.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat(self, messages, model=None, max_tokens=None, temperature=None, tools=None, **kwargs):
        model = model or self.config.model or "gemini-2.5-flash"
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        # Convert to Gemini format
        contents = []
        system_instruction = None
        for msg in self._convert_messages(messages):
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}],
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.config.base_url}/models/{model}:generateContent?key={self.config.api_key}"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        self._call_count += 1
        candidate = data.get("candidates", [{}])[0]
        content = ""
        for part in candidate.get("content", {}).get("parts", []):
            content += part.get("text", "")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return ChatResponse(
            content=content,
            model=model,
            provider="google",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=candidate.get("finishReason", "STOP"),
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
            raw=data,
        )

    async def stream_chat(self, messages, model=None, max_tokens=None, temperature=None, **kwargs) -> AsyncIterator[str]:
        result = await self.chat(messages, model, max_tokens, temperature, **kwargs)
        yield result.content
