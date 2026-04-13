"""PubMed search page crawler and parser."""

import logging
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

from pubmedsoso.config import Config
from pubmedsoso.models import Article, FreeStatus, SearchParams, SearchResult

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"


class PubMedSearcher:
    """Searches PubMed and parses search result pages."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )
        self._last_total_count: int = 0

    def _build_search_url(self, keyword: str, page: int = 1, size: int = 50) -> str:
        """Build PubMed search URL with parameters."""
        params = {
            "term": keyword.strip(),
            "size": size,
            "page": page,
        }
        return f"{PUBMED_BASE_URL}?{urllib.parse.urlencode(params)}"

    def _fetch_page(self, url: str) -> bytes | None:
        """Fetch a page with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.request_timeout)
                response.raise_for_status()
                return response.content
            except requests.RequestException as e:
                wait = self.config.retry_backoff * (2**attempt)
                logger.warning(
                    "Fetch attempt %d failed for %s: %s. Retrying in %.1fs",
                    attempt + 1,
                    url,
                    e,
                    wait,
                )
                time.sleep(wait)
        logger.error("All fetch attempts failed for %s", url)
        return None

    def _parse_search_page(self, html: bytes) -> list[Article]:
        """Parse a single PubMed search results page."""
        soup = BeautifulSoup(html, "html.parser")

        value_span = soup.find("span", class_="value")
        if value_span:
            self._last_total_count = int(value_span.get_text(strip=True).replace(",", ""))
        else:
            self._last_total_count = 0

        articles: list[Article] = []
        for docsum in soup.find_all("div", class_="docsum-content"):
            try:
                article = self._parse_docsum(docsum)
                articles.append(article)
            except Exception:
                logger.warning("Failed to parse a docsum entry, skipping", exc_info=True)
                continue

        return articles

    def _parse_docsum(self, docsum) -> Article:
        """Parse a single docsum-content div into an Article."""
        title_tag = docsum.find("a", class_="docsum-title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        pmid_tag = docsum.find("span", class_="citation-part")
        pmid = (
            int(pmid_tag.get_text(strip=True))
            if pmid_tag and pmid_tag.get_text(strip=True).isdigit()
            else None
        )

        free_tag = docsum.find("span", class_="free-resources")
        if free_tag:
            free_text = free_tag.get_text(strip=True)
            if "PMC" in free_text:
                free_status = FreeStatus.FREE_PMC
            else:
                free_status = FreeStatus.FREE_ARTICLE
        else:
            free_status = FreeStatus.NOT_FREE

        review_spans = docsum.find_all("span", class_="citation-part")
        is_review = any("Review" in s.get_text() for s in review_spans)

        authors_tag = docsum.find("span", class_="full-authors")
        authors = authors_tag.get_text(strip=True) if authors_tag else ""

        journal_tag = docsum.find("span", class_="journal-citation")
        journal_text = journal_tag.get_text(strip=True) if journal_tag else ""

        doi = ""
        if "doi:" in journal_text:
            doi_match = re.search(r"(doi:\s*\S+)", journal_text)
            if doi_match:
                doi = doi_match.group(1).rstrip(".")
                journal_text = re.sub(r"\s*doi:\s*\S+", "", journal_text).strip().rstrip(".")

        return Article(
            title=title,
            authors=authors,
            journal=journal_text,
            doi=doi,
            pmid=pmid,
            free_status=free_status,
            is_review=is_review,
        )

    def search(self, params: SearchParams) -> SearchResult:
        """Execute a PubMed search across multiple pages."""
        all_articles: list[Article] = []
        pages_crawled = 0

        for page in range(1, params.page_num + 1):
            url = self._build_search_url(params.keyword, page=page, size=params.page_size)
            logger.info("Fetching search page %d: %s", page, url)

            html = self._fetch_page(url)
            if html is None:
                logger.error("Failed to fetch page %d, stopping search", page)
                break

            articles = self._parse_search_page(html)
            all_articles.extend(articles)
            pages_crawled += 1

            total_pages = (self._last_total_count + params.page_size - 1) // params.page_size
            if page >= total_pages:
                logger.info("Reached last page (%d of %d)", page, total_pages)
                break

            time.sleep(self.config.min_request_interval)

        return SearchResult(
            total_count=self._last_total_count,
            articles=all_articles,
            pages_crawled=pages_crawled,
        )
