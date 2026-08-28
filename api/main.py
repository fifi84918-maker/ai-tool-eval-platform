"""FastAPI application entry point."""

from fastapi import FastAPI
from api.routers import skills, eval

app = FastAPI(
    title="AI Skill Benchmark Platform",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.include_router(skills.router)
app.include_router(eval.router, prefix="/api/v1/eval", tags=["evaluation"])


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "AI Skill Benchmark Platform API",
        "version": "0.1.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
