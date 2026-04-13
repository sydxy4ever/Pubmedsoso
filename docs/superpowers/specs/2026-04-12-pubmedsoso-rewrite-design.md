# Pubmedsoso Full Rewrite Design

## Overview

Complete rewrite of Pubmedsoso — a PubMed literature crawler that searches, extracts metadata, downloads PDFs, and exports to Excel. The rewrite preserves all existing functionality while fixing code quality issues and adding Web UI + SciHub fallback.

**Architecture**: Monolithic layered (方案 A) — core business logic shared by CLI and Web.

**Target**: Python 3.10+, FastAPI Web UI, typer CLI, openpyxl export, SciHub fallback.

---

## 1. Project Structure

```
pubmedsoso/
├── pyproject.toml              # Project config + dependencies
├── README.md
├── src/
│   └── pubmedsoso/
│       ├── __init__.py
│       ├── main.py             # Unified entry (CLI / Web dispatch)
│       ├── config.py           # Configuration (dataclass, env vars)
│       ├── models.py           # Data models (dataclass, replace bare dict/list)
│       │
│       ├── core/               # Core business logic (pure Python, no framework deps)
│       │   ├── __init__.py
│       │   ├── search.py       # PubMed search + search page parsing
│       │   ├── detail.py       # Article detail page parsing (abstract/keywords/affiliations)
│       │   ├── download.py     # PDF download (PMC + SciHub dual source)
│       │   └── export.py       # Data export (xlsx / csv)
│       │
│       ├── db/                 # Data access layer
│       │   ├── __init__.py
│       │   ├── database.py     # SQLite connection management + schema init
│       │   └── repository.py   # CRUD operations (parameterized queries, no SQL injection)
│       │
│       ├── web/                # FastAPI Web UI
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPI app factory
│       │   ├── routes.py       # API routes
│       │   ├── schemas.py      # Pydantic request/response models
│       │   └── static/         # Frontend static files (HTML+JS, no frontend framework)
│       │       ├── index.html
│       │       ├── style.css
│       │       └── app.js
│       │
│       └── cli/                # CLI entry
│           ├── __init__.py
│           └── commands.py     # typer command definitions
│
└── tests/                      # Tests
    ├── test_search.py
    ├── test_detail.py
    ├── test_download.py
    ├── test_export.py
    └── test_repository.py
```

**Key decisions**:
- `core/` is pure Python, no FastAPI or web framework dependency — shared by CLI and Web
- `models.py` uses dataclass to define `Article` etc., replacing bare list/dict
- Web UI uses plain HTML+JS (no React/Vue), avoiding frontend build toolchain
- `pyproject.toml` replaces `requirements.txt` (modern Python packaging standard)

---

## 2. Data Models

```python
# models.py
from dataclasses import dataclass, field
from enum import IntEnum

class FreeStatus(IntEnum):
    NOT_FREE = 0       # Not free
    FREE_ARTICLE = 1   # Free article (no full text)
    FREE_PMC = 2       # Free PMC (full text PDF available)

@dataclass
class Article:
    """Complete information for a single article"""
    id: int | None = None                    # Auto-increment DB ID
    title: str = ""                          # Article title
    authors: str = ""                        # Author list
    journal: str = ""                        # Journal/year
    doi: str = ""                            # DOI
    pmid: int | None = None                  # PubMed ID
    pmcid: str = ""                          # PMC ID
    abstract: str = ""                       # Abstract
    keywords: str = ""                       # Keywords
    affiliations: str = ""                   # Author affiliations
    free_status: FreeStatus = FreeStatus.NOT_FREE  # Free status
    is_review: bool = False                  # Is review article
    save_path: str = ""                      # PDF save path

@dataclass
class SearchResult:
    """Search result summary"""
    total_count: int = 0                     # Total results on PubMed
    articles: list[Article] = field(default_factory=list)
    pages_crawled: int = 0                   # Pages crawled

@dataclass
class SearchParams:
    """Search parameters"""
    keyword: str = ""
    page_size: int = 50
    page_num: int = 10
    download_limit: int = 10
```

**Improvements over existing**:
- `FreeStatus` enum replaces magic numbers 0/1/2
- `is_review` uses bool instead of string '0'/'1'
- Every field has type annotation and default value
- `SearchResult` encapsulates search summary info

---

## 3. Core Business Logic

### 3.1 Search (`core/search.py`)

