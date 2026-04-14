"""Pydantic models for API request/response schemas."""

from typing import Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    keyword: str


class SearchConfirmRequest(BaseModel):
    task_id: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result_count: int = 0
    message: str = ""
    search_id: Optional[int] = None


class ArticleResponse(BaseModel):
    id: Optional[int] = None
    title: str = ""
    authors: str = ""
    journal: str = ""
    pub_year: str = ""
    impact_factor: str = ""
    jcr_quartile: str = ""
    cas_quartile: str = ""
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
    search_id: int
    keyword: str
    article_count: int
    created_at: str
