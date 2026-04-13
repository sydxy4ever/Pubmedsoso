"""Integration test: full pipeline with mocked HTTP."""

from pathlib import Path

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.core.export import Exporter
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import FreeStatus


def test_full_pipeline(tmp_path, fixtures_dir):
    """Test the full search → detail → export pipeline with fixture HTML."""
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
        detail = fetcher._parse_detail_page(detail_html, article)
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