```python
class PubMedSearcher:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()  # Connection reuse

    def search(self, params: SearchParams) -> SearchResult:
        """Execute search, return SearchResult"""
        # 1. Build URL (urllib.parse.urlencode)
        # 2. Paginate + parse (BeautifulSoup)
        # 3. Return SearchResult

    def _parse_search_page(self, html: bytes) -> list[Article]:
        """Parse single search results page"""
        # BeautifulSoup + CSS selectors replace regex

    def _fetch_page(self, url: str) -> bytes | None:
        """HTTP GET with retry and error handling"""
        # 3 retries, exponential backoff
```

### 3.2 Detail Fetching (`core/detail.py`)

```python
class DetailFetcher:
    def __init__(self, config: Config):
        self.session = requests.Session()

    def fetch_details(self, articles: list[Article]) -> list[Article]:
        """Batch fetch article details, supplement PMCID/abstract/keywords/affiliations"""
        # Fetch detail page for each article, parse and UPDATE Article

    def _parse_detail_page(self, html: bytes, pmid: int) -> Article:
        """Parse single article detail page"""
        # BeautifulSoup CSS selectors
```

### 3.3 PDF Download (`core/download.py`)

```python
class BaseDownloader(ABC):
    @abstractmethod
    def download(self, article: Article) -> Path | None:
        """Download PDF, return file path or None"""

class PMCDownloader(BaseDownloader):
    """Download free PDFs from PubMed Central"""
    def download(self, article: Article) -> Path | None:
        # https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/pdf/
        # 60s timeout, 3 retries

class SciHubDownloader(BaseDownloader):
    """Fallback: download non-free PDFs from SciHub"""
    def download(self, article: Article) -> Path | None:
        # 1. Search SciHub by DOI
        # 2. Parse PDF link from result page
        # 3. Download PDF

class DownloadManager:
    """Download manager: try PMC first, fall back to SciHub"""
    def __init__(self, config: Config):
        self.pmc = PMCDownloader(config)
        self.scihub = SciHubDownloader(config)

    def download(self, article: Article) -> Path | None:
        if article.free_status == FreeStatus.FREE_PMC:
            result = self.pmc.download(article)
            if result:
                return result
        # SciHub fallback (any article with DOI can be attempted)
        if article.doi:
            return self.scihub.download(article)
        return None
```

### 3.4 Data Export (`core/export.py`)

```python
class Exporter:
    @staticmethod
    def to_xlsx(articles: list[Article], path: Path) -> Path:
        """Export to .xlsx (openpyxl)"""

    @staticmethod
    def to_csv(articles: list[Article], path: Path) -> Path:
        """Export to .csv"""
```

---

## 4. Data Access Layer

### 4.1 Database (`db/database.py`)

```python
class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        # Connection management, context manager support

    def init_schema(self) -> None:
        # Create tables if not exist
```

### 4.2 Repository (`db/repository.py`)

```python
class ArticleRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert_batch(self, articles: list[Article]) -> int:
        """Batch insert, return inserted count"""
        # Parameterized queries, no SQL injection

    def update_detail(self, article: Article) -> None:
        """Update detail info (PMCID/abstract/keywords/affiliations)"""

    def update_save_path(self, pmcid: str, path: str) -> None:
        """Update PDF save path"""

    def get_free_pmc_articles(self) -> list[Article]:
        """Get all free PMC articles"""

    def get_all_articles(self) -> list[Article]:
        """Get all articles"""

    def get_by_pmids(self, pmids: list[int]) -> list[Article]:
        """Query by PMID list"""
```

**Improvements**:
- All SQL uses parameterized queries (`?` placeholders), eliminating SQL injection
- `Database` manages connection lifecycle
- `ArticleRepository` encapsulates all data operations, returns typed `Article` objects

---

## 5. Web UI

### 5.1 API Endpoints

```
GET  /api/search?keyword=xxx&page_num=10&download_num=5
     → Start async search task, return task_id

GET  /api/tasks/{task_id}
     → Query task progress (searching/fetching details/downloading/complete)

GET  /api/articles?task_id=xxx
     → Get article list (paginated)

GET  /api/articles/{pmid}/download
     → Download single PDF

GET  /api/export?task_id=xxx&format=xlsx
     → Export Excel/CSV

GET  /api/history
     → Historical search records
```

### 5.2 Frontend

Plain HTML + Vanilla JS in `web/static/`:
- Search form: keyword + page count + download count
- Progress bar: real-time crawl/download progress
- Results table: article list, sortable/filterable
- Download button: single/batch download
- Export button: Excel/CSV

