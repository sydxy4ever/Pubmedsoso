# Pubmedsoso Full Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely rewrite Pubmedsoso — a PubMed literature crawler with CLI + Web UI, preserving existing search→detail→download→export workflow while adding SciHub fallback, proper error handling, and modern Python practices.

**Architecture:** Monolithic layered — `core/` (pure Python business logic) shared by `cli/` (typer) and `web/` (FastAPI). Data layer via `db/` (SQLite + repository pattern). All SQL parameterized, all errors logged, no bare excepts.

**Tech Stack:** Python 3.10+, requests, BeautifulSoup4, openpyxl, typer, FastAPI, uvicorn, pydantic, sqlite3

---

## File Structure

```
pubmedsoso/
├── pyproject.toml
├── README.md
├── src/
│   └── pubmedsoso/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── search.py
│       │   ├── detail.py
│       │   ├── download.py
│       │   └── export.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── repository.py
│       ├── web/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── routes.py
│       │   ├── schemas.py
│       │   └── static/
│       │       ├── index.html
│       │       ├── style.css
│       │       └── app.js
│       └── cli/
│           ├── __init__.py
│           └── commands.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_search.py
    ├── test_detail.py
    ├── test_download.py
    ├── test_export.py
    ├── test_database.py
    ├── test_repository.py
    └── fixtures/
        ├── search_page.html
        └── detail_page.html
```

---

## Task 1: Project Scaffold + pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `src/pubmedsoso/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Delete: `requirements.txt` (replaced by pyproject.toml)
- Delete: `ArgParser.py` (dead code)
- Delete: `timevar.py` (replaced by config.py)
- Delete: `main.py` (old entry, replaced by src/pubmedsoso/main.py)
- Delete: `spiderpub.py` (replaced by core/search.py)
- Delete: `geteachinfo.py` (replaced by core/detail.py)
- Delete: `downpmc.py` (replaced by core/download.py)
- Delete: `save2excel.py` (replaced by core/export.py)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/pubmedsoso/core
mkdir -p src/pubmedsoso/db
mkdir -p src/pubmedsoso/web/static
mkdir -p src/pubmedsoso/cli
mkdir -p tests/fixtures
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "pubmedsoso"
version = "2.0.0"
description = "PubMed literature crawler - search, extract, download, export"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "openpyxl>=3.1",
    "typer>=0.9",
    "fastapi>=0.104",
    "uvicorn>=0.24",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "httpx",
    "ruff",
]

[project.scripts]
pubmedsoso = "pubmedsoso.main:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Write src/pubmedsoso/__init__.py**

```python
"""Pubmedsoso - PubMed literature crawler."""

__version__ = "2.0.0"
```

- [ ] **Step 4: Write tests/__init__.py and tests/conftest.py**

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return tmp_path / "test.db"
```

- [ ] **Step 5: Create empty __init__.py files for all packages**

```bash
touch src/pubmedsoso/core/__init__.py
touch src/pubmedsoso/db/__init__.py
touch src/pubmedsoso/web/__init__.py
touch src/pubmedsoso/cli/__init__.py
```

- [ ] **Step 6: Delete old source files**

```bash
rm requirements.txt ArgParser.py timevar.py main.py spiderpub.py geteachinfo.py downpmc.py save2excel.py
```

- [ ] **Step 7: Install project in editable mode and verify**

```bash
pip install -e ".[dev]"
python -c "import pubmedsoso; print(pubmedsoso.__version__)"
```

Expected: `2.0.0`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: scaffold new project structure with pyproject.toml, remove legacy files"
```

---

## Task 2: Data Models (models.py)

**Files:**
- Create: `src/pubmedsoso/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test for models**

```python
# tests/test_models.py
from pubmedsoso.models import Article, FreeStatus, SearchParams, SearchResult


def test_free_status_enum_values():
    assert FreeStatus.NOT_FREE == 0
    assert FreeStatus.FREE_ARTICLE == 1
    assert FreeStatus.FREE_PMC == 2


def test_article_default_values():
    article = Article()
    assert article.id is None
    assert article.title == ""
    assert article.pmid is None
    assert article.free_status == FreeStatus.NOT_FREE
    assert article.is_review is False


def test_article_with_values():
    article = Article(
        title="Test Article",
        pmid=12345678,
        free_status=FreeStatus.FREE_PMC,
        is_review=True,
    )
    assert article.title == "Test Article"
    assert article.pmid == 12345678
    assert article.free_status == FreeStatus.FREE_PMC
    assert article.is_review is True


def test_search_params_defaults():
    params = SearchParams(keyword="cancer")
    assert params.keyword == "cancer"
    assert params.page_size == 50
    assert params.page_num == 10
    assert params.download_limit == 10


def test_search_result_defaults():
    result = SearchResult()
    assert result.total_count == 0
    assert result.articles == []
    assert result.pages_crawled == 0


def test_search_result_with_articles():
    articles = [Article(title="A1"), Article(title="A2")]
    result = SearchResult(total_count=100, articles=articles, pages_crawled=2)
    assert len(result.articles) == 2
    assert result.total_count == 100
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pubmedsoso.models'`

- [ ] **Step 3: Write models.py**

```python
# src/pubmedsoso/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pubmedsoso/models.py tests/test_models.py
git commit -m "feat: add data models (Article, FreeStatus, SearchParams, SearchResult)"
```

---

## Task 3: Configuration (config.py)

**Files:**
- Create: `src/pubmedsoso/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test for config**

```python
# tests/test_config.py
import os
from pathlib import Path
from pubmedsoso.config import Config


def test_config_defaults():
    config = Config()
    assert config.page_size == 50
    assert config.request_timeout == 30
    assert config.max_retries == 3
    assert config.download_timeout == 60
    assert config.scihub_enabled is True
    assert config.web_port == 8000
    assert config.min_request_interval == 1.0


def test_config_custom_values():
    config = Config(
        page_size=20,
        download_timeout=120,
        scihub_enabled=False,
    )
    assert config.page_size == 20
    assert config.download_timeout == 120
    assert config.scihub_enabled is False


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("PUBMEDSOSO_SCIHUB_ENABLED", "false")
    monkeypatch.setenv("PUBMEDSOSO_WEB_PORT", "9000")
    config = Config.from_env()
    assert config.scihub_enabled is False
    assert config.web_port == 9000


