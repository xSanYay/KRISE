"""WebSocket handler for real-time chat."""

from __future__ import annotations
import json
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from app.models.session import ConversationMessage, MessageRole, SwipeAction
from app.storage.memory import get_session, update_session
from app.agents.orchestrator import Orchestrator
from app.llm.bedrock import BedrockProvider

logger = structlog.get_logger()

_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(BedrockProvider())
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
