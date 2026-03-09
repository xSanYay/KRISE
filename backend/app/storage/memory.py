"""In-memory session storage for prototype."""

from __future__ import annotations
import uuid
from datetime import datetime

from app.models.session import Session, SessionMode

# Simple dict store — replace with Redis/PostgreSQL in production
_sessions: dict[str, Session] = {}


def create_session(language: str = "en", mode: SessionMode = SessionMode.STANDARD) -> Session:
    """Create a new session."""
    session_id = str(uuid.uuid4())
    session = Session(id=session_id, language=language, mode=mode)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    """Get a session by ID."""
    return _sessions.get(session_id)


def update_session(session: Session) -> Session:
    """Update a session in the store."""
    session.updated_at = datetime.utcnow()
    _sessions[session.id] = session
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def list_sessions() -> list[Session]:
    """List all active sessions (debug)."""
    return list(_sessions.values())
