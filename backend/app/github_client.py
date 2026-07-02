import base64
import os
from typing import Any

import httpx


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.http_client = http_client

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-repo-health-backend",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def fetch_repo_context(self, owner: str, repo: str) -> dict[str, Any]:
        if self.http_client is not None:
            return await self._fetch_repo_context(self.http_client, owner, repo)

        async with httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=20.0,
        ) as http_client:
            return await self._fetch_repo_context(http_client, owner, repo)

    async def _fetch_repo_context(
        self,
        http_client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        repo_data = await self._get_json(http_client, f"/repos/{owner}/{repo}")
        default_branch = repo_data["default_branch"]

        languages = await self._get_json(http_client, f"/repos/{owner}/{repo}/languages")
        readme = await self._fetch_readme(http_client, owner, repo)
        file_paths = await self._fetch_file_paths(
            http_client,
            owner,
            repo,
            default_branch,
        )

        return {
            "owner": owner,
            "repo": repo,
            "repo_url": repo_data.get("html_url", f"https://github.com/{owner}/{repo}"),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "description": repo_data.get("description"),
            "default_branch": default_branch,
            "updated_at": repo_data.get("updated_at"),
            "languages": languages,
            "readme": readme,
            "file_paths": file_paths,
        }

    async def _fetch_readme(
        self,
        http_client: httpx.AsyncClient,
        owner: str,
        repo: str,
    ) -> str:
        response = await http_client.get(
            f"/repos/{owner}/{repo}/readme",
            headers=self.headers,
        )
        if response.status_code == 404:
            return ""

        data = self._json_from_response(response)
        if data.get("encoding") != "base64" or not data.get("content"):
            return ""

        raw = base64.b64decode(data["content"].replace("\n", ""))
        return raw.decode("utf-8", errors="replace")

    async def _fetch_file_paths(
        self,
        http_client: httpx.AsyncClient,
        owner: str,
        repo: str,
        default_branch: str,
    ) -> list[str]:
        data = await self._get_json(
            http_client,
            f"/repos/{owner}/{repo}/git/trees/{default_branch}",
            params={"recursive": "1"},
        )
        tree = data.get("tree", [])
        return [
            item["path"]
            for item in tree
            if item.get("type") == "blob" and item.get("path")
        ][:300]

    async def _get_json(
        self,
        http_client: httpx.AsyncClient,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        response = await http_client.get(path, params=params, headers=self.headers)
        return self._json_from_response(response)

    def _json_from_response(self, response: httpx.Response) -> Any:
        if response.status_code < 400:
            return response.json()

        message = "GitHub API request failed"
        try:
            message = response.json().get("message", message)
        except ValueError:
            if response.text:
                message = response.text

        raise GitHubAPIError(response.status_code, message)
