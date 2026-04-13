"""FastAPI web application for Pubmedsoso."""

from fastapi import FastAPI

app = FastAPI(
    title="Pubmedsoso",
    description="PubMed literature crawler web interface",
    version="2.0.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Pubmedsoso Web API", "version": "2.0.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
