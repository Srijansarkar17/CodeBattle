"""
WebSocket Connection Manager.

Tracks all active WebSocket connections and provides utilities
for sending messages to specific users or broadcasting to all.

Architecture:
- Each user can have ONE active WebSocket connection
- Connections are stored in memory (dict: user_id → WebSocket)
- When a user connects, their old connection is replaced
- On disconnect, the entry is removed
"""

import json
from typing import Dict, Optional, Any
from fastapi import WebSocket


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Maps user_id (str) → WebSocket connection object.
    All send operations are non-blocking (fire and forget with error handling).
    """

    def __init__(self):
        # Active connections: user_id → WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Accept a new WebSocket connection and register it.

        If the user already has a connection (e.g., opened another tab),
        we close the old one and register the new one.
        """
        await websocket.accept()

        # Close existing connection if any
        if user_id in self.active_connections:
            old_ws = self.active_connections[user_id]
            try:
                await old_ws.close(code=1000, reason="New connection established")
            except Exception:
                pass  # Already closed

        self.active_connections[user_id] = websocket
        print(f"✅ WebSocket connected: user_id={user_id} (total: {len(self.active_connections)})")

    def disconnect(self, user_id: str) -> None:
        """
        Remove a user's WebSocket connection from the registry.
        Called when the client disconnects or an error occurs.
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"❌ WebSocket disconnected: user_id={user_id} (total: {len(self.active_connections)})")

    async def send_to_user(self, user_id: str, data: Any) -> bool:
        """
        Send a JSON message to a specific user.

        Returns:
            True if the message was sent, False if the user is not connected.
        """
        websocket = self.active_connections.get(user_id)
        if not websocket:
            return False  # User not currently connected

        try:
            if isinstance(data, dict):
                await websocket.send_json(data)
            else:
                await websocket.send_text(str(data))
            return True
        except Exception as e:
            print(f"⚠️ Failed to send to user {user_id}: {e}")
            self.disconnect(user_id)
            return False

    async def broadcast(self, data: Any, exclude_user_id: Optional[str] = None) -> None:
        """
        Send a message to ALL connected users.

        Args:
            data: Message payload (will be JSON-serialized if dict)
            exclude_user_id: Optionally skip one specific user (e.g., the sender)
        """
        disconnected = []
        for uid, websocket in self.active_connections.items():
            if uid == exclude_user_id:
                continue
            try:
                if isinstance(data, dict):
                    await websocket.send_json(data)
                else:
                    await websocket.send_text(str(data))
            except Exception:
                disconnected.append(uid)

        # Clean up any dead connections discovered during broadcast
        for uid in disconnected:
            self.disconnect(uid)

    def get_connected_count(self) -> int:
        """Return total number of currently connected users."""
        return len(self.active_connections)

    def is_connected(self, user_id: str) -> bool:
        """Check if a specific user has an active WebSocket connection."""
        return user_id in self.active_connections


# ── Singleton Instance ────────────────────────────────────────────────────────
ws_manager = ConnectionManager()
