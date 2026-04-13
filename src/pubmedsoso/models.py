"""Data models for Pubmedsoso."""

from dataclasses import dataclass, field
from enum import IntEnum


class FreeStatus(IntEnum):
    """Free access status for articles."""

    NOT_FREE = 0
    FREE_ARTICLE = 1
    FREE_PMC = 2


@dataclass
class Article:
    """Complete information for a single PubMed article."""

    id: int | None = None
    title: str = ""
    authors: str = ""
    journal: str = ""
    doi: str = ""
    pmid: int | None = None
    pmcid: str = ""
    abstract: str = ""
    keywords: str = ""
    affiliations: str = ""
    free_status: FreeStatus = FreeStatus.NOT_FREE
    is_review: bool = False
    save_path: str = ""


@dataclass
class SearchResult:
    """Summary of a PubMed search operation."""

    total_count: int = 0
    articles: list[Article] = field(default_factory=list)
    pages_crawled: int = 0


@dataclass
class SearchParams:
    """Parameters for a PubMed search."""

    keyword: str = ""
    page_size: int = 50
    page_num: int = 10
    download_limit: int = 10
