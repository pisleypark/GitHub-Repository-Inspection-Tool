import json

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


class FakeGitHubClient:
    async def fetch_repo_context(self, owner: str, repo: str):
        return {
            "owner": owner,
            "repo": repo,
            "repo_url": f"https://github.com/{owner}/{repo}",
            "stars": 100,
            "forks": 20,
            "description": "Build resilient language agents.",
            "default_branch": "main",
            "updated_at": "2026-07-01T12:00:00Z",
            "languages": {"Python": 1234},
            "readme": "# LangGraph",
            "file_paths": ["README.md"],
        }


def parse_sse_events(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))
    return events


def test_analyze_stream_emits_progress_and_done(monkeypatch):
    monkeypatch.setattr(main_module, "GitHubClient", FakeGitHubClient)

    async def fake_code_auditor(repo_context):
        return {"score": 82, "strengths": [], "risks": [], "suggestions": []}

    async def fake_product_analyst(repo_context):
        return {
            "score": 78,
            "readme_clarity": "clear",
            "open_source_activity": "active",
            "strengths": [],
            "risks": [],
            "suggestions": [],
        }

    async def fake_final_judge(repo_context, agent_a_result, agent_b_result):
        return {
            "final_score": 80,
            "level": "B",
            "summary": "Solid project.",
            "dimension_scores": {
                "code_quality": 82,
                "product_value": 78,
                "activity": 80,
            },
            "top_issues": [],
            "top_suggestions": ["Improve docs"],
        }

    monkeypatch.setattr(main_module, "run_code_auditor", fake_code_auditor)
    monkeypatch.setattr(main_module, "run_product_analyst", fake_product_analyst)
    monkeypatch.setattr(main_module, "run_final_judge", fake_final_judge)

    response = TestClient(app).get(
        "/analyze/stream",
        params={"repo_url": "https://github.com/langchain-ai/langgraph"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse_events(response.text)
    assert [event["stage"] for event in events] == [
        "parsing_url",
        "fetching_github",
        "code_audit",
        "product_analysis",
        "final_judge",
        "done",
    ]
    assert events[-1]["data"]["repo_context"]["repo"] == "langgraph"
    assert events[-1]["data"]["agents"]["final_judge"]["final_score"] == 80


def test_analyze_stream_emits_error_for_invalid_url():
    response = TestClient(app).get(
        "/analyze/stream",
        params={"repo_url": "https://example.com/langchain-ai/langgraph"},
    )

    events = parse_sse_events(response.text)

    assert response.status_code == 200
    assert events[0]["stage"] == "parsing_url"
    assert events[-1]["stage"] == "error"
    assert "GitHub" in events[-1]["message"]


def test_analyze_stream_converts_unexpected_exception_to_error(monkeypatch):
    class BrokenGitHubClient:
        async def fetch_repo_context(self, owner: str, repo: str):
            raise RuntimeError("network exploded")

    monkeypatch.setattr(main_module, "GitHubClient", BrokenGitHubClient)

    response = TestClient(app).get(
        "/analyze/stream",
        params={"repo_url": "https://github.com/langchain-ai/langgraph"},
    )

    events = parse_sse_events(response.text)

    assert response.status_code == 200
    assert [event["stage"] for event in events] == [
        "parsing_url",
        "fetching_github",
        "error",
    ]
    assert "network exploded" in events[-1]["message"]


def test_analyze_stream_allows_vite_fallback_dev_ports():
    response = TestClient(app).get(
        "/analyze/stream",
        params={"repo_url": "https://example.com/langchain-ai/langgraph"},
        headers={"Origin": "http://127.0.0.1:5174"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
