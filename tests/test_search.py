"""Tests for PubMedSearcher E-UTILS API-based search."""

from unittest.mock import patch

from xml.etree import ElementTree as ET

from pubmedsoso.config import Config
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.models import FreeStatus, SearchParams


def test_parse_article_xml(fixtures_dir):
    """Parse the XML fixture and verify all three articles."""
    searcher = PubMedSearcher(Config())
    xml_content = (fixtures_dir / "search_page.xml").read_bytes()
    root = ET.fromstring(xml_content)
    article_elems = root.findall(".//PubmedArticle")
    assert len(article_elems) == 3

    articles = [searcher._parse_article_xml(elem) for elem in article_elems]

    # Article 0: Alzheimer's
    a0 = articles[0]
    assert a0.pmid == 12345678
    assert a0.title == "Alzheimer's disease and neuroinflammation"
    assert "Smith" in a0.authors
    assert "Neurosci Lett" in a0.journal
    assert a0.doi == "10.1234/test.2024.123"
    assert a0.free_status == FreeStatus.FREE_PMC
    assert a0.pmcid == "PMC9876543"
    assert "BACKGROUND" in a0.abstract
    assert "CONCLUSION" in a0.abstract
    assert "Alzheimer" in a0.keywords
    assert a0.is_review is False

    # Article 1: Headache review
    a1 = articles[1]
    assert a1.pmid == 23456789
    assert a1.title == "Novel therapeutic approaches for headache"
    assert a1.free_status == FreeStatus.NOT_FREE
    assert a1.is_review is True

    # Article 2: Cancer
    a2 = articles[2]
    assert a2.pmid == 34567890
    assert a2.title == "Cancer therapy resistance mechanisms"
    assert a2.free_status == FreeStatus.NOT_FREE


def test_esearch():
    """Mock _request_with_retry to return esearch XML, verify _esearch returns count and pmids."""
    searcher = PubMedSearcher(Config())
    esearch_xml = (
        b'<?xml version="1.0" ?>'
        b"<eSearchResult>"
        b"<Count>42</Count>"
        b"<IdList>"
        b"<Id>11111111</Id>"
        b"<Id>22222222</Id>"
        b"<Id>33333333</Id>"
        b"</IdList>"
        b"</eSearchResult>"
    )

    with patch.object(searcher, "_request_with_retry", return_value=esearch_xml):
        count, pmids = searcher._esearch("test query", retmax=10, retstart=0)

    assert count == 42
    assert pmids == ["11111111", "22222222", "33333333"]


def test_efetch(fixtures_dir):
    """Mock _request_with_retry to return XML fixture, verify _efetch returns Article list."""
    searcher = PubMedSearcher(Config())
    xml_content = (fixtures_dir / "search_page.xml").read_bytes()

    with patch.object(searcher, "_request_with_retry", return_value=xml_content):
        articles = searcher._efetch(["12345678", "23456789", "34567890"])

    assert len(articles) == 3
    assert articles[0].pmid == 12345678
    assert articles[1].pmid == 23456789
    assert articles[2].pmid == 34567890


def test_search_full(fixtures_dir):
    """Mock _esearch and _efetch to test the full search() flow."""
    searcher = PubMedSearcher(Config())
    xml_content = (fixtures_dir / "search_page.xml").read_bytes()
    articles = [
        searcher._parse_article_xml(elem)
        for elem in ET.fromstring(xml_content).findall(".//PubmedArticle")
    ]

    with patch.object(searcher, "_esearch", return_value=(3, ["12345678", "23456789", "34567890"])):
        with patch.object(searcher, "_efetch", return_value=articles):
            result = searcher.search(SearchParams(keyword="alzheimer"))

    assert result.total_count == 3
    assert len(result.articles) == 3
    assert result.articles[0].pmid == 12345678
    assert result.pages_crawled >= 1


def test_search_no_results():
    """Mock _esearch to return 0 results, verify empty SearchResult."""
    searcher = PubMedSearcher(Config())

    with patch.object(searcher, "_esearch", return_value=(0, [])):
        result = searcher.search(SearchParams(keyword="xyznonexistent"))

    assert result.total_count == 0
    assert result.articles == []
    assert result.pages_crawled == 0
