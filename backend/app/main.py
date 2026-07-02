import json
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from app.agents import (
    AgentJSONError,
    run_code_auditor,
    run_final_judge,
    run_product_analyst,
)
from app.github_client import GitHubAPIError, GitHubClient
from app.qwen_client import QwenAPIError
from app.repo_parser import parse_github_repo_url


load_dotenv()

app = FastAPI(title="GitHub Repo Health API")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str


@app.post("/analyze")
async def analyze_repo(request: AnalyzeRequest):
    owner, repo = _parse_or_raise(request.repo_url)
    repo_context = await _fetch_repo_context_or_raise(owner, repo)
    return await _run_agents_or_raise(repo_context)


@app.get("/analyze/stream")
async def analyze_repo_stream(repo_url: str):
    return StreamingResponse(
        _stream_analysis(repo_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_or_raise(repo_url: str) -> tuple[str, str]:
    try:
        return parse_github_repo_url(repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _fetch_repo_context_or_raise(owner: str, repo: str) -> dict[str, Any]:
    try:
        return await GitHubClient().fetch_repo_context(owner, repo)
    except GitHubAPIError as exc:
        status_code = exc.status_code if exc.status_code in {403, 404} else 502
        raise HTTPException(status_code=status_code, detail=exc.message) from exc


async def _run_agents_or_raise(repo_context: dict[str, Any]) -> dict[str, Any]:
    try:
        code_auditor_result = await run_code_auditor(repo_context)
        product_analyst_result = await run_product_analyst(repo_context)
        final_judge_result = await run_final_judge(
            repo_context,
            code_auditor_result,
            product_analyst_result,
        )
    except QwenAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AgentJSONError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "repo_context": repo_context,
        "agents": {
            "code_auditor": code_auditor_result,
            "product_analyst": product_analyst_result,
            "final_judge": final_judge_result,
        },
    }


async def _stream_analysis(repo_url: str) -> AsyncIterator[str]:
    try:
        yield _sse_event("parsing_url", "正在解析 GitHub URL")
        owner, repo = parse_github_repo_url(repo_url)

        yield _sse_event("fetching_github", "正在获取 GitHub 仓库信息")
        repo_context = await GitHubClient().fetch_repo_context(owner, repo)

        yield _sse_event("code_audit", "Agent A 正在分析代码结构")
        code_auditor_result = await run_code_auditor(repo_context)

        yield _sse_event("product_analysis", "Agent B 正在分析 README 和产品价值")
        product_analyst_result = await run_product_analyst(repo_context)

        yield _sse_event("final_judge", "Agent C 正在生成最终评分")
        final_judge_result = await run_final_judge(
            repo_context,
            code_auditor_result,
            product_analyst_result,
        )

        yield _sse_event(
            "done",
            "完成",
            {
                "repo_context": repo_context,
                "agents": {
                    "code_auditor": code_auditor_result,
                    "product_analyst": product_analyst_result,
                    "final_judge": final_judge_result,
                },
            },
        )
    except (ValueError, GitHubAPIError, QwenAPIError, AgentJSONError) as exc:
        message = exc.message if isinstance(exc, GitHubAPIError) else str(exc)
        yield _sse_event("error", message)
    except Exception as exc:
        yield _sse_event("error", str(exc) or "流式分析失败")


def _sse_event(stage: str, message: str, data: Any = None) -> str:
    payload = {
        "stage": stage,
        "message": message,
        "data": data,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
