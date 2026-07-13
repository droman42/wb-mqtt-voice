"""GitHub client for the problem-report sink (ARCH-32, design §5-6).

Talks to the PRIVATE reports repo (design D-1 — `locveil/locveil-reports`): commits the support bundle
via the contents API and opens the ticket via the issues API. Deliberately not an OutputPort —
this is an outbound service client (the BridgeClient precedent), owned by the ReportService.

Auth: a fine-grained PAT scoped to the reports repo ONLY (issues:write + contents:write), read
from the env var named in `[reports] token_env`. Nothing here ever touches the public repos.
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

_API = "https://api.github.com"


class GitHubReportClient:
    """Minimal two-call client: put a file, open an issue."""

    def __init__(self, repo: str, token: str, timeout_seconds: float = 15.0):
        self._repo = repo.strip("/")
        self._token = token
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                })

    async def stop(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # --- transport (one seam; tests stub this) ----------------------------------------------------

    async def _request_json(self, method: str, path: str,
                            body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        if self._session is None or self._session.closed:
            await self.start()
        assert self._session is not None
        async with self._session.request(method, f"{_API}{path}", json=body) as resp:
            return resp.status, await resp.json(content_type=None)

    # --- the two calls -----------------------------------------------------------------------------

    async def put_bundle(self, repo_path: str, data: bytes, message: str) -> str:
        """Commit the bundle file; returns the html_url of the blob. Raises on failure."""
        status, body = await self._request_json(
            "PUT", f"/repos/{self._repo}/contents/{repo_path}",
            {"message": message, "content": base64.b64encode(data).decode("ascii")})
        if status not in (200, 201):
            raise RuntimeError(f"bundle upload failed: HTTP {status} {str(body)[:200]}")
        return (body.get("content") or {}).get("html_url") or repo_path

    async def create_issue(self, title: str, body: str, labels: List[str]) -> str:
        """Open the ticket; returns its html_url. Raises on failure."""
        status, payload = await self._request_json(
            "POST", f"/repos/{self._repo}/issues",
            {"title": title, "body": body, "labels": labels})
        if status != 201:
            raise RuntimeError(f"issue creation failed: HTTP {status} {str(payload)[:200]}")
        return payload.get("html_url") or ""
