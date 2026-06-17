"""
WebSocket Endpoint.

ws://host/api/v1/ws/{user_id}?token=<JWT>

Lifecycle:
1. Client connects with JWT token as query param
2. Server validates token and registers connection
3. Server marks user as online in Redis
4. Messages are processed in a loop
5. On disconnect: mark offline, clean up connection

Message Protocol (JSON):
  Client → Server:
    { "event": "ping" }
    { "event": "matchmaking_join" }
    { "event": "matchmaking_leave" }
    { "event": "chat", "message": "hello" }

  Server → Client:
    { "event": "pong" }
    { "event": "match_found", "match_id": 123, "opponent_id": "456" }
    { "event": "error", "detail": "..." }
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.redis import redis_manager
from app.models.user import User
from app.websockets.manager import ws_manager

router = APIRouter()


async def get_user_from_token(token: str) -> User:
    """
    Validate JWT and return the User object.
    Used for WebSocket authentication (can't use standard HTTP Bearer here).
    """
    try:
        token_data = decode_token(token)
    except HTTPException:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == int(token_data.user_id))
        )
        return result.scalar_one_or_none()


@router.websocket("/battle")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
):
    """
    Main WebSocket endpoint for real-time communication.

    Authentication: Pass your JWT as ?token=<your_access_token>
    Example: ws://localhost:8000/api/v1/ws/battle?token=eyJ...
    """

    # ── Authentication ────────────────────────────────────────────────────────
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = str(user.id)

    # ── Connect ───────────────────────────────────────────────────────────────
    await ws_manager.connect(websocket, user_id)
    await redis_manager.add_online_user(user_id)

    # Notify the client they're connected
    await ws_manager.send_to_user(
        user_id,
        {
            "event": "connected",
            "user_id": user_id,
            "username": user.username,
            "rating": user.rating,
            "online_count": ws_manager.get_connected_count(),
        },
    )

    try:
        # ── Message Loop ──────────────────────────────────────────────────────
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_to_user(user_id, {"event": "error", "detail": "Invalid JSON"})
                continue

            event = data.get("event")

            if event == "ping":
                # Simple heartbeat — client pings, server pongs
                await ws_manager.send_to_user(user_id, {"event": "pong"})

            elif event == "matchmaking_join":
                # Trigger matchmaking via the service
                from app.services.matchmaking import MatchmakingService
                service = MatchmakingService(redis_manager)
                result = await service.join_queue(user)
                await ws_manager.send_to_user(user_id, {"event": "matchmaking_status", **result})

            elif event == "matchmaking_leave":
                await redis_manager.remove_from_matchmaking_queue(user_id)
                await ws_manager.send_to_user(user_id, {"event": "matchmaking_left"})

            elif event == "chat":
                # Broadcast a chat message — in Phase 2, restrict to match room
                message = data.get("message", "")[:500]  # limit to 500 chars
                await ws_manager.broadcast(
                    {"event": "chat", "from": user.username, "message": message},
                    exclude_user_id=None,
                )

            else:
                await ws_manager.send_to_user(
                    user_id,
                    {"event": "error", "detail": f"Unknown event: {event!r}"},
                )

    except WebSocketDisconnect:
        pass  # Client disconnected normally

    except Exception as e:
        print(f"⚠️ WebSocket error for user {user_id}: {e}")

    finally:
        # ── Disconnect Cleanup ────────────────────────────────────────────────
        ws_manager.disconnect(user_id)
        await redis_manager.remove_online_user(user_id)
        await redis_manager.remove_from_matchmaking_queue(user_id)
        print(f"🧹 Cleaned up connection for user {user_id}")
