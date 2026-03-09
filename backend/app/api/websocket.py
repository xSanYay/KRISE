"""WebSocket handler for real-time chat."""

from __future__ import annotations
import json
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from app.models.session import ConversationMessage, MessageRole, SwipeAction
from app.storage.memory import get_session, update_session
from app.agents.orchestrator import Orchestrator
from app.config import get_settings

logger = structlog.get_logger()

_orchestrator: Orchestrator | None = None


def _make_llm():
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "auto":
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            provider = "bedrock"
        elif settings.gemini_api_key:
            provider = "gemini"
        elif settings.anthropic_api_key:
            provider = "anthropic"
        else:
            raise RuntimeError(
                "No LLM provider credentials are configured. Set AWS, GEMINI_API_KEY, or ANTHROPIC_API_KEY in the backend environment."
            )

    if provider == "bedrock":
        if not (settings.aws_access_key_id and settings.aws_secret_access_key):
            raise RuntimeError("Bedrock is selected but AWS credentials are missing.")
        from app.llm.bedrock import BedrockProvider
        return BedrockProvider()
    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini is selected but GEMINI_API_KEY is missing.")
        from app.llm.gemini import GeminiProvider
        return GeminiProvider()
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Anthropic is selected but ANTHROPIC_API_KEY is missing.")
        from app.llm.anthropic import AnthropicProvider
        return AnthropicProvider()

    raise RuntimeError(f"Unsupported llm_provider: {settings.llm_provider}")


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(_make_llm())
    return _orchestrator


async def websocket_handler(websocket: WebSocket, session_id: str):
    """Handle WebSocket connection for a session."""
    await websocket.accept()

    session = get_session(session_id)
    if not session:
        await websocket.send_json({"type": "error", "content": "Session not found"})
        await websocket.close()
        return

    logger.info("ws_connected", session_id=session_id)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type", "message")

            if msg_type == "message":
                # Send typing indicator
                await websocket.send_json({"type": "typing", "content": ""})

                orchestrator = _get_orchestrator()
                response = await orchestrator.process_message(
                    payload.get("content", ""), session
                )
                update_session(session)

                await websocket.send_json(response.model_dump())

            elif msg_type == "swipe":
                orchestrator = _get_orchestrator()
                swipe = SwipeAction(
                    product_id=payload.get("product_id", ""),
                    direction=payload.get("direction", "left"),
                    reason=payload.get("reason"),
                )
                response = await orchestrator.handle_swipe(session, swipe)
                update_session(session)

                await websocket.send_json({
                    "type": "swipe_result",
                    **response.model_dump(),
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("ws_error", session_id=session_id, error=str(e))
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