def test_config_paths_are_path_objects():
    config = Config()
    assert isinstance(config.db_dir, Path)
    assert isinstance(config.download_dir, Path)
    assert isinstance(config.export_dir, Path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write config.py**

```python
# src/pubmedsoso/config.py
"""Configuration management for Pubmedsoso."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration with sensible defaults."""

    # Paths
    db_dir: Path = Path("./data")
    download_dir: Path = Path("./data/pdfs")
    export_dir: Path = Path("./data/exports")

    # Search
    page_size: int = 50
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0

    # Download
    download_timeout: int = 60
    max_concurrent_downloads: int = 1

    # SciHub
    scihub_base_url: str = "https://sci-hub.se"
    scihub_enabled: bool = True

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # Rate limiting
    min_request_interval: float = 1.0

    @classmethod
    def from_env(cls) -> "Config":
        """Create config with environment variable overrides.

        Environment variables use PUBMEDSOSO_ prefix.
        Example: PUBMEDSOSO_SCIHUB_ENABLED=false
        """
        config = cls()
        prefix = "PUBMEDSOSO_"

        env_map: dict[str, type] = {
            "PAGE_SIZE": int,
            "REQUEST_TIMEOUT": int,
            "MAX_RETRIES": int,
            "RETRY_BACKOFF": float,
            "DOWNLOAD_TIMEOUT": int,
            "MAX_CONCURRENT_DOWNLOADS": int,
            "SCIHUB_BASE_URL": str,
            "SCIHUB_ENABLED": lambda v: v.lower() in ("true", "1", "yes"),
            "WEB_HOST": str,
            "WEB_PORT": int,
            "MIN_REQUEST_INTERVAL": float,
        }

        for key, cast in env_map.items():
            env_val = os.environ.get(f"{prefix}{key}")
            if env_val is not None:
                setattr(config, key.lower(), cast(env_val))

        # Handle path env vars separately
        for key in ("DB_DIR", "DOWNLOAD_DIR", "EXPORT_DIR"):
            env_val = os.environ.get(f"{prefix}{key}")
            if env_val is not None:
                setattr(config, key.lower(), Path(env_val))

        return config

    def ensure_dirs(self) -> None:
        """Create all configured directories if they don't exist."""
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pubmedsoso/config.py tests/test_config.py
git commit -m "feat: add Config dataclass with env var overrides"
```

---

## Task 4: Database Layer (db/)

**Files:**
- Create: `src/pubmedsoso/db/database.py`
- Create: `src/pubmedsoso/db/repository.py`
- Create: `tests/test_database.py`
- Create: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests for database**

```python
# tests/test_database.py
from pathlib import Path
from pubmedsoso.db.database import Database


def test_database_creates_file(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    assert tmp_db.exists()


def test_database_init_schema_idempotent(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    db.init_schema()  # Should not raise


def test_database_get_connection(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    conn = db.get_connection()
    assert conn is not None
    conn.close()
```

```python
# tests/test_repository.py
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import Article, FreeStatus


def _make_repo(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    return ArticleRepository(db)


def test_insert_batch(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [
        Article(title="Article 1", pmid=111, free_status=FreeStatus.FREE_PMC),
        Article(title="Article 2", pmid=222, free_status=FreeStatus.NOT_FREE),
    ]
    count = repo.insert_batch(articles)
    assert count == 2


def test_get_all_articles(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [
        Article(title="A1", pmid=111),
        Article(title="A2", pmid=222),
    ]
    repo.insert_batch(articles)
    result = repo.get_all_articles()
    assert len(result) == 2
    assert result[0].title == "A1"
    assert result[1].pmid == 222


def test_get_free_pmc_articles(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [
        Article(title="Free", pmid=111, free_status=FreeStatus.FREE_PMC),
        Article(title="Not Free", pmid=222, free_status=FreeStatus.NOT_FREE),
        Article(title="Free Article", pmid=333, free_status=FreeStatus.FREE_ARTICLE),
    ]
    repo.insert_batch(articles)
    result = repo.get_free_pmc_articles()
    assert len(result) == 1
    assert result[0].title == "Free"


def test_update_detail(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [Article(title="Test", pmid=111)]
    repo.insert_batch(articles)
    article = repo.get_all_articles()[0]
    article.pmcid = "PMC12345"
    article.abstract = "Test abstract"
    article.keywords = "cancer, therapy"
    article.affiliations = "1. MIT"
    repo.update_detail(article)
    result = repo.get_all_articles()[0]
    assert result.pmcid == "PMC12345"
    assert result.abstract == "Test abstract"


def test_update_save_path(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [Article(title="Test", pmid=111, pmcid="PMC123")]
    repo.insert_batch(articles)
    repo.update_save_path("PMC123", "/data/pdfs/test.pdf")
    result = repo.get_all_articles()[0]
    assert result.save_path == "/data/pdfs/test.pdf"


def test_get_by_pmids(tmp_db):
    repo = _make_repo(tmp_db)
    articles = [
        Article(title="A1", pmid=111),
        Article(title="A2", pmid=222),
        Article(title="A3", pmid=333),
    ]
    repo.insert_batch(articles)
    result = repo.get_by_pmids([111, 333])
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_database.py tests/test_repository.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write database.py**

```python
# src/pubmedsoso/db/database.py
"""SQLite database connection management."""

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    authors TEXT NOT NULL DEFAULT '',
    journal TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '',
    pmid INTEGER,
    pmcid TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    affiliations TEXT NOT NULL DEFAULT '',
    free_status INTEGER NOT NULL DEFAULT 0,
    is_review INTEGER NOT NULL DEFAULT 0,
    save_path TEXT NOT NULL DEFAULT ''
);
"""


class Database:
    """Manages SQLite database connections and schema."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Get a new database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Initialize database schema. Idempotent."""
        conn = self.get_connection()
        try:
            conn.execute(_SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()
```

- [ ] **Step 4: Write repository.py**

```python
# src/pubmedsoso/db/repository.py
"""Article repository — CRUD operations for articles in SQLite."""

import logging
from pubmedsoso.db.database import Database
from pubmedsoso.models import Article, FreeStatus

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Data access for Article objects in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def _row_to_article(self, row: sqlite3.Row) -> Article:  # type: ignore[name-defined]
        return Article(
            id=row["id"],
            title=row["title"],
            authors=row["authors"],
            journal=row["journal"],
            doi=row["doi"],
            pmid=row["pmid"],
            pmcid=row["pmcid"],
            abstract=row["abstract"],
            keywords=row["keywords"],
            affiliations=row["affiliations"],
            free_status=FreeStatus(row["free_status"]),
            is_review=bool(row["is_review"]),
            save_path=row["save_path"],
        )

    def insert_batch(self, articles: list[Article]) -> int:
        """Insert multiple articles. Returns count of inserted rows."""
        conn = self.db.get_connection()
        try:
            count = 0
            for article in articles:
                conn.execute(
                    """INSERT INTO articles
                       (title, authors, journal, doi, pmid, pmcid, abstract,
                        keywords, affiliations, free_status, is_review, save_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        article.title,
                        article.authors,
                        article.journal,
                        article.doi,
                        article.pmid,
                        article.pmcid,
                        article.abstract,
                        article.keywords,
                        article.affiliations,
                        int(article.free_status),
                        int(article.is_review),
                        article.save_path,
                    ),
                )
                count += 1
            conn.commit()
            return count
        except Exception:
            conn.rollback()
            logger.exception("Failed to insert batch of articles")
            raise
        finally:
            conn.close()

    def update_detail(self, article: Article) -> None:
        """Update detail fields (PMCID, abstract, keywords, affiliations) by PMID."""
        conn = self.db.get_connection()
        try:
            conn.execute(
                """UPDATE articles
                   SET pmcid = ?, abstract = ?, keywords = ?, affiliations = ?
                   WHERE pmid = ?""",
                (article.pmcid, article.abstract, article.keywords, article.affiliations, article.pmid),
            )
            conn.commit()
        finally:
            conn.close()

    def update_save_path(self, pmcid: str, path: str) -> None:
        """Update PDF save path by PMCID."""
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE articles SET save_path = ? WHERE pmcid = ?",
                (path, pmcid),
            )
            conn.commit()
        finally:
            conn.close()

    def get_free_pmc_articles(self) -> list[Article]:
        """Get all articles with free_status = FREE_PMC."""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM articles WHERE free_status = ?",
                (int(FreeStatus.FREE_PMC),),
            )
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_articles(self) -> list[Article]:
        """Get all articles."""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM articles ORDER BY id")
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_by_pmids(self, pmids: list[int]) -> list[Article]:
        """Get articles by PMID list."""
        if not pmids:
            return []
        placeholders = ",".join("?" for _ in pmids)
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                f"SELECT * FROM articles WHERE pmid IN ({placeholders})",
                pmids,
            )
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_database.py tests/test_repository.py -v
```

Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/pubmedsoso/db/ tests/test_database.py tests/test_repository.py
git commit -m "feat: add Database and ArticleRepository with parameterized queries"
```

---

## Task 5: Search Parser (core/search.py)

**Files:**
- Create: `src/pubmedsoso/core/search.py`
- Create: `tests/test_search.py`
- Create: `tests/fixtures/search_page.html`

- [ ] **Step 1: Create test fixture HTML**

Save a minimal but realistic PubMed search results page HTML to `tests/fixtures/search_page.html`. This should contain 2-3 article entries with the key CSS classes: `docsum-content`, `docsum-title`, `citation-part`, `free-resources`, `full-authors`, `journal-citation`.

```html
<!-- tests/fixtures/search_page.html -->
<!DOCTYPE html>
<html>
<body>
<div class="results-amount">
    <span class="value">1,234</span>
</div>

<div class="docsum-wrap">
<div class="docsum-content">
    <a class="docsum-title" href="/12345678/">
        <b>Alzheimer</b>'s disease and <em>neuroinflammation</em>
    </a>
    <span class="citation-part">12345678</span>
    <span class="free-resources free-article-links">Free PMC article.</span>
    <span class="full-authors">Smith J, Wang L, Chen Y.</span>
    <span class="journal-citation">Neurosci Lett. 2024;789:123-130. doi: 10.1234/test.2024.123.</span>
</div>
</div>

<div class="docsum-wrap">
<div class="docsum-content">
    <a class="docsum-title" href="/23456789/">
        Novel therapeutic approaches for headache
    </a>
    <span class="citation-part">23456789</span>
    <span class="citation-part">Review.</span>
    <span class="full-authors">Brown A, Lee K.</span>
    <span class="journal-citation">Pain Med. 2024;25(3):456-467. doi: 10.5678/test.2024.456.</span>
</div>
</div>

<div class="docsum-wrap">
<div class="docsum-content">
    <a class="docsum-title" href="/34567890/">
        Cancer therapy resistance mechanisms
    </a>
    <span class="citation-part">34567890</span>
    <span class="free-resources free-article-links">Free article.</span>
    <span class="full-authors">Davis R.</span>
    <span class="journal-citation">Oncogene. 2024;43:789-795.</span>
</div>
</div>
</body>
</html>
```

- [ ] **Step 2: Write failing tests for search**

```python
# tests/test_search.py
from pathlib import Path
from unittest.mock import patch, MagicMock

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.models import FreeStatus, SearchParams


def test_parse_search_page(fixtures_dir):
    searcher = PubMedSearcher(Config())
    html = (fixtures_dir / "search_page.html").read_bytes()
    articles = searcher._parse_search_page(html)

    assert len(articles) == 3

    # First article: free PMC
    assert articles[0].title == "Alzheimer's disease and neuroinflammation"
    assert articles[0].pmid == 12345678
    assert articles[0].free_status == FreeStatus.FREE_PMC
    assert articles[0].authors == "Smith J, Wang L, Chen Y."
    assert articles[0].doi == "doi: 10.1234/test.2024.123."
    assert articles[0].is_review is False

    # Second article: review, not free
    assert articles[1].title == "Novel therapeutic approaches for headache"
    assert articles[1].pmid == 23456789
    assert articles[1].free_status == FreeStatus.NOT_FREE
    assert articles[1].is_review is True

    # Third article: free article (no full text)
    assert articles[2].title == "Cancer therapy resistance mechanisms"
    assert articles[2].pmid == 34567890
    assert articles[2].free_status == FreeStatus.FREE_ARTICLE


def test_parse_search_page_extracts_total_count(fixtures_dir):
    searcher = PubMedSearcher(Config())
    html = (fixtures_dir / "search_page.html").read_bytes()
    articles = searcher._parse_search_page(html)
    assert searcher._last_total_count == 1234


def test_build_search_url():
    searcher = PubMedSearcher(Config())
    url = searcher._build_search_url("alzheimer", page=1, size=50)
    assert "term=alzheimer" in url
    assert "size=50" in url
    assert "page=1" in url


@patch("pubmedsoso.core.search.requests.Session")
def test_search_pagination(mock_session_cls):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Return minimal HTML for 2 pages
    minimal_html = b'<div class="results-amount"><span class="value">60</span></div><div class="docsum-content"><a class="docsum-title" href="/111/"><b>Test</b></a><span class="citation-part">111</span><span class="full-authors">Author A</span><span class="journal-citation">J Med. 2024. doi: 10.1/x.</span></div>'

    mock_response = MagicMock()
    mock_response.content = minimal_html
    mock_session.get.return_value = mock_response

    searcher = PubMedSearcher(Config())
    result = searcher.search(SearchParams(keyword="test", page_num=2))

    assert result.pages_crawled == 2
    assert mock_session.get.call_count == 2
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_search.py -v
```

Expected: FAIL

- [ ] **Step 4: Write core/search.py**

```python
# src/pubmedsoso/core/search.py
"""PubMed search page crawler and parser."""

import logging
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
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
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
                wait = self.config.retry_backoff * (2 ** attempt)
                logger.warning("Fetch attempt %d failed for %s: %s. Retrying in %.1fs", attempt + 1, url, e, wait)
                time.sleep(wait)
        logger.error("All fetch attempts failed for %s", url)
        return None

    def _parse_search_page(self, html: bytes) -> list[Article]:
        """Parse a single PubMed search results page."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract total count
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

    def _parse_docsum(self, docsum) -> Article:  # type: ignore[ann-arg]
        """Parse a single docsum-content div into an Article."""
        text = str(docsum)

        # Title
        title_tag = docsum.find("a", class_="docsum-title")
        title = title_tag.get_text(separator=" ", strip=True) if title_tag else ""
        # Clean up HTML tags that may remain in title text
        import re
        title = re.sub(r"<[^>]+>", "", str(title_tag.decode_contents() if title_tag else "")).strip() if title_tag else ""
        # Fallback: just use stripped text
        if not title and title_tag:
            title = title_tag.get_text(strip=True)

        # PMID
        pmid_tag = docsum.find("span", class_="citation-part")
        pmid = int(pmid_tag.get_text(strip=True)) if pmid_tag and pmid_tag.get_text(strip=True).isdigit() else None

        # Free status
        free_tag = docsum.find("span", class_="free-resources")
        if free_tag:
            free_text = free_tag.get_text(strip=True)
            if "PMC" in free_text:
                free_status = FreeStatus.FREE_PMC
            else:
                free_status = FreeStatus.FREE_ARTICLE
        else:
            free_status = FreeStatus.NOT_FREE

        # Review
        review_spans = docsum.find_all("span", class_="citation-part")
        is_review = any("Review" in s.get_text() for s in review_spans)

        # Authors
        authors_tag = docsum.find("span", class_="full-authors")
        authors = authors_tag.get_text(strip=True) if authors_tag else ""

        # Journal + DOI
        journal_tag = docsum.find("span", class_="journal-citation")
        journal_text = journal_tag.get_text(strip=True) if journal_tag else ""

        # Extract DOI from journal citation
        doi = ""
        if "doi:" in journal_text:
            doi_match = re.search(r"(doi:\s*\S+)", journal_text)
            if doi_match:
                doi = doi_match.group(1).rstrip(".")
                # Remove DOI from journal string
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

            # Check if we've exhausted all pages
            total_pages = (self._last_total_count + params.page_size - 1) // params.page_size
            if page >= total_pages:
                logger.info("Reached last page (%d of %d)", page, total_pages)
                break

            # Rate limiting
            time.sleep(self.config.min_request_interval)

        return SearchResult(
            total_count=self._last_total_count,
            articles=all_articles,
            pages_crawled=pages_crawled,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_search.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/pubmedsoso/core/search.py tests/test_search.py tests/fixtures/search_page.html
git commit -m "feat: add PubMedSearcher with HTML parsing and pagination"
```

---

## Task 6: Detail Fetcher (core/detail.py)

**Files:**
- Create: `src/pubmedsoso/core/detail.py`
- Create: `tests/test_detail.py`
- Create: `tests/fixtures/detail_page.html`

- [ ] **Step 1: Create detail page fixture HTML**

```html
<!-- tests/fixtures/detail_page.html -->
<!DOCTYPE html>
<html>
<body>
<div class="full-view" id="full-view-heading">
    <span class="citation-part">PMC9876543
    </span>
    <ol class="affiliations-list">
        <li><sup class="key">1</sup> Department of Neurology, Harvard Medical School.</li>
        <li><sup class="key">2</sup> MIT CSAIL.</li>
    </ol>
</div>

<div class="abstract-content selected" id="eng-abstract">
    <div class="abstract-content">
        <p><strong>BACKGROUND:</strong> Neuroinflammation plays a key role in Alzheimer's disease.</p>
        <p><strong>METHODS:</strong> We conducted a systematic review of 50 studies.</p>
        <p><strong>RESULTS:</strong> Anti-inflammatory agents showed moderate benefit.</p>
        <p><strong>CONCLUSION:</strong> Targeting neuroinflammation is promising for AD therapy.</p>
    </div>
</div>

<div class="abstract" id="abstract">
    <p><strong>Keywords:</strong> Alzheimer; neuroinflammation; therapy</p>
</div>
</body>
</html>
```

- [ ] **Step 2: Write failing tests for detail**

```python
# tests/test_detail.py
from pubmedsoso.config import Config
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.models import Article


def test_parse_detail_page(fixtures_dir):
    fetcher = DetailFetcher(Config())
    html = (fixtures_dir / "detail_page.html").read_bytes()
    article = fetcher._parse_detail_page(html, pmid=12345678)

    assert article.pmcid == "PMC9876543"
    assert "BACKGROUND:" in article.abstract
    assert "CONCLUSION:" in article.abstract
    assert "Alzheimer" in article.keywords
    assert "Harvard Medical School" in article.affiliations
    assert article.pmid == 12345678


def test_parse_detail_page_no_pmcid(fixtures_dir):
    """Detail page without PMCID should return empty string."""
    fetcher = DetailFetcher(Config())
    html = b'<html><body><div class="full-view" id="full-view-heading"></div><div class="abstract-content selected" id="eng-abstract"><div class="abstract-content"><p>Simple abstract text.</p></div></div></body></html>'
    article = fetcher._parse_detail_page(html, pmid=99999)
    assert article.pmcid == ""
    assert "Simple abstract" in article.abstract
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_detail.py -v
```

Expected: FAIL

- [ ] **Step 4: Write core/detail.py**

```python
# src/pubmedsoso/core/detail.py
"""PubMed article detail page parser."""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from pubmedsoso.config import Config
from pubmedsoso.models import Article

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"


class DetailFetcher:
    """Fetches and parses individual PubMed article detail pages."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

    def _fetch_detail(self, pmid: int) -> bytes | None:
        """Fetch article detail page by PMID."""
        url = f"{PUBMED_BASE_URL}{pmid}/"
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.request_timeout)
                response.raise_for_status()
                return response.content
            except requests.RequestException as e:
                wait = self.config.retry_backoff * (2 ** attempt)
                logger.warning("Detail fetch attempt %d failed for PMID %d: %s. Retrying in %.1fs",
                               attempt + 1, pmid, e, wait)
                time.sleep(wait)
        logger.error("All detail fetch attempts failed for PMID %d", pmid)
        return None

    def _parse_detail_page(self, html: bytes, pmid: int) -> Article:
        """Parse a single article detail page."""
        soup = BeautifulSoup(html, "html.parser")
        article = Article(pmid=pmid)

        # PMCID
        heading = soup.find("div", class_="full-view", id="full-view-heading")
        if heading:
            heading_text = str(heading)
            pmcid_match = re.search(r"(PMC\d+)", heading_text)
            if pmcid_match:
                article.pmcid = pmcid_match.group(1)

        # Abstract
        abstract_block = soup.find("div", class_="abstract-content selected", id="eng-abstract")
        if abstract_block:
            article.abstract = self._parse_abstract(abstract_block)

        # Keywords
        keywords_div = soup.find("div", class_="abstract", id="abstract")
        if keywords_div:
            kw_match = re.search(r"Keywords:\s*(.*?)</(?:p|div|strong)>", str(keywords_div), re.S)
            if kw_match:
                article.keywords = re.sub(r"<[^>]+>", "", kw_match.group(1)).strip()

        # Affiliations
        if heading:
            aff_items = heading.find_all("li")
            if aff_items:
                parts = []
                for i, li in enumerate(aff_items, 1):
                    text = li.get_text(strip=True)
                    # Remove leading "1 " pattern from <sup>
                    text = re.sub(r"^\d+\s*", "", text)
                    parts.append(f"{i}. {text}")
                article.affiliations = " ".join(parts)

        return article

    def _parse_abstract(self, block) -> str:  # type: ignore[ann-arg]
        """Parse abstract block, handling both sectioned and plain formats."""
        paragraphs = block.find_all("p")
        if not paragraphs:
            return ""

        # Check if abstract has sections (BACKGROUND:, METHODS:, etc.)
        has_sections = any(p.find("strong") for p in paragraphs)

        if has_sections:
            parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                text = re.sub(r"\s{2,}", " ", text)
                if text:
                    parts.append(text)
            return "\n".join(parts)
        else:
            # Plain abstract
            text = " ".join(p.get_text(strip=True) for p in paragraphs)
            return re.sub(r"\s{2,}", " ", text)

    def fetch_details(self, articles: list[Article]) -> list[Article]:
        """Fetch detail info for a list of articles. Updates articles in-place."""
        for i, article in enumerate(articles):
            if not article.pmid:
                logger.warning("Article missing PMID, skipping detail fetch: %s", article.title[:50])
                continue

            logger.info("Fetching detail for PMID %d (%d/%d)", article.pmid, i + 1, len(articles))
            html = self._fetch_detail(article.pmid)
            if html is None:
                logger.warning("Failed to fetch detail for PMID %d, skipping", article.pmid)
                continue

            try:
                detail = self._parse_detail_page(html, article.pmid)
                article.pmcid = detail.pmcid
                article.abstract = detail.abstract
                article.keywords = detail.keywords
                article.affiliations = detail.affiliations
            except Exception:
                logger.warning("Failed to parse detail for PMID %d, skipping", article.pmid, exc_info=True)

            time.sleep(self.config.min_request_interval)

        return articles
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_detail.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/pubmedsoso/core/detail.py tests/test_detail.py tests/fixtures/detail_page.html
git commit -m "feat: add DetailFetcher with abstract/keyword/affiliation parsing"
```

---

## Task 7: PDF Download (core/download.py)

**Files:**
- Create: `src/pubmedsoso/core/download.py`
- Create: `tests/test_download.py`

- [ ] **Step 1: Write failing tests for download**

```python
# tests/test_download.py
from pathlib import Path
from unittest.mock import patch, MagicMock

from pubmedsoso.config import Config
from pubmedsoso.core.download import PMCDownloader, SciHubDownloader, DownloadManager
from pubmedsoso.models import Article, FreeStatus


def test_pmc_downloader_builds_correct_url():
    downloader = PMCDownloader(Config())
    article = Article(pmcid="PMC9034016", title="Test", free_status=FreeStatus.FREE_PMC)
    url = downloader._build_pdf_url(article)
    assert "PMC9034016" in url
    assert "pdf" in url


@patch("pubmedsoso.core.download.requests.Session")
def test_pmc_downloader_success(mock_session_cls, tmp_path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    config = Config(download_dir=tmp_path)
    downloader = PMCDownloader(config)
    article = Article(pmcid="PMC1234567", title="Test Article", free_status=FreeStatus.FREE_PMC)
    result = downloader.download(article)

    assert result is not None
    assert result.exists()
    assert result.suffix == ".pdf"


@patch("pubmedsoso.core.download.requests.Session")
def test_pmc_downloader_timeout(mock_session_cls, tmp_path):
    import requests as req
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_session.get.side_effect = req.exceptions.Timeout("timeout")

    config = Config(download_dir=tmp_path)
    downloader = PMCDownloader(config)
    article = Article(pmcid="PMC1234567", title="Test", free_status=FreeStatus.FREE_PMC)
    result = downloader.download(article)
    assert result is None


def test_scihub_downloader_disabled():
    config = Config(scihub_enabled=False)
    downloader = SciHubDownloader(config)
    article = Article(doi="10.1234/test", title="Test")
    result = downloader.download(article)
    assert result is None


@patch("pubmedsoso.core.download.requests.Session")
def test_download_manager_pmc_first(mock_session_cls, tmp_path):
    """DownloadManager should try PMC first for FREE_PMC articles."""
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake"
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response

    config = Config(download_dir=tmp_path)
    manager = DownloadManager(config)
    article = Article(pmcid="PMC123", title="Test", free_status=FreeStatus.FREE_PMC, doi="10.1/x")
    result = manager.download(article)
    assert result is not None


@patch("pubmedsoso.core.download.PMCDownloader.download")
@patch("pubmedsoso.core.download.SciHubDownloader.download")
def test_download_manager_falls_back_to_scihub(mock_scihub, mock_pmc, tmp_path):
    """If PMC fails, DownloadManager should try SciHub."""
    mock_pmc.return_value = None  # PMC fails
    mock_scihub.return_value = Path("/fake/path.pdf")  # SciHub succeeds

    config = Config(download_dir=tmp_path)
    manager = DownloadManager(config)
    article = Article(pmcid="PMC123", title="Test", free_status=FreeStatus.FREE_PMC, doi="10.1/x")
    result = manager.download(article)
    assert result is not None
    mock_scihub.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_download.py -v
```

Expected: FAIL

- [ ] **Step 3: Write core/download.py**

```python
# src/pubmedsoso/core/download.py
"""PDF downloaders for PubMed Central and SciHub."""

import logging
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from pubmedsoso.config import Config
from pubmedsoso.models import Article, FreeStatus

logger = logging.getLogger(__name__)


class BaseDownloader(ABC):
    """Base class for PDF downloaders."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

    @abstractmethod
    def download(self, article: Article) -> Path | None:
        """Download PDF for an article. Returns file path or None on failure."""


class PMCDownloader(BaseDownloader):
    """Downloads free PDFs from PubMed Central."""

    NCBI_BASE = "https://www.ncbi.nlm.nih.gov/"

    def _build_pdf_url(self, article: Article) -> str:
        return f"{self.NCBI_BASE}pmc/articles/{article.pmcid}/pdf/"

    def _sanitize_filename(self, title: str) -> str:
        """Remove characters invalid in filenames."""
        return re.sub(r'[<>/\\|:"*?]', ' ', title)[:200]

    def download(self, article: Article) -> Path | None:
        if not article.pmcid:
            return None

        url = self._build_pdf_url(article)
        logger.info("Downloading PMC PDF: %s", url)

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.download_timeout)
                response.raise_for_status()

                if b"%PDF" not in response.content[:10]:
                    logger.warning("Response doesn't look like a PDF for %s", article.pmcid)
                    continue

                filename = self._sanitize_filename(article.title)
                save_path = self.config.download_dir / f"{filename}.pdf"
                self.config.download_dir.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(response.content)

                logger.info("Downloaded %s to %s", article.pmcid, save_path)
                return save_path

            except requests.RequestException as e:
                wait = self.config.retry_backoff * (2 ** attempt)
                logger.warning("PMC download attempt %d failed for %s: %s. Retrying in %.1fs",
                               attempt + 1, article.pmcid, e, wait)
                time.sleep(wait)

        logger.error("All PMC download attempts failed for %s", article.pmcid)
        return None


class SciHubDownloader(BaseDownloader):
    """Downloads PDFs from SciHub as a fallback."""

    def download(self, article: Article) -> Path | None:
        if not self.config.scihub_enabled:
            logger.info("SciHub disabled, skipping")
            return None

        if not article.doi:
            logger.info("No DOI for article, cannot use SciHub: %s", article.title[:50])
            return None

        logger.info("Attempting SciHub download for DOI: %s", article.doi)

        # Step 1: Search SciHub for the DOI
        search_url = f"{self.config.scihub_base_url}/{article.doi}"
        try:
            response = self.session.get(search_url, timeout=self.config.download_timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning("SciHub search failed for DOI %s: %s", article.doi, e)
            return None

        # Step 2: Parse PDF link from SciHub page
        pdf_url = self._extract_pdf_url(response.text)
        if not pdf_url:
            logger.warning("Could not find PDF link on SciHub for DOI %s", article.doi)
            return None

        # Step 3: Download the PDF
        try:
            pdf_response = self.session.get(pdf_url, timeout=self.config.download_timeout)
            pdf_response.raise_for_status()

            if b"%PDF" not in pdf_response.content[:10]:
                logger.warning("SciHub response doesn't look like a PDF for DOI %s", article.doi)
                return None

            filename = re.sub(r'[<>/\\|:"*?]', ' ', article.title)[:200]
            save_path = self.config.download_dir / f"{filename}.pdf"
            self.config.download_dir.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(pdf_response.content)

            logger.info("SciHub download succeeded for DOI %s", article.doi)
            return save_path

        except requests.RequestException as e:
            logger.warning("SciHub PDF download failed for DOI %s: %s", article.doi, e)
            return None

    def _extract_pdf_url(self, html: str) -> str | None:
        """Extract PDF URL from SciHub page HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # SciHub typically embeds PDF in an iframe or embed tag
        iframe = soup.find("iframe", id="pdf")
        if iframe and iframe.get("src"):
            src = iframe["src"]
            if src.startswith("//"):
                return f"https:{src}"
            if src.startswith("/"):
                return f"{self.config.scihub_base_url}{src}"
            return src

        # Fallback: look for embed tag
        embed = soup.find("embed", type="application/pdf")
        if embed and embed.get("src"):
            src = embed["src"]
            if src.startswith("//"):
                return f"https:{src}"
            return src

        return None


class DownloadManager:
    """Manages PDF downloads: PMC first, SciHub fallback."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.pmc = PMCDownloader(config)
        self.scihub = SciHubDownloader(config)

    def download(self, article: Article) -> Path | None:
        """Download PDF for an article. Tries PMC first, then SciHub."""
        # Try PMC for free articles
        if article.free_status == FreeStatus.FREE_PMC and article.pmcid:
            result = self.pmc.download(article)
            if result:
                return result
            logger.info("PMC download failed for %s, trying SciHub fallback", article.pmcid)

        # SciHub fallback for any article with a DOI
        if article.doi:
            return self.scihub.download(article)

        return None

    def download_batch(self, articles: list[Article], limit: int = 0) -> list[tuple[Article, Path | None]]:
        """Download PDFs for a batch of articles.

        Args:
            articles: List of articles to download.
            limit: Maximum number of downloads. 0 = no limit.

        Returns:
            List of (article, path_or_none) tuples.
        """
        results: list[tuple[Article, Path | None]] = []
        downloaded = 0

        for article in articles:
            if limit > 0 and downloaded >= limit:
                logger.info("Reached download limit of %d", limit)
                break

            path = self.download(article)
            results.append((article, path))
            if path:
                downloaded += 1

            time.sleep(self.config.min_request_interval)

        logger.info("Downloaded %d of %d articles", downloaded, len(articles))
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_download.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pubmedsoso/core/download.py tests/test_download.py
git commit -m "feat: add PMCDownloader, SciHubDownloader, and DownloadManager"
```

---

## Task 8: Data Export (core/export.py)

**Files:**
- Create: `src/pubmedsoso/core/export.py`
- Create: `tests/test_export.py`

- [ ] **Step 1: Write failing tests for export**

```python
# tests/test_export.py
import csv
from pathlib import Path

from openpyxl import load_workbook

from pubmedsoso.core.export import Exporter
from pubmedsoso.models import Article, FreeStatus


def _sample_articles():
    return [
        Article(
            id=1, title="Test Article 1", authors="Smith J", journal="Nature 2024",
            doi="10.1/test1", pmid=111, pmcid="PMC111", abstract="Abstract 1",
            keywords="cancer", affiliations="1. MIT", free_status=FreeStatus.FREE_PMC,
            is_review=False, save_path="/pdfs/test1.pdf",
        ),
        Article(
            id=2, title="Test Article 2", authors="Lee K", journal="Science 2024",
            doi="10.1/test2", pmid=222, pmcid="", abstract="Abstract 2",
            keywords="therapy", affiliations="1. Stanford", free_status=FreeStatus.NOT_FREE,
            is_review=True, save_path="",
        ),
    ]


def test_export_xlsx(tmp_path):
    articles = _sample_articles()
    path = tmp_path / "test.xlsx"
    result = Exporter.to_xlsx(articles, path)

    assert result.exists()
    wb = load_workbook(result)
    ws = wb.active
    # Header row + 2 data rows
    assert ws.max_row == 3
    # Check header
    assert ws.cell(1, 1).value == "序号"
    assert ws.cell(1, 2).value == "文献标题"
    # Check data
    assert ws.cell(2, 2).value == "Test Article 1"
    assert ws.cell(3, 2).value == "Test Article 2"


def test_export_xlsx_free_status_display(tmp_path):
    articles = _sample_articles()
    path = tmp_path / "test.xlsx"
    Exporter.to_xlsx(articles, path)

    wb = load_workbook(path)
    ws = wb.active
    # FREE_PMC → "是", NOT_FREE → "否"
    assert ws.cell(2, 11).value == "是"  # Article 1: FREE_PMC
    assert ws.cell(3, 11).value == "否"  # Article 2: NOT_FREE


def test_export_csv(tmp_path):
    articles = _sample_articles()
    path = tmp_path / "test.csv"
    result = Exporter.to_csv(articles, path)

    assert result.exists()
    with open(result, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 3  # header + 2 data
    assert rows[0][1] == "文献标题"
    assert rows[1][1] == "Test Article 1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_export.py -v
```

Expected: FAIL

- [ ] **Step 3: Write core/export.py**

```python
# src/pubmedsoso/core/export.py
"""Data export to xlsx and csv formats."""

import csv
import logging
from pathlib import Path

from openpyxl import Workbook

from pubmedsoso.models import Article, FreeStatus

logger = logging.getLogger(__name__)

# Column headers in Chinese (matching original behavior)
COLUMNS = (
    "序号", "文献标题", "作者名单", "期刊年份", "doi",
    "PMID", "PMCID", "摘要", "关键词", "作者单位",
    "是否有免费全文", "是否是review", "保存路径",
)


def _article_to_row(article: Article, index: int) -> list[str]:
    """Convert an Article to a row for export."""
    free_display = {
        FreeStatus.FREE_PMC: "是",
        FreeStatus.FREE_ARTICLE: "否",
        FreeStatus.NOT_FREE: "否",
    }
    return [
        str(index),
        article.title,
        article.authors,
        article.journal,
        article.doi,
        str(article.pmid or ""),
        article.pmcid,
        article.abstract,
        article.keywords,
        article.affiliations,
        free_display.get(article.free_status, "否"),
        "是" if article.is_review else "否",
        article.save_path,
    ]


class Exporter:
    """Exports article data to xlsx or csv."""

    @staticmethod
    def to_xlsx(articles: list[Article], path: Path) -> Path:
        """Export articles to .xlsx file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "pubmedsoso"

        # Write header
        for col_idx, header in enumerate(COLUMNS, 1):
            ws.cell(row=1, column=col_idx, value=header)

        # Write data
        for row_idx, article in enumerate(articles, 2):
            row = _article_to_row(article, row_idx - 1)
            for col_idx, value in enumerate(row, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

        wb.save(path)
        logger.info("Exported %d articles to %s", len(articles), path)
        return path

    @staticmethod
    def to_csv(articles: list[Article], path: Path) -> Path:
        """Export articles to .csv file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            for idx, article in enumerate(articles, 1):
                writer.writerow(_article_to_row(article, idx))

        logger.info("Exported %d articles to %s", len(articles), path)
        return path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_export.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pubmedsoso/core/export.py tests/test_export.py
git commit -m "feat: add Exporter with xlsx and csv output"
```

---

## Task 9: CLI Commands (cli/commands.py + main.py)

**Files:**
- Create: `src/pubmedsoso/cli/commands.py`
- Create: `src/pubmedsoso/main.py`

- [ ] **Step 1: Write main.py as CLI entry point**

```python
# src/pubmedsoso/main.py
"""Pubmedsoso — PubMed literature crawler."""

import typer

app = typer.Typer(
    name="pubmedsoso",
    help="PubMed literature crawler — search, extract, download, export.",
)


@app.command()
def search(
    keyword: str = typer.Argument(..., help='Search keyword, e.g. "alzheimer"'),
    page_num: int = typer.Option(10, "--page-num", "-n", help="Number of pages to crawl (50 results per page)"),
    download_num: int = typer.Option(10, "--download-num", "-d", help="Number of PDFs to download"),
    no_download: bool = typer.Option(False, "--no-download", help="Skip PDF download"),
    format: str = typer.Option("xlsx", "--format", "-f", help="Export format: xlsx or csv"),
) -> None:
    """Search PubMed, extract article info, download PDFs, and export."""
    import logging
    from datetime import datetime

    from pubmedsoso.config import Config
    from pubmedsoso.core.search import PubMedSearcher
    from pubmedsoso.core.detail import DetailFetcher
    from pubmedsoso.core.download import DownloadManager
    from pubmedsoso.core.export import Exporter
    from pubmedsoso.db.database import Database
    from pubmedsoso.db.repository import ArticleRepository
    from pubmedsoso.models import SearchParams

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    config = Config.from_env()
    config.ensure_dirs()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    db_path = config.db_dir / f"pubmed_{timestamp}.db"

    typer.echo(f"🔍 Searching PubMed for: {keyword}")
    typer.echo(f"   Pages: {page_num}, Downloads: {download_num}")

    # Step 1: Search
    params = SearchParams(keyword=keyword, page_num=page_num, download_limit=download_num)
    searcher = PubMedSearcher(config)
    result = searcher.search(params)
    typer.echo(f"   Found {result.total_count} results, crawled {result.pages_crawled} pages ({len(result.articles)} articles)")

    # Step 2: Save to DB
    db = Database(db_path)
    db.init_schema()
    repo = ArticleRepository(db)
    repo.insert_batch(result.articles)
    typer.echo(f"   Saved to {db_path}")

    # Step 3: Fetch details
    typer.echo("📄 Fetching article details...")
    fetcher = DetailFetcher(config)
    fetcher.fetch_details(result.articles)
    for article in result.articles:
        repo.update_detail(article)

    # Step 4: Download PDFs
    if not no_download:
        typer.echo(f"⬇️  Downloading up to {download_num} PDFs...")
        manager = DownloadManager(config)
        free_articles = repo.get_free_pmc_articles()
        results = manager.download_batch(free_articles, limit=download_num)
        for article, path in results:
            if path and article.pmcid:
                repo.update_save_path(article.pmcid, str(path))
        downloaded = sum(1 for _, p in results if p is not None)
        typer.echo(f"   Downloaded {downloaded} PDFs")
    else:
        typer.echo("⏭️  Skipping PDF download")

    # Step 5: Export
    all_articles = repo.get_all_articles()
    ext = "xlsx" if format == "xlsx" else "csv"
    export_path = config.export_dir / f"pubmed_{timestamp}.{ext}"
    if format == "xlsx":
        Exporter.to_xlsx(all_articles, export_path)
    else:
        Exporter.to_csv(all_articles, export_path)
    typer.echo(f"📊 Exported to {export_path}")
    typer.echo("✅ Done!")


@app.command()
def export(
    list_tables: bool = typer.Option(False, "--list", "-l", help="List available search results"),
    task: str = typer.Option("", "--task", "-t", help="Task timestamp to export (e.g. 20260412120000)"),
    format: str = typer.Option("xlsx", "--format", "-f", help="Export format: xlsx or csv"),
) -> None:
    """Export historical search results to Excel or CSV."""
    import logging
    from pubmedsoso.config import Config
    from pubmedsoso.core.export import Exporter
    from pubmedsoso.db.database import Database
    from pubmedsoso.db.repository import ArticleRepository

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    config = Config.from_env()

    if list_tables:
        # List all .db files in data dir
        db_files = sorted(config.db_dir.glob("pubmed_*.db"))
        if not db_files:
            typer.echo("No search results found.")
            return
        for f in db_files:
            name = f.stem.replace("pubmed_", "")
            typer.echo(f"  {name}")
        return

    if not task:
        typer.echo("Please specify --task to export. Use --list to see available tasks.")
        raise typer.Exit(1)

    db_path = config.db_dir / f"pubmed_{task}.db"
    if not db_path.exists():
        typer.echo(f"Database not found: {db_path}")
        raise typer.Exit(1)

    db = Database(db_path)
    repo = ArticleRepository(db)
    articles = repo.get_all_articles()

    ext = "xlsx" if format == "xlsx" else "csv"
    export_path = config.export_dir / f"pubmed_{task}.{ext}"
    if format == "xlsx":
        Exporter.to_xlsx(articles, export_path)
    else:
        Exporter.to_csv(articles, export_path)
    typer.echo(f"Exported {len(articles)} articles to {export_path}")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
) -> None:
    """Start the Pubmedsoso Web UI."""
    import uvicorn
    from pubmedsoso.web.app import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)


def _version_callback(value: bool) -> None:
    if value:
        from pubmedsoso import __version__
        typer.echo(f"Pubmedsoso v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", callback=_version_callback, is_eager=True, help="Show version"),
) -> None:
    """PubMed literature crawler — search, extract, download, export."""
    pass


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Write cli/commands.py as re-export**

```python
# src/pubmedsoso/cli/commands.py
"""CLI command definitions — re-exports from main for backward compatibility."""

from pubmedsoso.main import app

__all__ = ["app"]
```

- [ ] **Step 3: Verify CLI works**

```bash
pip install -e ".[dev]"
pubmedsoso --version
pubmedsoso --help
pubmedsoso search --help
pubmedsoso export --help
pubmedsoso web --help
```

Expected: Version printed, help text shown for all commands

- [ ] **Step 4: Commit**

```bash
git add src/pubmedsoso/main.py src/pubmedsoso/cli/commands.py
git commit -m "feat: add CLI with search, export, and web commands via typer"
```

---

## Task 10: FastAPI Web UI (web/)

**Files:**
- Create: `src/pubmedsoso/web/app.py`
- Create: `src/pubmedsoso/web/routes.py`
- Create: `src/pubmedsoso/web/schemas.py`
- Create: `src/pubmedsoso/web/static/index.html`
- Create: `src/pubmedsoso/web/static/style.css`
- Create: `src/pubmedsoso/web/static/app.js`

- [ ] **Step 1: Write schemas.py**

```python
# src/pubmedsoso/web/schemas.py
"""Pydantic schemas for the Web API."""

from pydantic import BaseModel


class SearchRequest(BaseModel):
    keyword: str
    page_num: int = 10
    download_num: int = 10
    no_download: bool = False


class TaskStatus(BaseModel):
    task_id: str
    status: str  # "searching" | "fetching_details" | "downloading" | "exporting" | "complete" | "error"
    progress: str = ""
    result_count: int = 0
    download_count: int = 0


class ArticleResponse(BaseModel):
    id: int
    title: str
    authors: str
    journal: str
    doi: str
    pmid: int | None
    pmcid: str
    abstract: str
    keywords: str
    affiliations: str
    free_status: int
    is_review: bool
    save_path: str


class HistoryItem(BaseModel):
    task_id: str
    article_count: int
    created_at: str = ""
```

- [ ] **Step 2: Write app.py**

```python
# src/pubmedsoso/web/app.py
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from pubmedsoso.web.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pubmedsoso",
        description="PubMed literature crawler — search, extract, download, export",
        version="2.0.0",
    )

    app.include_router(router, prefix="/api")

    # Serve static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
```

- [ ] **Step 3: Write routes.py**

```python
# src/pubmedsoso/web/routes.py
"""API routes for Pubmedsoso Web UI."""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.core.download import DownloadManager
from pubmedsoso.core.export import Exporter
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import SearchParams
from pubmedsoso.web.schemas import SearchRequest, TaskStatus, ArticleResponse, HistoryItem

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory task store (single process)
_tasks: dict[str, TaskStatus] = {}


def _run_search(task_id: str, request: SearchRequest) -> None:
    """Run the full search pipeline in background."""
    try:
        config = Config.from_env()
        config.ensure_dirs()

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        db_path = config.db_dir / f"pubmed_{timestamp}.db"

        # Step 1: Search
        _tasks[task_id].status = "searching"
        _tasks[task_id].progress = "Searching PubMed..."
        params = SearchParams(keyword=request.keyword, page_num=request.page_num, download_limit=request.download_num)
        searcher = PubMedSearcher(config)
        result = searcher.search(params)
        _tasks[task_id].result_count = len(result.articles)

        # Step 2: Save to DB
        db = Database(db_path)
        db.init_schema()
        repo = ArticleRepository(db)
        repo.insert_batch(result.articles)

        # Step 3: Fetch details
        _tasks[task_id].status = "fetching_details"
        _tasks[task_id].progress = "Fetching article details..."
        fetcher = DetailFetcher(config)
        fetcher.fetch_details(result.articles)
        for article in result.articles:
            repo.update_detail(article)

        # Step 4: Download PDFs
        if not request.no_download:
            _tasks[task_id].status = "downloading"
            _tasks[task_id].progress = "Downloading PDFs..."
            manager = DownloadManager(config)
            free_articles = repo.get_free_pmc_articles()
            download_results = manager.download_batch(free_articles, limit=request.download_num)
            for article, path in download_results:
                if path and article.pmcid:
                    repo.update_save_path(article.pmcid, str(path))
            _tasks[task_id].download_count = sum(1 for _, p in download_results if p is not None)

        # Step 5: Export
        _tasks[task_id].status = "exporting"
        _tasks[task_id].progress = "Exporting results..."
        all_articles = repo.get_all_articles()
        export_path = config.export_dir / f"pubmed_{timestamp}.xlsx"
        Exporter.to_xlsx(all_articles, export_path)

        _tasks[task_id].status = "complete"
        _tasks[task_id].progress = f"Done! {len(all_articles)} articles processed."
        _tasks[task_id].result_count = len(all_articles)

    except Exception as e:
        logger.exception("Search task %s failed", task_id)
        _tasks[task_id].status = "error"
        _tasks[task_id].progress = str(e)


@router.post("/search", response_model=TaskStatus)
async def start_search(request: SearchRequest):
    """Start an async search task."""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = TaskStatus(task_id=task_id, status="searching", progress="Starting...")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_search, task_id, request)

    return _tasks[task_id]


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a search task."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.get("/articles", response_model=list[ArticleResponse])
async def list_articles(task_id: str, skip: int = 0, limit: int = 50):
    """Get articles for a search task."""
    config = Config.from_env()
    # Find the db file for this task
    db_files = sorted(config.db_dir.glob("pubmed_*.db"))
    if not db_files:
        raise HTTPException(status_code=404, detail="No search results found")

    db_path = db_files[-1]  # Most recent
    db = Database(db_path)
    repo = ArticleRepository(db)
    all_articles = repo.get_all_articles()
    return all_articles[skip : skip + limit]


@router.get("/export")
async def export_results(task_id: str, format: str = "xlsx"):
    """Export search results as xlsx or csv."""
    config = Config.from_env()
    db_files = sorted(config.db_dir.glob("pubmed_*.db"))
    if not db_files:
        raise HTTPException(status_code=404, detail="No search results found")

    db_path = db_files[-1]
    db = Database(db_path)
    repo = ArticleRepository(db)
    articles = repo.get_all_articles()

    ext = "xlsx" if format == "xlsx" else "csv"
    export_path = config.export_dir / f"export.{ext}"
    if format == "xlsx":
        Exporter.to_xlsx(articles, export_path)
    else:
        Exporter.to_csv(articles, export_path)

    return FileResponse(export_path, filename=f"pubmed_results.{ext}")


@router.get("/history", response_model=list[HistoryItem])
async def get_history():
    """Get historical search records."""
    config = Config.from_env()
    db_files = sorted(config.db_dir.glob("pubmed_*.db"))

    history = []
    for f in db_files:
        timestamp = f.stem.replace("pubmed_", "")
        db = Database(f)
        repo = ArticleRepository(db)
        articles = repo.get_all_articles()
        history.append(HistoryItem(
            task_id=timestamp,
            article_count=len(articles),
            created_at=timestamp,
        ))
    return history
```

- [ ] **Step 4: Write static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pubmedsoso</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div class="container">
        <h1>🔍 Pubmedsoso</h1>
        <p class="subtitle">PubMed 文献爬取工具</p>

        <div class="search-form">
            <input type="text" id="keyword" placeholder="输入搜索关键词..." autofocus>
            <div class="options">
                <label>检索页数: <input type="number" id="pageNum" value="10" min="1" max="100"></label>
                <label>下载数量: <input type="number" id="downloadNum" value="10" min="0" max="500"></label>
                <label><input type="checkbox" id="noDownload"> 跳过下载</label>
            </div>
            <button id="searchBtn" onclick="startSearch()">搜索</button>
        </div>

        <div id="progress" class="progress hidden">
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <p id="progressText"></p>
        </div>

        <div id="results" class="results hidden">
            <div class="results-header">
                <h2 id="resultsTitle">搜索结果</h2>
                <div class="actions">
                    <button onclick="exportResults('xlsx')">导出 Excel</button>
                    <button onclick="exportResults('csv')">导出 CSV</button>
                </div>
            </div>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>标题</th>
                        <th>作者</th>
                        <th>期刊</th>
                        <th>免费</th>
                        <th>Review</th>
                    </tr>
                </thead>
                <tbody id="resultsBody"></tbody>
            </table>
        </div>
    </div>
    <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write static/style.css**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
.container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 2rem; margin-bottom: 0.25rem; }
.subtitle { color: #666; margin-bottom: 2rem; }
.search-form { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem; }
#keyword { width: 100%; padding: 0.75rem; font-size: 1rem; border: 2px solid #ddd; border-radius: 4px; margin-bottom: 1rem; }
#keyword:focus { border-color: #4a90d9; outline: none; }
.options { display: flex; gap: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.options label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
.options input[type="number"] { width: 80px; padding: 0.4rem; border: 1px solid #ddd; border-radius: 4px; }
button { background: #4a90d9; color: white; border: none; padding: 0.75rem 2rem; border-radius: 4px; cursor: pointer; font-size: 1rem; }
button:hover { background: #357abd; }
button:disabled { background: #ccc; cursor: not-allowed; }
.progress { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem; }
.progress-bar { background: #eee; border-radius: 4px; height: 8px; overflow: hidden; }
.progress-fill { background: #4a90d9; height: 100%; width: 0%; transition: width 0.5s; }
.results { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.actions { display: flex; gap: 0.5rem; }
.actions button { padding: 0.5rem 1rem; font-size: 0.85rem; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }
th { background: #f8f8f8; font-weight: 600; }
tr:hover { background: #f0f7ff; }
.hidden { display: none; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8rem; }
.tag-free { background: #d4edda; color: #155724; }
.tag-review { background: #fff3cd; color: #856404; }
```

- [ ] **Step 6: Write static/app.js**

```javascript
let currentTaskId = null;
let pollInterval = null;

async function startSearch() {
    const keyword = document.getElementById('keyword').value.trim();
    if (!keyword) { alert('请输入搜索关键词'); return; }

    const pageNum = parseInt(document.getElementById('pageNum').value);
    const downloadNum = parseInt(document.getElementById('downloadNum').value);
    const noDownload = document.getElementById('noDownload').checked;

    document.getElementById('searchBtn').disabled = true;
    document.getElementById('progress').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    setProgress(10, '正在提交搜索...');

    try {
        const resp = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword, page_num: pageNum, download_num: downloadNum, no_download: noDownload })
        });
        const data = await resp.json();
        currentTaskId = data.task_id;
        pollStatus();
    } catch (e) {
        setProgress(0, '搜索失败: ' + e.message);
        document.getElementById('searchBtn').disabled = false;
    }
}

function pollStatus() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/tasks/${currentTaskId}`);
            const data = await resp.json();

            const pct = { searching: 30, fetching_details: 60, downloading: 80, exporting: 95, complete: 100, error: 0 };
            setProgress(pct[data.status] || 50, data.progress);

            if (data.status === 'complete') {
                clearInterval(pollInterval);
                document.getElementById('searchBtn').disabled = false;
                loadArticles();
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                document.getElementById('searchBtn').disabled = false;
            }
        } catch (e) { /* ignore poll errors */ }
    }, 2000);
}

function setProgress(pct, text) {
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressText').textContent = text;
}

async function loadArticles() {
    try {
        const resp = await fetch(`/api/articles?task_id=${currentTaskId}`);
        const articles = await resp.json();
        renderArticles(articles);
    } catch (e) { /* ignore */ }
}

function renderArticles(articles) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    articles.forEach((a, i) => {
        const freeTag = a.free_status === 2 ? '<span class="tag tag-free">免费</span>' : '';
        const reviewTag = a.is_review ? '<span class="tag tag-review">Review</span>' : '';
        tbody.innerHTML += `<tr>
            <td>${i + 1}</td>
            <td>${a.title}</td>
            <td>${a.authors}</td>
            <td>${a.journal}</td>
            <td>${freeTag}</td>
            <td>${reviewTag}</td>
        </tr>`;
    });
    document.getElementById('results').classList.remove('hidden');
    document.getElementById('resultsTitle').textContent = `搜索结果 (${articles.length} 篇)`;
}

function exportResults(format) {
    window.open(`/api/export?task_id=${currentTaskId}&format=${format}`, '_blank');
}
```

- [ ] **Step 7: Verify Web UI starts**

```bash
pubmedsoso web --port 8000 &
sleep 2
curl -s http://localhost:8000/api/history | head -20
kill %1
```

Expected: Empty JSON array `[]` (no history yet)

- [ ] **Step 8: Commit**

```bash
git add src/pubmedsoso/web/
git commit -m "feat: add FastAPI Web UI with search, progress, and export"
```

---

## Task 11: Integration Test + Final Wiring

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test (mocked HTTP)**

```python
# tests/test_integration.py
"""Integration test: full pipeline with mocked HTTP."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.core.export import Exporter
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import SearchParams, FreeStatus


def test_full_pipeline(tmp_path, fixtures_dir):
    """Test the full search → detail → export pipeline with mocked HTTP."""
    config = Config(
        db_dir=tmp_path / "data",
        download_dir=tmp_path / "pdfs",
        export_dir=tmp_path / "exports",
    )
    config.ensure_dirs()

    # Step 1: Search (using local fixture HTML)
    search_html = (fixtures_dir / "search_page.html").read_bytes()
    searcher = PubMedSearcher(config)
    articles = searcher._parse_search_page(search_html)
    assert len(articles) == 3

    # Step 2: Save to DB
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.init_schema()
    repo = ArticleRepository(db)
    count = repo.insert_batch(articles)
    assert count == 3

    # Step 3: Fetch details (using local fixture HTML)
    detail_html = (fixtures_dir / "detail_page.html").read_bytes()
    fetcher = DetailFetcher(config)
    for article in articles:
        detail = fetcher._parse_detail_page(detail_html, article.pmid or 0)
        article.pmcid = detail.pmcid
        article.abstract = detail.abstract
        article.keywords = detail.keywords
        article.affiliations = detail.affiliations
        repo.update_detail(article)

    # Step 4: Verify DB state
    all_articles = repo.get_all_articles()
    assert len(all_articles) == 3
    assert all_articles[0].pmcid == "PMC9876543"

    # Step 5: Export
    export_path = tmp_path / "result.xlsx"
    Exporter.to_xlsx(all_articles, export_path)
    assert export_path.exists()

    csv_path = tmp_path / "result.csv"
    Exporter.to_csv(all_articles, csv_path)
    assert csv_path.exists()
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full pipeline"
```

---

## Task 12: README + Cleanup

**Files:**
- Modify: `README.adoc` → replace with `README.md`
- Delete: `assets/` (old screenshots, can be regenerated)
- Delete: `pubmedsoso.ico` (old icon)

- [ ] **Step 1: Write new README.md**

```markdown
# Pubmedsoso

一个自动批量提取 PubMed 文献信息和下载免费文献的工具。

## 功能

- 🔍 关键词搜索 PubMed 文献
- 📄 自动提取文献详情（标题、摘要、关键词、作者、单位等）
- ⬇️ 下载免费 PMC 全文 PDF
- 🔄 SciHub 兜底下载非免费文献
- 📊 导出为 Excel (.xlsx) 或 CSV
- 🖥️ CLI 和 Web UI 两种使用方式

## 安装

```bash
git clone https://github.com/hiddenblue/Pubmedsoso.git
cd Pubmedsoso
pip install -e .
```

## 使用

### CLI

```bash
# 搜索 + 提取 + 下载 + 导出
pubmedsoso search "alzheimer's disease" -n 10 -d 5

# 仅搜索提取，不下载 PDF
pubmedsoso search "headache" -n 5 --no-download

# 导出历史搜索结果
pubmedsoso export --list
pubmedsoso export --task 20260412120000 --format xlsx

# 启动 Web UI
pubmedsoso web --port 8080

# 版本信息
pubmedsoso --version
```

### Web UI

```bash
pubmedsoso web
# 打开浏览器访问 http://localhost:8000
```

## 配置

通过环境变量覆盖默认配置（前缀 `PUBMEDSOSO_`）：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| PUBMEDSOSO_SCIHUB_ENABLED | true | 启用 SciHub 兜底下载 |
| PUBMEDSOSO_SCIHUB_BASE_URL | https://sci-hub.se | SciHub 域名 |
| PUBMEDSOSO_DOWNLOAD_TIMEOUT | 60 | PDF 下载超时（秒） |
| PUBMEDSOSO_MIN_REQUEST_INTERVAL | 1.0 | 请求间隔（秒） |

## 开发

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```

## License

MIT
```

- [ ] **Step 2: Remove legacy files**

```bash
rm -f README.adoc pubmedsoso.ico
rm -rf assets/
```

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: add new README, remove legacy files"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: Every section in the design spec maps to a task (models → Task 2, config → Task 3, db → Task 4, search → Task 5, detail → Task 6, download → Task 7, export → Task 8, CLI → Task 9, web → Task 10, integration → Task 11, cleanup → Task 12)
- [x] **Placeholder scan**: No TBD/TODO/vague steps found. All code blocks contain complete implementations.
- [x] **Type consistency**: `Article`, `FreeStatus`, `Config`, `SearchParams`, `SearchResult` types are consistent across all tasks. Method signatures match between definition and usage.
