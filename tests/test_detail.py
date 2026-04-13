from pathlib import Path
from unittest.mock import MagicMock, patch

from pubmedsoso.config import Config
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.models import Article, FreeStatus


def test_parse_detail_page(fixtures_dir):
    fetcher = DetailFetcher(Config())
    html = (fixtures_dir / "detail_page.html").read_bytes()

    article = Article(pmid=12345678, title="Test Article")
    result = fetcher._parse_detail_page(html, article)

    assert result.pmcid == "PMC9876543"
    assert "BACKGROUND:" in result.abstract
    assert "Alzheimer's disease (AD) is a neurodegenerative disorder" in result.abstract
    assert "METHODS:" in result.abstract
    assert "RESULTS:" in result.abstract
    assert "CONCLUSION:" in result.abstract
    assert "neuroinflammation" in result.keywords
    assert "cytokines" in result.keywords
    assert (
        result.affiliations
        == "1. Department of Neuroscience, University of California, San Francisco, CA, USA. 2. Institute for Neurodegenerative Diseases, Stanford University, Stanford, CA, USA. 3. Department of Neurology, Johns Hopkins University, Baltimore, MD, USA."
    )


def test_parse_detail_page_no_pmcid(fixtures_dir, tmp_path):
    no_pmcid_html = b"""<!DOCTYPE html>
<html>
<body>
<div class="article-details">
    <div class="heading">
        <h1 class="heading-title">Test Article Without PMCID</h1>
        <div class="article-source">
            <span class="citation-part">J Test. 2024;1:1-10.</span>
            <span class="citation-part"><a href="/99999999/">PMID: 99999999</a></span>
        </div>
        <ul class="affiliations">
            <li>Test Institution.</li>
        </ul>
    </div>
    <div class="abstract" id="abstract">
        <div class="abstract-content selected" id="eng-abstract">
            <p class="abstract-content">This is a plain abstract without sections.</p>
        </div>
    </div>
</div>
</body>
</html>"""

    fetcher = DetailFetcher(Config())
    article = Article(pmid=99999999, title="Test Article Without PMCID")
    result = fetcher._parse_detail_page(no_pmcid_html, article)

    assert result.pmcid == ""
    assert result.abstract == "This is a plain abstract without sections."
    assert result.keywords == ""
    assert result.affiliations == "1. Test Institution."


@patch("pubmedsoso.core.detail.requests.Session")
def test_fetch_detail_retry(mock_session_cls):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_response = MagicMock()
    mock_response.content = b"<html><body>test</body></html>"
    mock_session.get.return_value = mock_response

    fetcher = DetailFetcher(Config())
    result = fetcher._fetch_detail(12345678)

    assert result is not None
    mock_session.get.assert_called_once()


@patch("pubmedsoso.core.detail.requests.Session")
def test_fetch_details_batch(mock_session_cls, fixtures_dir):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    html = (fixtures_dir / "detail_page.html").read_bytes()
    mock_response = MagicMock()
    mock_response.content = html
    mock_session.get.return_value = mock_response

    fetcher = DetailFetcher(Config())
    articles = [
        Article(pmid=12345678, title="Test Article 1"),
        Article(pmid=23456789, title="Test Article 2"),
    ]

    fetcher.fetch_details(articles)

    assert articles[0].pmcid == "PMC9876543"
    assert articles[1].pmcid == "PMC9876543"
    assert mock_session.get.call_count == 2
