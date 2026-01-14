from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class GreenhouseQuery:
    board_token: str                 # e.g. "stripe"
    content: bool = True             # include job descriptions
    timeout_s: int = 25


class GreenhouseConnector:
    """
    Fetch jobs from the Greenhouse Job Board API (public GET endpoints).

    Docs: https://developers.greenhouse.io/job-board.html  [oai_citation:2‡Greenhouse Developers](https://developers.greenhouse.io/job-board.html?utm_source=chatgpt.com)

    Returns RAW jobs:
      {
        "source": "greenhouse",
        "board_token": "...",
        "id": 123,
        "title": "...",
        "location": "...",
        "absolute_url": "...",
        "content": "...",            # HTML text if content=true
        "departments": [...],
        "offices": [...],
        "raw": {...}                 # original payload
      }
    """

    name = "greenhouse"

    def __init__(self, query: GreenhouseQuery) -> None:
        self.query = query

    def fetch(self) -> List[Dict[str, Any]]:
        base = f"https://boards-api.greenhouse.io/v1/boards/{self.query.board_token}/jobs"
        params = {"content": "true"} if self.query.content else {}

        resp = requests.get(base, params=params, timeout=self.query.timeout_s)
        resp.raise_for_status()

        data = resp.json()
        jobs = data.get("jobs", []) or []

        out: List[Dict[str, Any]] = []
        for j in jobs:
            out.append(
                {
                    "source": "greenhouse",
                    "board_token": self.query.board_token,
                    "id": j.get("id"),
                    "title": j.get("title"),
                    "location": (j.get("location") or {}).get("name", ""),
                    "absolute_url": j.get("absolute_url", ""),
                    "content": j.get("content", "") if self.query.content else "",
                    "departments": j.get("departments", []),
                    "offices": j.get("offices", []),
                    "raw": j,
                }
            )
        return out


def board_token_from_url(job_board_url: str) -> str:
    """
    Convenience helper:
      https://boards.greenhouse.io/stripe -> "stripe"
    """
    p = urlparse(job_board_url)
    token = p.path.strip("/").split("/")[0]
    if not token:
        raise ValueError(f"Could not parse board token from URL: {job_board_url}")
    return token