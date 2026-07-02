import asyncio
import base64
import json

import httpx

from app.github_client import GitHubClient


def test_fetch_repo_context_collects_required_fields():
    readme_content = "# LangGraph\n\nGraph orchestration."

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/langchain-ai/langgraph":
            return httpx.Response(
                200,
                json={
                    "stargazers_count": 100,
                    "forks_count": 20,
                    "description": "Build resilient language agents.",
                    "default_branch": "main",
                    "updated_at": "2026-07-01T12:00:00Z",
                    "html_url": "https://github.com/langchain-ai/langgraph",
                },
            )
        if path == "/repos/langchain-ai/langgraph/languages":
            return httpx.Response(200, json={"Python": 1234, "TypeScript": 456})
        if path == "/repos/langchain-ai/langgraph/readme":
            encoded = base64.b64encode(readme_content.encode("utf-8")).decode("ascii")
            return httpx.Response(200, json={"content": encoded, "encoding": "base64"})
        if path == "/repos/langchain-ai/langgraph/git/trees/main":
            assert request.url.params["recursive"] == "1"
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "README.md", "type": "blob"},
                        {"path": "src", "type": "tree"},
                        {"path": "src/index.py", "type": "blob"},
                    ]
                },
            )
        return httpx.Response(404, json={"message": "not found"})

    transport = httpx.MockTransport(handler)

    async def run_test():
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://api.github.com",
        ) as http_client:
            client = GitHubClient(http_client=http_client)
            return await client.fetch_repo_context("langchain-ai", "langgraph")

    repo_context = asyncio.run(run_test())

    assert repo_context == {
        "owner": "langchain-ai",
        "repo": "langgraph",
        "repo_url": "https://github.com/langchain-ai/langgraph",
        "stars": 100,
        "forks": 20,
        "description": "Build resilient language agents.",
        "default_branch": "main",
        "updated_at": "2026-07-01T12:00:00Z",
        "languages": {"Python": 1234, "TypeScript": 456},
        "readme": readme_content,
        "file_paths": ["README.md", "src/index.py"],
    }


def test_fetch_repo_context_limits_file_paths_to_300():
    tree = [{"path": f"file_{index}.py", "type": "blob"} for index in range(350)]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/example/project":
            return httpx.Response(
                200,
                json={
                    "stargazers_count": 1,
                    "forks_count": 2,
                    "description": None,
                    "default_branch": "main",
                    "updated_at": "2026-07-01T12:00:00Z",
                    "html_url": "https://github.com/example/project",
                },
            )
        if path == "/repos/example/project/languages":
            return httpx.Response(200, json={})
        if path == "/repos/example/project/readme":
            return httpx.Response(404, json={"message": "not found"})
        if path == "/repos/example/project/git/trees/main":
            return httpx.Response(200, json={"tree": tree})
        return httpx.Response(404, json={"message": "not found"})

    async def run_test():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.com",
        ) as http_client:
            client = GitHubClient(http_client=http_client)
            return await client.fetch_repo_context("example", "project")

    repo_context = asyncio.run(run_test())

    assert len(repo_context["file_paths"]) == 300
    assert repo_context["file_paths"][0] == "file_0.py"
    assert repo_context["file_paths"][-1] == "file_299.py"