**Design decisions**:
- Search is long-running → async execution via `asyncio.create_task()` in background thread + progress polling
- No frontend framework → zero build tools, serve directly from `static/`
- FastAPI includes Swagger UI → API docs at zero cost
- Task state stored in-memory dict (single-process, no Redis needed)

---

## 6. CLI

```bash
# Full pipeline: search + extract details + download + export (same as existing behavior)
pubmedsoso search "alzheimer's disease" -n 10 -d 5

# Search + extract only, no PDF download
pubmedsoso search "headache" -n 5 --no-download

# Export historical data
pubmedsoso export --list              # List historical searches
pubmedsoso export --task 20260412     # Export specific search results
pubmedsoso export --format csv        # Export as CSV

# Start Web UI
pubmedsoso web --port 8080

# Version info
pubmedsoso --version
```

Uses `typer` instead of bare `argparse` — auto-generated help docs and shell completion.

---

## 7. Error Handling Strategy

| Scenario | Strategy |
|----------|----------|
| HTTP request failure | 3 retries, exponential backoff (1s, 2s, 4s), log errors |
| Single article parse failure | Skip article, log warning, continue with remaining |
| PDF download timeout | 60s timeout, skip, try next download source |
| SciHub unavailable | Log warning, does not affect PMC downloads |
| Database write failure | Log error, raise exception for upper layer to decide |
| Global | Use Python `logging` module, replace all `print` statements |

**Core principle**: Single article failure does not affect overall flow. All errors are logged and traceable.

---

## 8. Configuration

```python
# config.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    # Paths
    db_dir: Path = Path("./data")
    download_dir: Path = Path("./data/pdfs")
    export_dir: Path = Path("./data/exports")

    # Search
    page_size: int = 50
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0  # seconds, exponential

    # Download
    download_timeout: int = 60
    max_concurrent_downloads: int = 1  # conservative start

    # SciHub
    scihub_base_url: str = "https://sci-hub.se"
    scihub_enabled: bool = True

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # Rate limiting
    min_request_interval: float = 1.0  # seconds between requests
```

Environment variable overrides via `PUBMEDSOSO_` prefix (e.g., `PUBMEDSOSO_SCIHUB_ENABLED=false`).

---

## 9. Dependencies

```toml
[project]
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",          # HTTP (replaces urllib)
    "beautifulsoup4>=4.12",    # HTML parsing
    "openpyxl>=3.1",           # xlsx export (replaces xlwt)
    "typer>=0.9",              # CLI framework (replaces bare argparse)
    "fastapi>=0.104",          # Web framework
    "uvicorn>=0.24",           # ASGI server
    "pydantic>=2.0",           # Data validation (FastAPI dependency)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "httpx",                   # Test FastAPI
    "ruff",                    # Linter + formatter
]
```

**Removed dependencies**:
- `bs4` (meta-package, unnecessary — use `beautifulsoup4` directly)
- `xlwt` (outdated, replaced by `openpyxl`)
- `eventlet` (use `requests` timeout, no monkey patching needed)

---

## 10. Workflow (Preserved from Existing)

The core 3-step workflow is preserved exactly:

```
main.py keyword -n 10 -d 5
        │
        ▼
① PubMedSearcher.search()
   │  Build URL: pubmed.ncbi.nlm.nih.gov/?term=keyword&size=50
   │  Paginate, extract: title, PMID, DOI, journal, authors, free mark, review mark
   │  Create sqlite table, insert articles (txt file output removed — data lives in SQLite)
   ▼
② DetailFetcher.fetch_details()
   │  For each article, fetch detail page by PMID
   │  Extract: PMCID, abstract (supports sections), keywords, affiliations
   │  UPDATE back to sqlite
   ▼
③ DownloadManager.download()
   │  Filter free PMC articles (FreeStatus.FREE_PMC)
   │  Try PMC download first, fall back to SciHub if DOI available
   │  Save to ./data/pdfs/
   │  Export to .xlsx via Exporter
```

---

## 11. Out of Scope

These items are explicitly NOT part of this rewrite:

- GUI desktop application (Tkinter/PyQt) — Web UI is sufficient
- Translation plugin (百度翻译) — can be added later
- PubMed API key authentication — not needed for public search
- Distributed/crawling infrastructure — single-machine tool
- User accounts / multi-user support — single-user tool
