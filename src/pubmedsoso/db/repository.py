"""Article repository — CRUD operations for articles in SQLite."""

import logging
import sqlite3

from pubmedsoso.db.database import Database
from pubmedsoso.models import Article, FreeStatus

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Data access for Article objects in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        return Article(
            id=row["id"],
            title=row["title"],
            authors=row["authors"],
            journal=row["journal"],
            doi=row["doi"],
            pmid=row["pmid"],
            pmcid=row["pmcid"],
            abstract=row["abstract"],
            keywords=row["keywords"],
            affiliations=row["affiliations"],
            free_status=FreeStatus(row["free_status"]),
            is_review=bool(row["is_review"]),
            save_path=row["save_path"],
        )

    def insert_batch(self, articles: list[Article]) -> int:
        """Insert multiple articles. Returns count of inserted rows."""
        conn = self.db.get_connection()
        try:
            count = 0
            for article in articles:
                conn.execute(
                    """INSERT INTO articles
                       (title, authors, journal, doi, pmid, pmcid, abstract,
                        keywords, affiliations, free_status, is_review, save_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        article.title,
                        article.authors,
                        article.journal,
                        article.doi,
                        article.pmid,
                        article.pmcid,
                        article.abstract,
                        article.keywords,
                        article.affiliations,
                        int(article.free_status),
                        int(article.is_review),
                        article.save_path,
                    ),
                )
                count += 1
            conn.commit()
            return count
        except Exception:
            conn.rollback()
            logger.exception("Failed to insert batch of articles")
            raise
        finally:
            conn.close()

    def update_detail(self, article: Article) -> None:
        """Update detail fields (PMCID, abstract, keywords, affiliations) by PMID."""
        conn = self.db.get_connection()
        try:
            conn.execute(
                """UPDATE articles
                   SET pmcid = ?, abstract = ?, keywords = ?, affiliations = ?
                   WHERE pmid = ?""",
                (
                    article.pmcid,
                    article.abstract,
                    article.keywords,
                    article.affiliations,
                    article.pmid,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_save_path(self, pmcid: str, path: str) -> None:
        """Update PDF save path by PMCID."""
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE articles SET save_path = ? WHERE pmcid = ?",
                (path, pmcid),
            )
            conn.commit()
        finally:
            conn.close()

    def get_free_pmc_articles(self) -> list[Article]:
        """Get all articles with free_status = FREE_PMC."""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM articles WHERE free_status = ?",
                (int(FreeStatus.FREE_PMC),),
            )
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_articles(self) -> list[Article]:
        """Get all articles."""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM articles ORDER BY id")
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_by_pmids(self, pmids: list[int]) -> list[Article]:
        """Get articles by PMID list."""
        if not pmids:
            return []
        placeholders = ",".join("?" for _ in pmids)
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                f"SELECT * FROM articles WHERE pmid IN ({placeholders})",
                pmids,
            )
            return [self._row_to_article(row) for row in cursor.fetchall()]
        finally:
            conn.close()
