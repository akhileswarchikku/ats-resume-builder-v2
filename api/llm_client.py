import json
import httpx
from api import config

_HEADERS = {
    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
    "HTTP-Referer": config.OPENROUTER_HTTP_REFERER,
    "X-Title": config.OPENROUTER_APP_TITLE,
    "Content-Type": "application/json",
}
_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def _record(data: dict) -> None:
    from api import cost_tracker
    usage = data.get("usage", {})
    cost_tracker.record_call(
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


async def chat(messages: list, max_tokens: int = 2048, temperature: float = 0.1) -> str:
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(_BASE_URL, headers=_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
    _record(data)
    return data["choices"][0]["message"]["content"]


async def chat_json(messages: list, max_tokens: int = 2048) -> dict:
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(_BASE_URL, headers=_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
    _record(data)
    raw = data["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)
