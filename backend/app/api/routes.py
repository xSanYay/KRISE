"""REST API routes."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.models.api import (
    CreateSessionRequest,
    SendMessageRequest,
    SwipeRequest,
    SessionResponse,
    MessageResponse,
    SwipeResponse,
    HealthResponse,
)
from app.models.session import SwipeAction
from app.storage.memory import create_session, get_session, update_session
from app.agents.orchestrator import Orchestrator
from app.llm.bedrock import BedrockProvider

router = APIRouter(prefix="/api/v1")

# Lazy init — created on first use
_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(BedrockProvider())
    return _orchestrator


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@router.post("/sessions", response_model=SessionResponse)
async def create_new_session(req: CreateSessionRequest):
    """Start a new conversation session."""
    session = create_session(language=req.language)
    return SessionResponse(
        session_id=session.id,
        status="active",
        phase=session.phase.value,
    )


@router.post("/sessions/{session_id}/message", response_model=MessageResponse)
async def send_message(session_id: str, req: SendMessageRequest):
    """Send a message to the agent."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = _get_orchestrator()
    response = await orchestrator.process_message(req.content, session)

    update_session(session)
    return response


@router.get("/sessions/{session_id}/profile")
async def get_intent_profile(session_id: str):
    """Get the current intent profile for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "phase": session.phase.value,
        "intent_profile": session.intent_profile.model_dump(),
        "conviction_score": session.intent_profile.conviction_score,
        "socratic_turns": session.socratic_turn_count,
    }


@router.post("/sessions/{session_id}/swipe", response_model=SwipeResponse)
async def handle_swipe(session_id: str, req: SwipeRequest):
    """Process a swipe action and get updated recommendations."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = _get_orchestrator()
    swipe = SwipeAction(
        product_id=req.product_id,
        direction=req.direction,
        reason=req.reason,
    )

    response = await orchestrator.handle_swipe(session, swipe)
    update_session(session)
    return response


@router.get("/sessions/{session_id}/products")
async def get_products(session_id: str):
    """Get current product deck for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "products": [ps.model_dump() for ps in session.product_deck],
        "shortlist": session.shortlist,
        "total": len(session.product_deck),
    }
