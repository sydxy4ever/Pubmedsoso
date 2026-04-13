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

from pubmedsoso.config import Config
from pubmedsoso.core.detail import DetailFetcher
from pubmedsoso.core.download import DownloadManager
from pubmedsoso.core.export import Exporter
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import Article, SearchParams
from pubmedsoso.web.schemas import (
    ArticleResponse,
    DownloadRequest,
    HistoryItem,
    SearchRequest,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_tasks: dict[str, TaskStatus] = {}
_task_articles: dict[str, list[Article]] = {}
_task_dbs: dict[str, Database] = {}
_task_timestamps: dict[str, datetime] = {}
_state_lock = threading.Lock()

_MAX_TASK_AGE = timedelta(hours=1)


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


def _run_search(task_id: str, request: SearchRequest, config: Config) -> None:
    try:
        _update_task(task_id, status="running", message="Searching PubMed...")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        db_path = config.db_dir / f"pubmed_{timestamp}.db"
        db = Database(db_path)
        db.init_schema()
        with _state_lock:
            _task_dbs[task_id] = db
        repo = ArticleRepository(db)

        searcher = PubMedSearcher(config)
        params = SearchParams(
            keyword=request.keyword,
            page_num=request.page_num,
            page_size=config.page_size,
        )
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
        repo.insert_batch(result.articles)
        _update_task(task_id, progress=0.4)

        _update_task(task_id, message="Fetching article details...")
        fetcher = DetailFetcher(config)
        fetcher.fetch_details(result.articles)
        for article in result.articles:
            if article.pmid:
                repo.update_detail(article)

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


def _run_download(task_id: str, download_num: int, config: Config) -> None:
    try:
        _update_task(task_id, status="downloading", message="Downloading PDFs...")

        articles = _task_articles.get(task_id, [])
        if not articles:
            db = _task_dbs.get(task_id)
            if db:
                repo = ArticleRepository(db)
                articles = repo.get_all_articles()

        if not articles:
            _update_task(task_id, status="failed", message="No articles found for download")
            return

        downloader = DownloadManager(config)
        results = downloader.download_batch(articles, limit=download_num)
        downloaded = sum(1 for _, p in results if p is not None)

        db = _task_dbs.get(task_id)
        if db:
            repo = ArticleRepository(db)
            for article, path in results:
                if path and article.pmcid:
                    repo.update_save_path(article.pmcid, str(path))
            with _state_lock:
                _task_articles[task_id] = repo.get_all_articles()

        _update_task(
            task_id,
            status="completed",
            message=f"Downloaded {downloaded} PDFs",
            download_count=downloaded,
            progress=1.0,
        )

    except Exception as e:
        logger.exception("Download task failed")
        _update_task(task_id, status="failed", message=str(e))


@router.post("/search")
async def start_search(request: SearchRequest) -> dict[str, str]:
    task_id = str(uuid.uuid4())[:8]
    with _state_lock:
        _tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="pending",
            message="Task created",
        )
        _task_timestamps[task_id] = datetime.now()

    config = Config.from_env()
    config.ensure_dirs()

    _cleanup_old_tasks()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_search, task_id, request, config)

    return {"task_id": task_id}


@router.post("/download")
async def start_download(request: DownloadRequest) -> dict[str, str]:
    task_id = request.task_id
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    if _tasks[task_id].status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task is still running")

    with _state_lock:
        _tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="pending",
            message="Download starting...",
        )

    config = Config.from_env()
    config.ensure_dirs()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run_download, task_id, request.download_num, config)

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> TaskStatus:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.get("/articles")
async def get_articles(
    task_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    if task_id and task_id in _task_articles:
        articles = _task_articles[task_id]
    elif task_id and task_id in _task_dbs:
        repo = ArticleRepository(_task_dbs[task_id])
        articles = repo.get_all_articles()
    else:
        config = Config.from_env()
        db_files = list(config.db_dir.glob("pubmed_*.db"))
        if not db_files:
            return {"articles": [], "total": 0, "page": page, "page_size": page_size}
        latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
        db = Database(latest_db)
        repo = ArticleRepository(db)
        articles = repo.get_all_articles()

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
    db_files = list(config.db_dir.glob("pubmed_*.db"))

    history: list[HistoryItem] = []
    for db_file in sorted(db_files, reverse=True):
        timestamp = db_file.stem.replace("pubmed_", "")
        db = Database(db_file)
        repo = ArticleRepository(db)
        articles = repo.get_all_articles()

        created_at = datetime.fromtimestamp(db_file.stat().st_mtime).isoformat()

        history.append(
            HistoryItem(
                task_id=timestamp,
                article_count=len(articles),
                created_at=created_at,
            )
        )

    return history
