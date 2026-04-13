"""CLI entry point for Pubmedsoso."""

import logging
from datetime import datetime
from typing import Optional

import typer

from pubmedsoso import __version__
from pubmedsoso.config import Config
from pubmedsoso.core.export import Exporter
from pubmedsoso.core.rank import rank_articles
from pubmedsoso.core.search import PubMedSearcher
from pubmedsoso.db.database import Database
from pubmedsoso.db.repository import ArticleRepository
from pubmedsoso.models import SearchParams

app = typer.Typer(
    name="pubmedsoso",
    help="PubMed literature crawler - search, extract, export",
    add_completion=False,
)


def _get_db(config: Config) -> Database:
    db_path = config.db_dir / "pubmedsoso.db"
    db = Database(db_path)
    db.init_schema()
    return db


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pubmedsoso {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    pass


@app.command()
def search(
    keyword: str = typer.Argument(..., help="Search keyword"),
    format: str = typer.Option("xlsx", "-f", "--format", help="Export format: xlsx or csv"),
) -> None:
    """Search PubMed (fetches ALL results) and export."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    config = Config.from_env()
    config.ensure_dirs()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    db_path = config.db_dir / "pubmedsoso.db"
    ext = "xlsx" if format == "xlsx" else "csv"
    export_path = config.export_dir / f"pubmed_{timestamp}.{ext}"

    typer.echo(f"Initializing database: {db_path}")
    db = Database(db_path)
    db.init_schema()
    search_id = db.create_search(keyword, datetime.now().isoformat())
    repo = ArticleRepository(db)

    typer.echo(f"Searching for: {keyword}")
    searcher = PubMedSearcher(config)
    params = SearchParams(keyword=keyword)
    result = searcher.search(params)

    typer.echo(f"Found {result.total_count} articles, fetched {len(result.articles)} entries")

    if not result.articles:
        typer.echo("No articles found, exiting.")
        return

    typer.echo("Saving search results to database...")
    repo.insert_batch(result.articles, search_id=search_id)

    typer.echo("Ranking journals...")
    rank_articles(result.articles)
    for article in result.articles:
        if article.pmid and (article.impact_factor or article.jcr_quartile or article.cas_quartile):
            repo.update_rank_fields(article.pmid, article)

    typer.echo(f"Exporting results to {export_path}...")
    if format == "xlsx":
        Exporter.to_xlsx(result.articles, export_path)
    else:
        Exporter.to_csv(result.articles, export_path)

    typer.echo(f"Done! Database: {db_path}, Export: {export_path}")


@app.command()
def export(
    list_tables: bool = typer.Option(False, "--list", "-l", help="List available searches"),
    search_id: Optional[int] = typer.Option(None, "--search-id", "-s", help="Search ID to export"),
    format: str = typer.Option("xlsx", "-f", "--format", help="Export format: xlsx or csv"),
) -> None:
    """Export historical search results."""
    config = Config.from_env()

    if list_tables or search_id is None:
        typer.echo("Available searches:")
        db = _get_db(config)
        searches = db.get_searches()
        if not searches:
            typer.echo("  No searches found.")
            return
        for s in searches:
            typer.echo(f"  [{s['id']}] {s['keyword']} ({s['created_at']})")
        return

    db = _get_db(config)
    repo = ArticleRepository(db)
    articles = repo.get_all_articles(search_id=search_id)

    if not articles:
        typer.echo("No articles found for this search.")
        return

    searches = db.get_searches()
    target = next((s for s in searches if s["id"] == search_id), None)
    timestamp = (
        target["created_at"]
        .replace(":", "")
        .replace("-", "")
        .replace("T", "")
        .replace("+", "")[:14]
        if target
        else str(search_id)
    )
    ext = "xlsx" if format == "xlsx" else "csv"
    export_path = config.export_dir / f"pubmed_export_{timestamp}.{ext}"

    typer.echo(f"Exporting {len(articles)} articles to {export_path}...")
    if format == "xlsx":
        Exporter.to_xlsx(articles, export_path)
    else:
        Exporter.to_csv(articles, export_path)

    typer.echo(f"Done! Export: {export_path}")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
) -> None:
    """Start the web UI."""
    import uvicorn

    typer.echo(f"Starting web server at http://{host}:{port}")
    uvicorn.run("pubmedsoso.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
