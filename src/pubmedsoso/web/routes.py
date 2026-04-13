"""FastAPI routes for PubMed search API."""

import asyncio
import logging
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from deep_translator import GoogleTranslator

from pubmedsoso.config import Config
from pubmedsoso.core.export import Exporter
from pubmedsoso.core.rank import rank_articles
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import Article, SearchParams
from pubmedsoso.web.schemas import (
    ArticleResponse,
    HistoryItem,
    SearchConfirmRequest,
    SearchRequest,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_tasks: dict[str, TaskStatus] = {}
_task_articles: dict[str, list[Article]] = {}
_task_timestamps: dict[str, datetime] = {}
_task_keywords: dict[str, str] = {}
_state_lock = threading.Lock()

_MAX_TASK_AGE = timedelta(hours=1)
_LARGE_RESULT_THRESHOLD = 500


def _cleanup_old_tasks() -> None:
    now = datetime.now()
    expired = [tid for tid, ts in _task_timestamps.items() if now - ts > _MAX_TASK_AGE]
    for tid in expired:
        _tasks.pop(tid, None)
        _task_articles.pop(tid, None)
        db = _task_dbs.pop(tid, None)
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
        _task_timestamps.pop(tid, None)


def _update_task(task_id: str, **kwargs: object) -> None:
    with _state_lock:
        for key, value in kwargs.items():
            setattr(_tasks[task_id], key, value)


def _run_search_count(task_id: str, keyword: str, config: Config) -> None:
    try:
        _update_task(task_id, status="running", message="Counting results...")

        searcher = PubMedSearcher(config)
        total_count, _ = searcher._esearch(keyword)

        _update_task(
            task_id,
            status="confirm" if total_count > _LARGE_RESULT_THRESHOLD else "counted",
            result_count=total_count,
            message=f"Found {total_count} results",
        )

    except Exception as e:
        logger.exception("Search count failed")
        _update_task(task_id, status="failed", message=str(e))


def _get_db(config: Config) -> Database:
    db_path = config.db_dir / "pubmedsoso.db"
    db = Database(db_path)
    db.init_schema()
    return db


def _run_search_full(task_id: str, keyword: str, config: Config) -> None:
    try:
        _update_task(task_id, status="running", message="Searching PubMed...")

        db = _get_db(config)
        with _state_lock:
            _task_dbs[task_id] = db

        search_id = db.create_search(keyword, datetime.now().isoformat())
        repo = ArticleRepository(db)

        searcher = PubMedSearcher(config)
        params = SearchParams(keyword=keyword)
        result = searcher.search(params)

        _update_task(
            task_id,
            progress=0.3,
            result_count=len(result.articles),
            message=f"Found {result.total_count} articles, fetching details...",
        )

        if not result.articles:
            _update_task(task_id, status="completed", message="No articles found")
            return

        _update_task(task_id, message="Saving to database...")
        repo.insert_batch(result.articles, search_id=search_id)
        _update_task(task_id, progress=0.5)

        _update_task(task_id, message="Ranking journals...")
        rank_articles(result.articles)
        for article in result.articles:
            if article.pmid and (
                article.impact_factor or article.jcr_quartile or article.cas_quartile
            ):
                repo.update_rank_fields(article.pmid, article)
        _update_task(task_id, progress=0.7)

        with _state_lock:
            _task_articles[task_id] = result.articles
        _update_task(
            task_id,
            status="completed",
            message=f"Found {result.total_count} results, {len(result.articles)} articles fetched",
            progress=1.0,
        )

    except Exception as e:
        logger.exception("Search task failed")
        _update_task(task_id, status="failed", message=str(e))


@router.post("/search")
async def start_search(request: SearchRequest) -> dict:
    task_id = str(uuid.uuid4())[:8]
    with _state_lock:
        _tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="pending",
            message="Task created",
        )
        _task_timestamps[task_id] = datetime.now()
        _task_keywords[task_id] = request.keyword

    config = Config.from_env()
    config.ensure_dirs()

    _cleanup_old_tasks()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_search_count, task_id, request.keyword, config)

    return {"task_id": task_id}


