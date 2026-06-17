"""
Matchmaking Service.

Business logic for pairing players in the queue.
Separated from the API layer so it can also be called from WebSocket handlers.
"""

from typing import Optional
from app.core.config import settings
from app.core.redis import RedisManager
from app.models.user import User


class MatchmakingService:
    """
    Handles the logic of adding users to the queue and finding matches.

    Strategy:
    - Players are stored in a Redis Sorted Set with their rating as score
    - When a player joins, we check for opponents within ±MATCHMAKING_RATING_RANGE
    - If found: create a match and notify both players via WebSocket
    - If not found: leave user in queue and return "searching"
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.rating_range = settings.MATCHMAKING_RATING_RANGE

    async def join_queue(self, user: User) -> dict:
        """
        Add a user to the matchmaking queue and immediately check for opponents.

        Returns:
            dict with keys: match_found, match_id (optional), message
        """
        user_id = str(user.id)

        # First check if an opponent is available BEFORE joining the queue
        # This avoids matching with yourself
        opponent = await self.redis.find_opponent(user_id, user.rating, self.rating_range)

        if opponent:
            # ── Match Found! ───────────────────────────────────────────────
            # Don't add ourselves to queue since we immediately matched
            opponent_id = opponent["user_id"]

            # In Phase 2 we'll create a DB Match record here and use the real ID
            # For now, generate a pseudo match_id from the two user IDs
            match_id = int(user_id) + int(opponent_id)

            # Notify both players via WebSocket (if connected)
            from app.websockets.manager import ws_manager
            await ws_manager.send_to_user(
                user_id,
                {
                    "event": "match_found",
                    "match_id": match_id,
                    "opponent_id": opponent_id,
                    "opponent_rating": opponent["rating"],
                },
            )
            await ws_manager.send_to_user(
                opponent_id,
                {
                    "event": "match_found",
                    "match_id": match_id,
                    "opponent_id": user_id,
                    "opponent_rating": user.rating,
                },
            )

            return {
                "match_found": True,
                "match_id": match_id,
                "opponent_id": opponent_id,
                "message": f"Match found! Battle starts now.",
            }

        # ── No Opponent Yet ────────────────────────────────────────────────
        # Add to queue and let the client poll or wait for WebSocket notification
        await self.redis.add_to_matchmaking_queue(user_id, user.rating)

        queue_size = await self.redis.get_queue_size()
        return {
            "match_found": False,
            "match_id": None,
            "message": f"Added to queue. Searching... ({queue_size} in queue)",
        }

    async def leave_queue(self, user_id: str) -> None:
        """Remove a user from the matchmaking queue."""
        await self.redis.remove_from_matchmaking_queue(user_id)
