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

    assert articles[0].title == "Alzheimer's disease and neuroinflammation"
    assert articles[0].pmid == 12345678
    assert articles[0].free_status == FreeStatus.FREE_PMC
    assert articles[0].authors == "Smith J, Wang L, Chen Y."
    assert articles[0].doi == "doi: 10.1234/test.2024.123"
    assert articles[0].is_review is False

    assert articles[1].title == "Novel therapeutic approaches for headache"
    assert articles[1].pmid == 23456789
    assert articles[1].free_status == FreeStatus.NOT_FREE
    assert articles[1].is_review is True

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

    minimal_html = b'<div class="results-amount"><span class="value">60</span></div><div class="docsum-content"><a class="docsum-title" href="/111/"><b>Test</b></a><span class="citation-part">111</span><span class="full-authors">Author A</span><span class="journal-citation">J Med. 2024. doi: 10.1/x.</span></div>'

    mock_response = MagicMock()
    mock_response.content = minimal_html
    mock_session.get.return_value = mock_response

    searcher = PubMedSearcher(Config())
    result = searcher.search(SearchParams(keyword="test", page_num=2))

    assert result.pages_crawled == 2
    assert mock_session.get.call_count == 2
