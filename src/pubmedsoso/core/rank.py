"""Journal ranking via impact_factor library (local database)."""

import logging
import re

from impact_factor.core import Factor

from pubmedsoso.models import Article

logger = logging.getLogger(__name__)

_factor: Factor | None = None

_YEAR_SUFFIX_RE = re.compile(r"\s+\d{4}\s*$")


def _get_factor() -> Factor:
    global _factor
    if _factor is None:
        _factor = Factor()
    return _factor


def _strip_year(name: str) -> str:
    return _YEAR_SUFFIX_RE.sub("", name)


def _lookup(journal_name: str) -> dict | None:
    if not journal_name:
        return None

    fa = _get_factor()
    results = fa.search(journal_name)
    if not results:
        results = fa.search(_strip_year(journal_name))
    return results[0] if results else None


def rank_articles(articles: list[Article]) -> None:
    """Set impact_factor, jcr_quartile, cas_quartile for articles in-place."""
    logger.info("Ranking journals for %d articles", len(articles))

    for article in articles:
        if not article.journal:
            continue

        entry = _lookup(article.journal)
        if not entry:
            continue

        factor_val = entry.get("factor")
        if factor_val is not None:
            article.impact_factor = str(factor_val)

        jcr = entry.get("jcr")
        if jcr:
            article.jcr_quartile = jcr

        zky = entry.get("zky")
        if zky and zky != ".":
            article.cas_quartile = zky

    logger.info("Journal ranking complete")
