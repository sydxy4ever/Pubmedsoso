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
