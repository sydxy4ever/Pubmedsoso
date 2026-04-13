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


def test_insert_batch_with_search_id(tmp_db):
    db = Database(tmp_db)
    db.init_schema()
    search_id = db.create_search("test keyword", "2026-01-01")
    repo = ArticleRepository(db)

    articles = [
        Article(title="S1 Article 1", pmid=111),
        Article(title="S1 Article 2", pmid=222),
    ]
    count = repo.insert_batch(articles, search_id=search_id)
    assert count == 2

    result = repo.get_all_articles(search_id=search_id)
    assert len(result) == 2
    assert result[0].title == "S1 Article 1"
    assert result[1].pmid == 222

    empty = repo.get_all_articles(search_id=999)
    assert empty == []
