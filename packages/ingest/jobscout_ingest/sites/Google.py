from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlencode, urljoin

from jobscout_ingest.connectors.PlaywrightBase import PlaywrightConnector


@dataclass(frozen=True)
class GoogleCareersQuery:
    keyword: str = "software engineer"
    max_results: int = 100
    max_pages: int = 50  # safety to avoid infinite loops


class GoogleCareersConnector(PlaywrightConnector):
    name = "google-careers"
    BASE_URL = "https://www.google.com/about/careers/applications/jobs/results"

    def __init__(self, query: GoogleCareersQuery) -> None:
        self.query = query

    def _build_results_url(self) -> str:
        return f"{self.BASE_URL}?{urlencode({'q': self.query.keyword})}"

    def scrape(self, page) -> List[Dict[str, Any]]:
        page.goto(self._build_results_url(), timeout=60000)

        # For SPAs, networkidle can happen before the list is actually populated.
        # Instead, wait for at least one job link to appear.
        job_link = "a[href*='/about/careers/applications/jobs/results/']"
        page.wait_for_selector(job_link, timeout=60000)

        results: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        def job_anchors():
            # These are the clickable job items; much more stable than "all h3".
            return page.locator(job_link)

        def first_job_url() -> str:
            loc = job_anchors().first
            href = loc.get_attribute("href") if loc.count() else None
            if not href:
                return ""
            return href if href.startswith("http") else urljoin("https://www.google.com", href)

        pages_visited = 0

        while len(results) < self.query.max_results and pages_visited < self.query.max_pages:
            pages_visited += 1

            anchors = job_anchors()
            count = anchors.count()
            if count == 0:
                print("[google-careers] STOP: no job anchors found on page", pages_visited)
                break

            # Parse current page results
            for i in range(count):
                a = anchors.nth(i)
                href = a.get_attribute("href") or ""
                url = href if href.startswith("http") else urljoin("https://www.google.com", href)
                if not url or url in seen_urls:
                    continue

                raw_text = (a.inner_text() or "").strip()
                # Title is usually within the clickable element; fallback to first line
                lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
                title = lines[0] if lines else ""
                location = lines[1] if len(lines) > 1 else ""

                seen_urls.add(url)
                results.append(
                    {
                        "source": "google-careers",
                        "source_url": url,
                        "title": title,
                        "location": location,
                        "raw_text": raw_text,
                    }
                )

                if len(results) >= self.query.max_results:
                    break

            # Attempt to go to next page
            prev_first = first_job_url()

            # The "Next" control is often an icon button with text node navigate_next
            next_button = page.locator(
                "xpath=//button[.//span[normalize-space(text())='navigate_next'] or .//*[normalize-space(text())='navigate_next']]"
            )

            if next_button.count() == 0:
                print("[google-careers] STOP: next button not found (page", pages_visited, ")")
                break

            if not next_button.first.is_enabled():
                print("[google-careers] STOP: next button disabled (page", pages_visited, ")")
                break

            next_button.first.click()

            # Wait for the results list to actually change
            try:
                page.wait_for_function(
                    """(prev) => {
                        const a = document.querySelector("a[href*='/about/careers/applications/jobs/results/']");
                        if (!a) return false;
                        return a.href !== prev;
                    }""",
                    arg=prev_first,
                    timeout=60000,
                )
            except Exception:
                # If it didn't change, we're likely at the last page or blocked by UI state
                now_first = first_job_url()
                print("[google-careers] STOP: results did not change after clicking next",
                      "| prev_first =", prev_first,
                      "| now_first =", now_first)
                break

        print(f"[google-careers] DONE: collected {len(results)} jobs across {pages_visited} pages")
        return results[: self.query.max_results]