from urllib.parse import urlparse


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip())
    hostname = (parsed.hostname or "").lower()

    if hostname != "github.com":
        raise ValueError("URL must point to GitHub")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must include owner and repo")

    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("GitHub URL must include owner and repo")

    return owner, repo
