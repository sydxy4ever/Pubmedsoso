"""Integration test: full pipeline with XML fixture."""

from xml.etree import ElementTree as ET

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.core.export import Exporter
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import FreeStatus


def test_full_pipeline(tmp_path, fixtures_dir):
    """Test the full search → save → export pipeline with XML fixture."""
    config = Config(
        db_dir=tmp_path / "data",
        export_dir=tmp_path / "exports",
    )
    config.ensure_dirs()

    # Step 1: Parse articles from XML fixture (simulates efetch results)
    xml_content = (fixtures_dir / "search_page.xml").read_bytes()
    root = ET.fromstring(xml_content)
    searcher = PubMedSearcher(config)
    articles = []
    for article_elem in root.findall(".//PubmedArticle"):
        article = searcher._parse_article_xml(article_elem)
        articles.append(article)
    assert len(articles) == 3

    # Verify efetch already provides details (abstract, keywords, pmcid)
    assert articles[0].pmcid == "PMC9876543"
    assert articles[0].free_status == FreeStatus.FREE_PMC
    assert "BACKGROUND" in articles[0].abstract
    assert "Alzheimer" in articles[0].keywords
    assert articles[1].is_review is True

    # Step 2: Save to DB
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.init_schema()
    repo = ArticleRepository(db)
    count = repo.insert_batch(articles)
    assert count == 3

    # Step 3: Verify DB state
    all_articles = repo.get_all_articles()
    assert len(all_articles) == 3
    assert all_articles[0].pmcid == "PMC9876543"

    # Step 4: Export
    export_path = tmp_path / "result.xlsx"
    Exporter.to_xlsx(all_articles, export_path)
    assert export_path.exists()

    csv_path = tmp_path / "result.csv"
    Exporter.to_csv(all_articles, csv_path)
    assert csv_path.exists()
