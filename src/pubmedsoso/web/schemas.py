"""Pydantic models for API request/response schemas."""

from typing import Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    keyword: str
    page_num: int = 10


class DownloadRequest(BaseModel):
    task_id: str
    download_num: int = 10


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result_count: int = 0
    download_count: int = 0
    message: str = ""


class ArticleResponse(BaseModel):
    id: Optional[int] = None
    title: str = ""
    authors: str = ""
    journal: str = ""
    doi: str = ""
    pmid: Optional[int] = None
    pmcid: str = ""
    abstract: str = ""
    keywords: str = ""
    affiliations: str = ""
    free_status: int = 0
    is_review: bool = False
    save_path: str = ""

    class Config:
        from_attributes = True


class HistoryItem(BaseModel):
    task_id: str
    article_count: int
    created_at: str
