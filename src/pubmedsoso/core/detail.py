"""PubMed article detail page fetcher and parser."""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from pubmedsoso.config import Config
from pubmedsoso.models import Article

logger = logging.getLogger(__name__)

PUBMED_DETAIL_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


class DetailFetcher:
    """Fetches and parses PubMed article detail pages."""

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

    def _fetch_detail(self, pmid: int) -> bytes | None:
        """Fetch article detail page by PMID with retry."""
        url = PUBMED_DETAIL_URL.format(pmid=pmid)
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.request_timeout)
                response.raise_for_status()
                return response.content
            except requests.RequestException as e:
                wait = self.config.retry_backoff * (2**attempt)
                logger.warning(
                    "Fetch attempt %d failed for PMID %d: %s. Retrying in %.1fs",
                    attempt + 1,
                    pmid,
                    e,
                    wait,
                )
                time.sleep(wait)
        logger.error("All fetch attempts failed for PMID %d", pmid)
        return None

    def _parse_abstract(self, block) -> str:
        """Parse abstract block, handling sectioned and plain formats."""
        sections = block.find_all("div", class_="abstract-section")
        if sections:
            parts = []
            for section in sections:
                title_tag = section.find("strong", class_="sub-title")
                content_tag = section.find("p", class_="abstract-content")
                if title_tag and content_tag:
                    title = title_tag.get_text(strip=True)
                    content = content_tag.get_text(strip=True)
                    parts.append(f"{title} {content}")
            return " ".join(parts)

        content = block.find("p", class_="abstract-content")
        if content:
            return content.get_text(strip=True)

        return block.get_text(strip=True)

    def _parse_detail_page(self, html: bytes, article: Article) -> Article:
        """Parse detail page HTML and update article with details."""
        soup = BeautifulSoup(html, "html.parser")

        heading = soup.find("div", class_="heading")
        if heading:
            pmcid_match = re.search(r"(PMC\d+)", heading.get_text())
            if pmcid_match:
                article.pmcid = pmcid_match.group(1)

            affiliations_list = heading.find("ul", class_="affiliations")
            if affiliations_list:
                items = affiliations_list.find_all("li")
                if items:
                    formatted = []
                    for i, item in enumerate(items, 1):
                        formatted.append(f"{i}. {item.get_text(strip=True)}")
                    article.affiliations = " ".join(formatted)

        abstract_div = soup.find("div", class_="abstract-content", id="eng-abstract")
        if abstract_div:
            article.abstract = self._parse_abstract(abstract_div)

        abstract_container = soup.find("div", class_="abstract", id="abstract")
        if abstract_container:
            keywords_p = abstract_container.find("p", class_="keywords")
            if keywords_p:
                keywords_text = keywords_p.get_text(strip=True)
                match = re.search(r"Keywords:\s*(.*)", keywords_text)
                if match:
                    article.keywords = match.group(1).strip()

        return article

    def fetch_details(self, articles: list[Article]) -> None:
        """Batch fetch details for articles, updating them in-place."""
        for article in articles:
            if article.pmid is None:
                logger.warning("Article has no PMID, skipping detail fetch")
                continue

            logger.info("Fetching details for PMID %d", article.pmid)
            html = self._fetch_detail(article.pmid)
            if html:
                self._parse_detail_page(html, article)

            time.sleep(self.config.min_request_interval)
