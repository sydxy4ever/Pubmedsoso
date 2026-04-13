"""Tests for journal ranking module."""

from unittest.mock import MagicMock, patch

import pytest

from pubmedsoso.core.rank import _strip_year, rank_articles
from pubmedsoso.models import Article


SAMPLE_ENTRY = {
    "journal_abbr": "Nature",
    "eissn": "1476-4687",
    "journal": "NATURE",
    "factor": 48.5,
    "nlm_id": "0410462",
    "jcr": "Q1",
    "issn": "0028-0836",
    "zky": "1 区",
}

SAMPLE_ENTRY_NO_ZKY = {
    "journal_abbr": "Some Journal",
    "eissn": "1234-5678",
    "journal": "SOME JOURNAL",
    "factor": 2.0,
    "nlm_id": "1234567",
    "jcr": "Q3",
    "issn": "0000-0000",
    "zky": ".",
}


class TestStripYear:
    def test_strip_year(self):
        assert _strip_year("Neurosci Lett 2024") == "Neurosci Lett"
        assert _strip_year("Nature 2023") == "Nature"
        assert _strip_year("Oncogene") == "Oncogene"
        assert _strip_year("J Med 2024") == "J Med"


class TestRankArticles:
    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_sets_three_fields(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_fa.search.side_effect = lambda name: (
            [SAMPLE_ENTRY]
            if name == "Nature"
            else [{"journal_abbr": "Oncogene", "factor": 7.3, "jcr": "Q1", "zky": "1 区"}]
        )
        mock_get_factor.return_value = mock_fa

        articles = [
            Article(journal="Nature"),
            Article(journal="Oncogene"),
            Article(journal="Nature"),
        ]

        rank_articles(articles)

        assert articles[0].impact_factor == "48.5"
        assert articles[0].jcr_quartile == "Q1"
        assert articles[0].cas_quartile == "1 区"
        assert articles[1].impact_factor == "7.3"
        assert articles[1].jcr_quartile == "Q1"
        assert articles[2].impact_factor == articles[0].impact_factor

    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_empty_journal(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_get_factor.return_value = mock_fa

        articles = [Article(journal="")]
        rank_articles(articles)
        assert articles[0].impact_factor == ""
        assert articles[0].jcr_quartile == ""
        assert articles[0].cas_quartile == ""
        mock_fa.search.assert_not_called()

    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_no_journal(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_get_factor.return_value = mock_fa

        articles = [Article()]
        rank_articles(articles)
        assert articles[0].impact_factor == ""

    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_dot_zky_skipped(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_fa.search.return_value = [SAMPLE_ENTRY_NO_ZKY]
        mock_get_factor.return_value = mock_fa

        articles = [Article(journal="Some Journal")]
        rank_articles(articles)
        assert articles[0].impact_factor == "2.0"
        assert articles[0].jcr_quartile == "Q3"
        assert articles[0].cas_quartile == ""

    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_strips_year(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_fa.search.side_effect = lambda name: [SAMPLE_ENTRY] if name == "Nature" else []
        mock_get_factor.return_value = mock_fa

        articles = [Article(journal="Nature 2024")]
        rank_articles(articles)
        assert articles[0].impact_factor == "48.5"

    @patch("pubmedsoso.core.rank._get_factor")
    def test_rank_articles_no_result(self, mock_get_factor):
        mock_fa = MagicMock()
        mock_fa.search.return_value = []
        mock_get_factor.return_value = mock_fa

        articles = [Article(journal="UnknownJournal")]
        rank_articles(articles)
        assert articles[0].impact_factor == ""
        assert articles[0].jcr_quartile == ""
        assert articles[0].cas_quartile == ""
