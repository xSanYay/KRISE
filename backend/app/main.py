"""Krise Engine — FastAPI Application Entry Point."""

from __future__ import annotations
from contextlib import asynccontextmanager
import structlog

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.websocket import websocket_handler
from app.scraping.browser import browser_manager

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("krise_engine_starting")
    logger.info("krise_engine_ready")
    yield
    logger.info("krise_engine_stopping")
    await browser_manager.stop()
    logger.info("krise_engine_stopped")


settings = get_settings()

app = FastAPI(
    title="Krise Engine",
    description="Multi-Agent Intent Orchestrator for AI Commerce",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_allow_origins(),
    allow_origin_regex=settings.cors_allow_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(api_router)


# WebSocket endpoint
@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket_handler(websocket, session_id)
