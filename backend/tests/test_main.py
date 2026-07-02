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


def test_analyze_returns_repo_context(monkeypatch):
    calls = []

    monkeypatch.setattr(main_module, "GitHubClient", FakeGitHubClient)

    async def fake_code_auditor(repo_context):
        calls.append("code_auditor")
        assert repo_context["repo"] == "langgraph"
        return {"score": 82, "strengths": [], "risks": [], "suggestions": []}

    async def fake_product_analyst(repo_context):
        calls.append("product_analyst")
        assert repo_context["repo"] == "langgraph"
        return {
            "score": 78,
            "readme_clarity": "clear",
            "open_source_activity": "active",
            "strengths": [],
            "risks": [],
            "suggestions": [],
        }

    async def fake_final_judge(repo_context, agent_a_result, agent_b_result):
        calls.append("final_judge")
        assert agent_a_result["score"] == 82
        assert agent_b_result["score"] == 78
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
    client = TestClient(app)

    response = client.post(
        "/analyze",
        json={"repo_url": "https://github.com/langchain-ai/langgraph"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "repo_context": {
            "owner": "langchain-ai",
            "repo": "langgraph",
            "repo_url": "https://github.com/langchain-ai/langgraph",
            "stars": 100,
            "forks": 20,
            "description": "Build resilient language agents.",
            "default_branch": "main",
            "updated_at": "2026-07-01T12:00:00Z",
            "languages": {"Python": 1234},
            "readme": "# LangGraph",
            "file_paths": ["README.md"],
        },
        "agents": {
            "code_auditor": {
                "score": 82,
                "strengths": [],
                "risks": [],
                "suggestions": [],
            },
            "product_analyst": {
                "score": 78,
                "readme_clarity": "clear",
                "open_source_activity": "active",
                "strengths": [],
                "risks": [],
                "suggestions": [],
            },
            "final_judge": {
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
            },
        },
    }
    assert calls == ["code_auditor", "product_analyst", "final_judge"]


def test_analyze_rejects_invalid_github_url():
    client = TestClient(app)

    response = client.post(
        "/analyze",
        json={"repo_url": "https://example.com/langchain-ai/langgraph"},
    )

    assert response.status_code == 400
    assert "GitHub" in response.json()["detail"]
