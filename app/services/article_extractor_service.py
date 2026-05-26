import trafilatura
import httpx
from bs4 import BeautifulSoup

from app.schemas.article import ArticleData
from app.utils.exceptions import ExtractionError
from app.utils.normalization import is_probable_person_name
from app.utils.text import collapse_whitespace


class ArticleExtractorService:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    async def extract(self, url: str) -> ArticleData:
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        title = collapse_whitespace(soup.title.get_text()) if soup.title else ""

        raw_authors = [
            collapse_whitespace(tag.get_text())
            for tag in soup.select('[rel="author"], .author, [class*="author"]')
            if collapse_whitespace(tag.get_text())
        ]
        authors = [
            name for name in dict.fromkeys(raw_authors) if is_probable_person_name(name)
        ]

        published_at = None
        time_node = soup.select_one("time[datetime]")
        if time_node:
            published_at = time_node.get("datetime")

        text = trafilatura.extract(html) or ""
        if not text.strip():
            paragraph_text = " ".join(
                p.get_text(" ", strip=True) for p in soup.select("article p")
            )
            text = collapse_whitespace(paragraph_text)

        if not text:
            raise ExtractionError("Could not extract article text")

        return ArticleData(
            url=url,
            title=title,
            authors=authors,
            published_at=published_at,
            text=text,
        )
