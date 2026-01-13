from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright

class PlaywrightConnector(ABC):
    name: str

    def fetch(self) -> list[dict]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            jobs = self.scrape(page)
            browser.close()
            return jobs
    
    @abstractmethod
    def scrape(self, page) -> list[dict]:
        pass
