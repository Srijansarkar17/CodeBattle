"""
Redis Connection Manager.

Provides:
- Async Redis connection pool
- Online user tracking (who is currently connected)
- Matchmaking queue operations
- Generic key/value helpers
"""

import json
import asyncio
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings


class RedisManager:
    """
    Singleton Redis manager.
    Manages a single connection pool shared across the application.
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Open the Redis connection pool."""
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,         # Always return str, not bytes
            max_connections=settings.REDIS_POOL_SIZE,
        )
        # Verify connection is alive
        await self._client.ping()
        print("✅ Redis connected.")

    async def disconnect(self) -> None:
        """Close all Redis connections."""
        if self._client:
            await self._client.aclose()
            print("✅ Redis disconnected.")

    @property
    def client(self) -> aioredis.Redis:
        """Return the raw Redis client for advanced operations."""
        if not self._client:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return self._client

    # ── Online User Tracking ──────────────────────────────────────────────────
    # We store online users in a Redis Set: "online_users"
    # Each entry is a user_id (string)

    async def add_online_user(self, user_id: str) -> None:
        """Mark a user as online."""
        await self._client.sadd("online_users", user_id)

    async def remove_online_user(self, user_id: str) -> None:
        """Mark a user as offline."""
        await self._client.srem("online_users", user_id)

    async def get_online_users(self) -> set:
        """Return the set of all currently online user IDs."""
        return await self._client.smembers("online_users")

    async def is_user_online(self, user_id: str) -> bool:
        """Check if a specific user is online."""
        return await self._client.sismember("online_users", user_id)

    async def get_online_count(self) -> int:
        """Return the total number of online users."""
        return await self._client.scard("online_users")

    # ── Matchmaking Queue ─────────────────────────────────────────────────────
    # Queue is a Redis Sorted Set: "matchmaking_queue"
    # Score = user's rating (allows finding opponents within ±100 range)
    # Member = JSON string with {user_id, rating, queued_at}

    MATCHMAKING_QUEUE_KEY = "matchmaking_queue"

    async def add_to_matchmaking_queue(
        self, user_id: str, rating: int
    ) -> None:
        """Add a user to the matchmaking queue with their rating as score."""
        entry = json.dumps({"user_id": user_id, "rating": rating})
        await self._client.zadd(
            self.MATCHMAKING_QUEUE_KEY,
            {entry: rating},    # Score = rating for range queries
        )

    async def remove_from_matchmaking_queue(self, user_id: str) -> None:
        """Remove a user from the matchmaking queue (they cancelled or matched)."""
        # We need to find their entry by scanning (user_id is inside JSON)
        all_entries = await self._client.zrange(
            self.MATCHMAKING_QUEUE_KEY, 0, -1, withscores=True
        )
        for member, _ in all_entries:
            data = json.loads(member)
            if data["user_id"] == user_id:
                await self._client.zrem(self.MATCHMAKING_QUEUE_KEY, member)
                break

    async def find_opponent(
        self, user_id: str, rating: int, rating_range: int = 100
    ) -> Optional[dict]:
        """
        Find an opponent within ±rating_range of the given rating.

        Uses Redis ZRANGEBYSCORE to efficiently query by rating range.
        Returns the matched opponent's data dict, or None if no match found.
        """
        min_rating = rating - rating_range
        max_rating = rating + rating_range

        # Get all users in the rating range
        candidates = await self._client.zrangebyscore(
            self.MATCHMAKING_QUEUE_KEY,
            min_rating,
            max_rating,
            withscores=False,
        )

        for member in candidates:
            data = json.loads(member)
            # Skip ourselves
            if data["user_id"] == user_id:
                continue
            # Found a valid opponent — remove them from queue
            await self._client.zrem(self.MATCHMAKING_QUEUE_KEY, member)
            return data

        return None  # No suitable opponent found yet

    async def get_queue_size(self) -> int:
        """Return how many players are currently in the matchmaking queue."""
        return await self._client.zcard(self.MATCHMAKING_QUEUE_KEY)

    # ── Generic Cache Helpers ─────────────────────────────────────────────────

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        """Set a key with an optional TTL (default 5 minutes)."""
        await self._client.setex(key, ttl_seconds, value)

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key, returns None if missing."""
        return await self._client.get(key)

    async def delete(self, key: str) -> None:
        """Delete a key."""
        await self._client.delete(key)


# ── Singleton Instance ────────────────────────────────────────────────────────
redis_manager = RedisManager()
