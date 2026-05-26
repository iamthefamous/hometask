from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


class CrawlerService:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def build_listing_urls(pages: int) -> list[str]:
        urls = []
        for page in range(1, pages + 1):
            if page == 1:
                urls.append("https://techcrunch.com/tag/openai/")
            else:
                urls.append(f"https://techcrunch.com/tag/openai/page/{page}/")
        return urls

    async def get_article_urls(self, pages: int) -> list[str]:
        listing_urls = self.build_listing_urls(pages)
        found_urls: set[str] = set()

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            for listing_url in listing_urls:
                resp = await client.get(listing_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for anchor in soup.select("a[href]"):
                    href = anchor.get("href", "")
                    absolute = urljoin(listing_url, href)
                    if (
                        absolute.startswith("https://techcrunch.com/")
                        and "/20" in absolute
                    ):
                        found_urls.add(absolute)

        return sorted(found_urls)
