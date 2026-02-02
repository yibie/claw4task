"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claw4task.api.routes import router as api_router
from claw4task.api.web_routes import router as web_router
from claw4task.api.claim_routes import router as claim_router
from claw4task.core.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await db.init()
    yield
    # Shutdown
    await db.engine.dispose()


app = FastAPI(
    title="Claw4Task",
    description="AI Agent Task Marketplace - Let AI Agents work for each other",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(api_router)
app.include_router(web_router)
app.include_router(claim_router)

# Static files
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="claw4task/static"), name="static")

# Serve SKILL.md at root
from fastapi.responses import FileResponse, PlainTextResponse
import os

@app.get("/SKILL.md")
async def serve_skill():
    """Serve SKILL.md for easy copying."""
    skill_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "SKILL.md")
    return FileResponse(skill_path, media_type="text/markdown")


@app.get("/robots.txt", response_class=PlainTextResponse)
async def serve_robots():
    """Serve robots.txt for SEO."""
    robots_path = os.path.join(os.path.dirname(__file__), "static", "robots.txt")
    with open(robots_path, "r") as f:
        return f.read()


@app.get("/sitemap.xml", response_class=PlainTextResponse)
async def serve_sitemap():
    """Serve sitemap.xml for SEO."""
    sitemap_path = os.path.join(os.path.dirname(__file__), "static", "sitemap.xml")
    with open(sitemap_path, "r") as f:
        return f.read()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Claw4Task",
        "version": "0.1.0",
        "description": "AI Agent Task Marketplace",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
