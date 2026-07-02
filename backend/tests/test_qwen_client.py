import asyncio

import httpx
import pytest

from app.qwen_client import QwenAPIError, call_qwen


def test_call_qwen_posts_openai_compatible_request(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["authorization"] = request.headers["Authorization"]
        captured_request["payload"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"score": 88}'
                        }
                    }
                ]
            },
        )

    async def run_test():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ) as http_client:
            return await call_qwen(
                [{"role": "user", "content": "hello"}],
                temperature=0.3,
                http_client=http_client,
            )

    content = asyncio.run(run_test())

    assert content == '{"score": 88}'
    assert captured_request["url"].endswith("/chat/completions")
    assert captured_request["authorization"] == "Bearer test-key"
    assert '"model":"qwen-plus"' in captured_request["payload"]
    assert '"temperature":0.3' in captured_request["payload"]
    assert '"messages":[{"role":"user","content":"hello"}]' in captured_request["payload"]


def test_call_qwen_requires_dashscope_api_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(QwenAPIError, match="DASHSCOPE_API_KEY"):
        asyncio.run(call_qwen([{"role": "user", "content": "hello"}]))
