import asyncio

import pytest

import app.agents as agents_module
from app.agents import (
    AgentJSONError,
    run_code_auditor,
    run_final_judge,
    run_product_analyst,
)


REPO_CONTEXT = {
    "owner": "example",
    "repo": "project",
    "description": "Example project",
    "stars": 120,
    "forks": 12,
    "updated_at": "2026-07-01T00:00:00Z",
    "languages": {"Python": 1000},
    "readme": "# Example\nUseful project.",
    "file_paths": ["README.md", "src/app.py", "tests/test_app.py", ".github/workflows/ci.yml"],
}


def test_run_code_auditor_parses_json(monkeypatch):
    async def fake_call_qwen(messages, temperature=0.2):
        assert "repo_context" in messages[-1]["content"]
        return '{"score": 82, "strengths": ["tests"], "risks": [], "suggestions": []}'

    monkeypatch.setattr(agents_module, "call_qwen", fake_call_qwen)

    result = asyncio.run(run_code_auditor(REPO_CONTEXT))

    assert result == {
        "score": 82,
        "strengths": ["tests"],
        "risks": [],
        "suggestions": [],
    }


def test_run_product_analyst_repairs_markdown_json(monkeypatch):
    async def fake_call_qwen(messages, temperature=0.2):
        return """```json
{"score": 75, "readme_clarity": "clear", "open_source_activity": "active", "strengths": [], "risks": [], "suggestions": []}
```"""

    monkeypatch.setattr(agents_module, "call_qwen", fake_call_qwen)

    result = asyncio.run(run_product_analyst(REPO_CONTEXT))

    assert result["score"] == 75
    assert result["readme_clarity"] == "clear"
    assert result["open_source_activity"] == "active"


def test_run_final_judge_parses_json(monkeypatch):
    async def fake_call_qwen(messages, temperature=0.2):
        assert "code_auditor_result" in messages[-1]["content"]
        assert "product_analyst_result" in messages[-1]["content"]
        return """
        {
          "final_score": 80,
          "level": "B",
          "summary": "Solid project.",
          "dimension_scores": {"code_quality": 82, "product_value": 75, "activity": 80},
          "top_issues": [],
          "top_suggestions": ["Improve docs"]
        }
        """

    monkeypatch.setattr(agents_module, "call_qwen", fake_call_qwen)

    result = asyncio.run(
        run_final_judge(
            REPO_CONTEXT,
            {"score": 82, "strengths": [], "risks": [], "suggestions": []},
            {
                "score": 75,
                "readme_clarity": "clear",
                "open_source_activity": "active",
                "strengths": [],
                "risks": [],
                "suggestions": [],
            },
        )
    )

    assert result["final_score"] == 80
    assert result["level"] == "B"
    assert result["dimension_scores"]["code_quality"] == 82


def test_agent_raises_clear_error_for_invalid_json(monkeypatch):
    async def fake_call_qwen(messages, temperature=0.2):
        return "not json"

    monkeypatch.setattr(agents_module, "call_qwen", fake_call_qwen)

    with pytest.raises(AgentJSONError, match="valid JSON"):
        asyncio.run(run_code_auditor(REPO_CONTEXT))
