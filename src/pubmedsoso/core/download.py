"""PDF download functionality for PubMed articles."""

import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from pubmedsoso.config import Config
from pubmedsoso.models import Article, FreeStatus


class BaseDownloader(ABC):
    """Abstract base class for PDF downloaders."""

    def __init__(self, config: Config):
        self.config = config
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Pubmedsoso/2.0)"})
        return self._session

    @abstractmethod
    def download(self, article: Article) -> Path | None:
        pass


class PMCDownloader(BaseDownloader):
    """Download PDFs from PubMed Central."""

    def _build_pdf_url(self, article: Article) -> str:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{article.pmcid}/pdf/"

    def _sanitize_filename(self, title: str) -> str:
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "_", title)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "unnamed"
        return sanitized[:200]

    def download(self, article: Article) -> Path | None:
        if not article.pmcid:
            return None

        url = self._build_pdf_url(article)
        session = self._get_session()

        for attempt in range(self.config.max_retries):
            try:
                response = session.get(
                    url, timeout=self.config.download_timeout, allow_redirects=True
                )
                response.raise_for_status()

                if not response.content.startswith(b"%PDF"):
                    return None

                self.config.download_dir.mkdir(parents=True, exist_ok=True)
                filename = self._sanitize_filename(article.title)
                filepath = self.config.download_dir / f"{filename}.pdf"
                filepath.write_bytes(response.content)
                return filepath

            except (requests.Timeout, requests.RequestException):
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_backoff * (2**attempt))
                continue

        return None


class SciHubDownloader(BaseDownloader):
    """Download PDFs via Sci-Hub."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.enabled = config.scihub_enabled

    def _extract_pdf_url(self, html: str) -> str | None:
        iframe_match = re.search(
            r'<iframe[^>]*id=["\']?pdf["\']?[^>]*src=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if iframe_match:
            return iframe_match.group(1)

        embed_match = re.search(
            r'<embed[^>]*src=["\']([^"\']+\.pdf[^"\']*)["\']',
            html,
            re.IGNORECASE,
        )
        if embed_match:
            return embed_match.group(1)

        return None

    def _sanitize_filename(self, title: str) -> str:
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "_", title)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "unnamed"
        return sanitized[:200]

    def download(self, article: Article) -> Path | None:
        if not self.enabled:
            return None

        if not article.doi:
            return None

        session = self._get_session()
        scihub_url = f"{self.config.scihub_base_url}/{article.doi}"

        for attempt in range(self.config.max_retries):
            try:
                response = session.get(
                    scihub_url, timeout=self.config.download_timeout, allow_redirects=True
                )
                response.raise_for_status()

                pdf_url = self._extract_pdf_url(response.text)
                if not pdf_url:
                    return None

                pdf_response = session.get(
                    pdf_url, timeout=self.config.download_timeout, allow_redirects=True
                )
                pdf_response.raise_for_status()

                if not pdf_response.content.startswith(b"%PDF"):
                    return None

                self.config.download_dir.mkdir(parents=True, exist_ok=True)
                filename = self._sanitize_filename(article.title)
                filepath = self.config.download_dir / f"{filename}.pdf"
                filepath.write_bytes(pdf_response.content)
                return filepath

            except (requests.Timeout, requests.RequestException):
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_backoff * (2**attempt))
                continue

        return None


class DownloadManager:
    """Manage PDF downloads from multiple sources."""

    def __init__(self, config: Config):
        self.config = config
        self.pmc_downloader = PMCDownloader(config)
        self.scihub_downloader = SciHubDownloader(config)

    def download(self, article: Article) -> Path | None:
        if article.free_status == FreeStatus.FREE_PMC and article.pmcid:
            result = self.pmc_downloader.download(article)
            if result:
                return result

        if article.doi:
            result = self.scihub_downloader.download(article)
            if result:
                return result

        return None

    def download_batch(self, articles: list[Article], limit: int | None = None) -> list[Path]:
        results: list[Path] = []
        to_download = articles[:limit] if limit else articles

        for article in to_download:
            result = self.download(article)
            if result:
                results.append(result)

        return results
