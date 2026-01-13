from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

from jobscout_ingest.connectors.PlaywrightBase import PlaywrightConnector


@dataclass(frozen=True)
class GoogleCareersQuery:
    """
    Controls what the Google Careers results page shows.

    Examples:
      - keyword="software engineer intern"
      - locations=["United States", "California"]
      - remote_only=True (best-effort; depends on UI filters)
      - max_results=100
    """
    keyword: str = "software engineer intern"
    locations: Optional[List[str]] = None
    max_results: int = 100


class GoogleCareersConnector(PlaywrightConnector):
    """
    Scrapes job search results from Google Careers (careers.google.com).

    Output is RAW postings (not normalized):
      {
        "source": "google-careers",
        "source_url": "...",         # job detail page link
        "title": "...",
        "location": "...",
        "team": "...",               # best-effort
        "employment_type": "...",    # best-effort if present
        "posted_hint": "...",        # if present
        "raw_text": "...",           # listing card text
      }

    This connector intentionally avoids deep parsing of the detail page in MVP.
    You can add a second step later to open each job and extract full description.
    """

    name = "google-careers"

    BASE_URL = "https://careers.google.com/jobs/results/"

    def __init__(self, query: GoogleCareersQuery) -> None:
        self.query = query

    def scrape(self, page) -> List[Dict[str, Any]]:
        url = self._build_results_url(self.query)
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle")

        # Best-effort: accept cookies if a banner appears.
        self._dismiss_cookie_banner(page)

        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        # Google Careers often uses infinite scroll / "load more".
        # We'll scroll until we collect max_results or no new cards appear.
        stagnant_rounds = 0
        last_count = 0

        while len(results) < self.query.max_results and stagnant_rounds < 6:
            cards = page.query_selector_all("a[href*='/jobs/results/']")

            for a in cards:
                href = a.get_attribute("href")
                if not href:
                    continue

                full_url = href if href.startswith("http") else urljoin("https://careers.google.com", href)
                if full_url in seen_urls:
                    continue

                # Try to pull a structured view from the card.
                # Card text usually contains title + location + team lines.
                raw_text = a.inner_text().strip()
                title = self._guess_title(raw_text)
                location = self._guess_location(raw_text)
                team = self._guess_team(raw_text)

                seen_urls.add(full_url)
                results.append(
                    {
                        "source": "google-careers",
                        "source_url": full_url,
                        "title": title,
                        "location": location,
                        "team": team,
                        "raw_text": raw_text,
                    }
                )

                if len(results) >= self.query.max_results:
                    break

            # progress detection
            if len(results) == last_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
                last_count = len(results)

            # Scroll to trigger lazy loading
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(800)

        return results[: self.query.max_results]

    def _build_results_url(self, q: GoogleCareersQuery) -> str:
        # Google Careers has a UI-driven filter system; query params aren’t always stable.
        # The most stable approach for MVP is to use the keyword search box via URL "q".
        params = {"q": q.keyword}

        # Locations: best-effort. If Google changes URL param behavior, you can remove this
        # and instead apply filters via UI clicks (more work, more stable once coded).
        if q.locations:
            # This may or may not be respected; still useful as a hint.
            params["location"] = ", ".join(q.locations)

        return f"{self.BASE_URL}?{urlencode(params)}"

    def _dismiss_cookie_banner(self, page) -> None:
        # Best-effort. If not present, does nothing.
        # We avoid “anti-bot” tricks; just a normal click if visible.
        for label in ["Accept all", "I agree", "Accept"]:
            btn = page.get_by_role("button", name=label)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)
                break

    def _guess_title(self, raw_text: str) -> str:
        # Usually first line is the title.
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
        return lines[0] if lines else ""

    def _guess_location(self, raw_text: str) -> str:
        # Location often appears in the card text; heuristic.
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
        # Common pattern: Title / Location / Team
        if len(lines) >= 2:
            return lines[1]
        return ""

    def _guess_team(self, raw_text: str) -> str:
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
        # Common pattern: Title / Location / Team
        if len(lines) >= 3:
            return lines[2]
        return ""