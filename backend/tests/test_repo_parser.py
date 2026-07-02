import pytest

from app.repo_parser import parse_github_repo_url


def test_parse_standard_github_repo_url():
    owner, repo = parse_github_repo_url("https://github.com/langchain-ai/langgraph")

    assert owner == "langchain-ai"
    assert repo == "langgraph"


def test_parse_repo_url_with_trailing_slash_and_git_suffix():
    owner, repo = parse_github_repo_url("https://github.com/langchain-ai/langgraph.git/")

    assert owner == "langchain-ai"
    assert repo == "langgraph"


def test_rejects_non_github_url():
    with pytest.raises(ValueError, match="GitHub"):
        parse_github_repo_url("https://example.com/langchain-ai/langgraph")
