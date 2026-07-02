import json
import re
from typing import Any

from app.qwen_client import call_qwen


class AgentJSONError(Exception):
    pass


async def run_code_auditor(repo_context: dict[str, Any]) -> dict[str, Any]:
    content = await call_qwen(
        [
            {
                "role": "system",
                "content": (
                    "你是代码审计 Agent。只能基于用户提供的 repo_context 分析，"
                    "不得编造未提供的信息。请根据目录结构、语言分布、配置文件、tests、"
                    "CI、src 目录判断代码工程质量。只输出合法 JSON，不要输出 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": _json_payload(
                    {
                        "repo_context": repo_context,
                        "required_output": {
                            "score": "0-100 integer",
                            "strengths": [],
                            "risks": [],
                            "suggestions": [],
                        },
                    }
                ),
            },
        ]
    )
    return _parse_agent_json(content, {"score", "strengths", "risks", "suggestions"})


async def run_product_analyst(repo_context: dict[str, Any]) -> dict[str, Any]:
    content = await call_qwen(
        [
            {
                "role": "system",
                "content": (
                    "你是产品价值 Agent。只能基于用户提供的 repo_context 分析，"
                    "不得编造未提供的信息。请根据 README、stars、forks、更新时间、"
                    "项目描述判断 README 清晰度、实用价值、开源活跃度。只输出合法 JSON，"
                    "不要输出 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": _json_payload(
                    {
                        "repo_context": repo_context,
                        "required_output": {
                            "score": "0-100 integer",
                            "readme_clarity": "",
                            "open_source_activity": "",
                            "strengths": [],
                            "risks": [],
                            "suggestions": [],
                        },
                    }
                ),
            },
        ]
    )
    return _parse_agent_json(
        content,
        {
            "score",
            "readme_clarity",
            "open_source_activity",
            "strengths",
            "risks",
            "suggestions",
        },
    )


async def run_final_judge(
    repo_context: dict[str, Any],
    agent_a_result: dict[str, Any],
    agent_b_result: dict[str, Any],
) -> dict[str, Any]:
    content = await call_qwen(
        [
            {
                "role": "system",
                "content": (
                    "你是总分裁判 Agent。只能基于 repo_context、代码审计结果、"
                    "产品价值结果生成最终体检报告，不得编造未提供的信息。"
                    "只输出合法 JSON，不要输出 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": _json_payload(
                    {
                        "repo_context": repo_context,
                        "code_auditor_result": agent_a_result,
                        "product_analyst_result": agent_b_result,
                        "required_output": {
                            "final_score": "0-100 integer",
                            "level": "A/B/C/D",
                            "summary": "",
                            "dimension_scores": {
                                "code_quality": 0,
                                "product_value": 0,
                                "activity": 0,
                            },
                            "top_issues": [],
                            "top_suggestions": [],
                        },
                    }
                ),
            },
        ]
    )
    return _parse_agent_json(
        content,
        {
            "final_score",
            "level",
            "summary",
            "dimension_scores",
            "top_issues",
            "top_suggestions",
        },
    )


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _parse_agent_json(content: str, required_keys: set[str]) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        repaired = _repair_json_text(content)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise AgentJSONError("Agent did not return valid JSON") from exc

    if not isinstance(parsed, dict):
        raise AgentJSONError("Agent did not return a JSON object")

    missing_keys = sorted(required_keys - set(parsed))
    if missing_keys:
        raise AgentJSONError(
            f"Agent JSON missing required keys: {', '.join(missing_keys)}"
        )

    return parsed


def _repair_json_text(content: str) -> str:
    text = content.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text
