import json
import os
from typing import Any

import httpx


DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenAPIError(Exception):
    pass


async def call_qwen(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise QwenAPIError("Missing DASHSCOPE_API_KEY environment variable")

    payload = {
        "model": DEFAULT_QWEN_MODEL,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if http_client is not None:
        response = await http_client.post(
            "/chat/completions",
            content=json.dumps(payload, separators=(",", ":")),
            headers=headers,
        )
        return _extract_content(response)

    base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL)
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        response = await client.post(
            "/chat/completions",
            content=json.dumps(payload, separators=(",", ":")),
            headers=headers,
        )
        return _extract_content(response)


def _extract_content(response: httpx.Response) -> str:
    if response.status_code >= 400:
        raise QwenAPIError(_error_message(response))

    try:
        data: dict[str, Any] = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise QwenAPIError("Qwen API response did not contain message content") from exc


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or "Qwen API request failed"

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if data.get("message"):
            return str(data["message"])

    return "Qwen API request failed"
