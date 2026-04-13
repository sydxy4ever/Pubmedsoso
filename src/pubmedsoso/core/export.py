import csv
from pathlib import Path

from openpyxl import Workbook

from pubmedsoso.models import Article, FreeStatus

COLUMNS = (
    "序号",
    "文献标题",
    "作者名单",
    "期刊年份",
    "doi",
    "PMID",
    "PMCID",
    "摘要",
    "关键词",
    "作者单位",
    "是否有免费全文",
    "是否是review",
    "保存路径",
)


def _article_to_row(article: Article, index: int) -> list[str]:
    free_display = "是" if article.free_status == FreeStatus.FREE_PMC else "否"
    review_display = "是" if article.is_review else "否"
    return [
        str(index),
        article.title,
        article.authors,
        article.journal,
        article.doi,
        str(article.pmid) if article.pmid else "",
        article.pmcid,
        article.abstract,
        article.keywords,
        article.affiliations,
        free_display,
        review_display,
        article.save_path,
    ]


class Exporter:
    @staticmethod
    def to_xlsx(articles: list[Article], path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.append(list(COLUMNS))
        for idx, article in enumerate(articles, 1):
            ws.append(_article_to_row(article, idx))
        wb.save(path)
        wb.close()
        return path

    @staticmethod
    def to_csv(articles: list[Article], path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(list(COLUMNS))
            for idx, article in enumerate(articles, 1):
                writer.writerow(_article_to_row(article, idx))
        return path