@router.post("/search/confirm")
async def confirm_search(request: SearchConfirmRequest) -> dict[str, str]:
    task_id = request.task_id
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
    if task.status not in ("confirm", "counted"):
        raise HTTPException(status_code=400, detail=f"Task status is {task.status}, cannot confirm")

    keyword = _task_keywords.get(task_id, "")
    if not keyword:
        raise HTTPException(status_code=400, detail="No keyword found for task")

    _update_task(task_id, status="running", message="Fetching all results...")

    config = Config.from_env()
    config.ensure_dirs()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_search_full, task_id, keyword, config)

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> TaskStatus:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.get("/articles")
async def get_articles(
    task_id: Optional[str] = Query(None),
    search_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100000),
) -> dict:
    if task_id and task_id in _task_articles:
        articles = _task_articles[task_id]
    else:
        config = Config.from_env()
        db = _get_db(config)
        repo = ArticleRepository(db)
        articles = repo.get_all_articles(search_id=search_id)

    start = (page - 1) * page_size
    end = start + page_size
    paginated = articles[start:end]

    return {
        "articles": [
            ArticleResponse(
                id=a.id,
                title=a.title,
                authors=a.authors,
                journal=a.journal,
                pub_year=a.pub_year,
                impact_factor=a.impact_factor,
                jcr_quartile=a.jcr_quartile,
                cas_quartile=a.cas_quartile,
                doi=a.doi,
                pmid=a.pmid,
                pmcid=a.pmcid,
                abstract=a.abstract,
                keywords=a.keywords,
                affiliations=a.affiliations,
                free_status=int(a.free_status),
                is_review=a.is_review,
                save_path=a.save_path,
            )
            for a in paginated
        ],
        "total": len(articles),
        "page": page,
        "page_size": page_size,
    }


@router.get("/export")
async def export_results(
    task_id: Optional[str] = Query(None),
    export_format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
):
    if task_id and task_id in _task_articles:
        articles = _task_articles[task_id]
    elif task_id and task_id in _task_dbs:
        repo = ArticleRepository(_task_dbs[task_id])
        articles = repo.get_all_articles()
    else:
        config = Config.from_env()
        db_files = list(config.db_dir.glob("pubmed_*.db"))
        if not db_files:
            raise HTTPException(status_code=404, detail="No articles found")
        latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
        db = Database(latest_db)
        repo = ArticleRepository(db)
        articles = repo.get_all_articles()

    if not articles:
        raise HTTPException(status_code=404, detail="No articles to export")

    buffer = BytesIO()
    suffix = ".xlsx" if export_format == "xlsx" else ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        temp_path = Path(tmp.name)

    if export_format == "xlsx":
        Exporter.to_xlsx(articles, temp_path)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"pubmed_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    else:
        Exporter.to_csv(articles, temp_path)
        media_type = "text/csv"
        filename = f"pubmed_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"

    with open(temp_path, "rb") as f:
        buffer.write(f.read())
    buffer.seek(0)
    temp_path.unlink()

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/history")
async def get_history() -> list[HistoryItem]:
    config = Config.from_env()
    db = _get_db(config)
    repo = ArticleRepository(db)

    history: list[HistoryItem] = []
    for search in db.get_searches():
        articles = repo.get_all_articles(search_id=search["id"])
        history.append(
            HistoryItem(
                task_id=search["keyword"],
                article_count=len(articles),
                created_at=search["created_at"],
            )
        )

    return history


@router.get("/translate")
async def translate_text(text: str = Query(..., min_length=1)) -> dict:
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, lambda: GoogleTranslator(source="en", target="zh-CN").translate(text)
        )
        return {"translated": result}
    except Exception as e:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=str(e))
