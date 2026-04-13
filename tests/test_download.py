from unittest.mock import MagicMock, patch

from pubmedsoso.config import Config
from pubmedsoso.models import Article, FreeStatus


def test_pmc_downloader_builds_correct_url():
    from pubmedsoso.core.download import PMCDownloader

    config = Config()
    downloader = PMCDownloader(config)

    article = Article(pmcid="PMC12345", title="Test Article")
    url = downloader._build_pdf_url(article)

    assert "PMC12345" in url
    assert "pdf" in url
    assert "ncbi.nlm.nih.gov" in url


@patch("pubmedsoso.core.download.requests.Session")
def test_pmc_downloader_success(mock_session_cls, tmp_path):
    from pubmedsoso.core.download import PMCDownloader

    config = Config(download_dir=tmp_path)
    downloader = PMCDownloader(config)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_response

    article = Article(pmcid="PMC12345", title="Test Article")
    result = downloader.download(article)

    assert result is not None
    assert result.suffix == ".pdf"
    mock_session.get.assert_called_once()


@patch("pubmedsoso.core.download.requests.Session")
def test_pmc_downloader_timeout(mock_session_cls, tmp_path):
    from pubmedsoso.core.download import PMCDownloader
    import requests

    config = Config(download_dir=tmp_path)
    downloader = PMCDownloader(config)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_session.get.side_effect = requests.Timeout("Connection timed out")

    article = Article(pmcid="PMC12345", title="Test Article")
    result = downloader.download(article)

    assert result is None


def test_scihub_downloader_disabled():
    from pubmedsoso.core.download import SciHubDownloader

    config = Config(scihub_enabled=False)
    downloader = SciHubDownloader(config)

    article = Article(doi="10.1234/test.2024.123", title="Test Article")
    result = downloader.download(article)

    assert result is None


@patch("pubmedsoso.core.download.requests.Session")
def test_download_manager_pmc_first(mock_session_cls, tmp_path):
    from pubmedsoso.core.download import DownloadManager

    config = Config(download_dir=tmp_path)
    manager = DownloadManager(config)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_response

    article = Article(
        pmcid="PMC12345",
        doi="10.1234/test.2024.123",
        title="Test Article",
        free_status=FreeStatus.FREE_PMC,
    )
    result = manager.download(article)

    assert result is not None
    assert "PMC12345" in mock_session.get.call_args[0][0]


@patch("pubmedsoso.core.download.requests.Session")
def test_download_manager_falls_back_to_scihub(mock_session_cls, tmp_path):
    from pubmedsoso.core.download import DownloadManager

    config = Config(download_dir=tmp_path, scihub_enabled=True)
    manager = DownloadManager(config)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    call_count = [0]

    def mock_get(url, *args, **kwargs):
        call_count[0] += 1
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        if call_count[0] == 1:
            mock_response.content = (
                b'<html><iframe id="pdf" src="https://example.com/paper.pdf"></iframe></html>'
            )
            mock_response.text = (
                '<html><iframe id="pdf" src="https://example.com/paper.pdf"></iframe></html>'
            )
        else:
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.text = ""

        return mock_response

    mock_session.get.side_effect = mock_get

    article = Article(
        pmcid="",
        doi="10.1234/test.2024.123",
        title="Test Article",
        free_status=FreeStatus.NOT_FREE,
    )
    manager.download(article)

    assert call_count[0] >= 2


def test_sanitize_filename():
    from pubmedsoso.core.download import PMCDownloader

    config = Config()
    downloader = PMCDownloader(config)

    result = downloader._sanitize_filename('Test/Article: With "Invalid" Chars?')
    assert "/" not in result
    assert ":" not in result
    assert '"' not in result
    assert "?" not in result


@patch("pubmedsoso.core.download.requests.Session")
def test_download_batch_with_limit(mock_session_cls, tmp_path):
    from pubmedsoso.core.download import DownloadManager

    config = Config(download_dir=tmp_path)
    manager = DownloadManager(config)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_response

    articles = [
        Article(pmcid=f"PMC{i}", title=f"Article {i}", free_status=FreeStatus.FREE_PMC)
        for i in range(5)
    ]

    results = manager.download_batch(articles, limit=3)

    assert len(results) == 3


def test_extract_pdf_url_from_html():
    from pubmedsoso.core.download import SciHubDownloader

    config = Config()
    downloader = SciHubDownloader(config)

    html = '<html><iframe id="pdf" src="https://example.com/paper.pdf"></iframe></html>'
    url = downloader._extract_pdf_url(html)
    assert url == "https://example.com/paper.pdf"

    html2 = '<html><embed src="https://other.com/doc.pdf" type="application/pdf"></embed></html>'
    url2 = downloader._extract_pdf_url(html2)
    assert url2 == "https://other.com/doc.pdf"
