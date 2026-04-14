"""PubMed search via E-UTILS API."""

import logging
import time
from xml.etree import ElementTree as ET

import requests

from pubmedsoso.config import Config
from pubmedsoso.models import Article, FreeStatus, SearchParams, SearchResult

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

BATCH_SIZE = 200


class PubMedSearcher:
    """Searches PubMed via E-UTILS API and parses XML results."""

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

    def _request_with_retry(self, url: str, params: dict) -> bytes | None:
        for attempt in range(self.config.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.config.request_timeout)
                resp.raise_for_status()
                return resp.content
            except requests.RequestException as e:
                wait = self.config.retry_backoff * (2**attempt)
                logger.warning(
                    "Attempt %d failed for %s: %s. Retrying in %.1fs", attempt + 1, url, e, wait
                )
                time.sleep(wait)
        logger.error("All attempts failed for %s", url)
        return None

    def _esearch(self, keyword: str, retmax: int = 0, retstart: int = 0) -> tuple[int, list[str]]:
        """Run esearch. Returns (total_count, list_of_pmids)."""
        params = {
            "db": "pubmed",
            "term": keyword.strip(),
            "retmode": "xml",
        }
        if retmax > 0:
            params["retmax"] = retmax
            params["retstart"] = retstart

        content = self._request_with_retry(ESEARCH_URL, params)
        if content is None:
            return 0, []

        root = ET.fromstring(content)
        count = int(root.findtext("Count", "0"))
        ids = [id_elem.text for id_elem in root.findall(".//Id") if id_elem.text]
        return count, ids

    def _efetch(self, pmids: list[str]) -> list[Article]:
        """Fetch article details by PMID list via efetch."""
        if not pmids:
            return []

        articles: list[Article] = []
        for i in range(0, len(pmids), BATCH_SIZE):
            batch = pmids[i : i + BATCH_SIZE]
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
                "rettype": "abstract",
            }

            content = self._request_with_retry(EFETCH_URL, params)
            if content is None:
                continue

            try:
                root = ET.fromstring(content)
                for article_elem in root.findall(".//PubmedArticle"):
                    try:
                        article = self._parse_article_xml(article_elem)
                        articles.append(article)
                    except Exception:
                        logger.warning("Failed to parse a PubmedArticle, skipping", exc_info=True)
            except ET.ParseError:
                logger.error("Failed to parse efetch XML response")

            time.sleep(self.config.min_request_interval)

        return articles

    def _parse_article_xml(self, article_elem: ET.Element) -> Article:
        """Parse a single PubmedArticle XML element."""
        article = Article()

        # PMID
        pmid_elem = article_elem.find(".//PMID")
        if pmid_elem is not None and pmid_elem.text:
            article.pmid = int(pmid_elem.text)

        # Title
        title_elem = article_elem.find(".//ArticleTitle")
        if title_elem is not None:
            article.title = "".join(title_elem.itertext()).strip()

        # Authors
        authors = []
        for author_elem in article_elem.findall(".//Author"):
            last = author_elem.findtext("LastName", "")
            fore = author_elem.findtext("ForeName", "")
            if last:
                authors.append(f"{fore} {last}".strip() if fore else last)
        article.authors = ", ".join(authors)

        # Journal
        journal_elem = article_elem.find(".//Journal/Title")
        if journal_elem is not None:
            article.journal = journal_elem.text or ""

        # Journal ISO abbreviation
        iso_elem = article_elem.find(".//Journal/ISOAbbreviation")
        if iso_elem is not None and iso_elem.text:
            article.journal = iso_elem.text

        # Publication year
        year_elem = article_elem.find(".//Journal/JournalIssue/PubDate/Year")
        if year_elem is not None and year_elem.text:
            article.pub_year = year_elem.text

        # DOI
        for aid in article_elem.findall(".//ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                article.doi = aid.text
                break

        # Abstract
        abstract_parts = []
        for abs_text in article_elem.findall(".//Abstract/AbstractText"):
            label = abs_text.get("Label", "")
            text = "".join(abs_text.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        article.abstract = "\n".join(abstract_parts)

        # Keywords
        keywords = []
        for kw_elem in article_elem.findall(".//Keyword"):
            if kw_elem.text:
                keywords.append(kw_elem.text.strip())
        article.keywords = "; ".join(keywords)

        # Affiliations
        affs = []
        for aff_elem in article_elem.findall(".//AffiliationInfo/Affiliation"):
            if aff_elem.text:
                affs.append(aff_elem.text.strip())
        article.affiliations = "; ".join(affs)

        # Free status - check for PMCID in ArticleIdList
        for aid in article_elem.findall(".//ArticleId"):
            if aid.get("IdType") == "pmc" and aid.text:
                article.pmcid = aid.text
                article.free_status = FreeStatus.FREE_PMC
                break

        # Check for free article via ELocationID
        if article.free_status != FreeStatus.FREE_PMC:
            for eloc in article_elem.findall(".//ELocationID"):
                if eloc.get("EIdType") == "pmc":
                    article.free_status = FreeStatus.FREE_ARTICLE
                    break

        # Review
        pub_type_elems = article_elem.findall(".//PublicationType")
        for pt in pub_type_elems:
            if pt.text and "Review" in pt.text:
                article.is_review = True
                break

        return article

    def search(self, params: SearchParams) -> SearchResult:
        """Execute a PubMed search, fetching ALL results via E-UTILS API."""
        logger.info("Searching PubMed for: %s", params.keyword)

        # Step 1: Get total count and all PMIDs
        total_count, all_pmids = self._esearch(params.keyword, retmax=0)
        if total_count == 0:
            return SearchResult(total_count=0, articles=[], pages_crawled=0)

        logger.info("Total results: %d, fetching all PMIDs...", total_count)

        # Fetch all PMIDs in batches
        all_pmids_fetched: list[str] = []
        retstart = 0
        while retstart < total_count:
            _, batch_ids = self._esearch(params.keyword, retmax=BATCH_SIZE, retstart=retstart)
            all_pmids_fetched.extend(batch_ids)
            retstart += BATCH_SIZE
            if not batch_ids:
                break
            time.sleep(self.config.min_request_interval)

        logger.info("Got %d PMIDs, fetching article details...", len(all_pmids_fetched))

        # Step 2: Fetch article details
        articles = self._efetch(all_pmids_fetched)

        logger.info("Fetched details for %d articles", len(articles))

        return SearchResult(
            total_count=total_count,
            articles=articles,
            pages_crawled=(total_count + BATCH_SIZE - 1) // BATCH_SIZE,
        )
