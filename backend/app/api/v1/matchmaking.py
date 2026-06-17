"""
Matchmaking API Endpoints.

POST /api/v1/matchmaking/join   — Join the matchmaking queue
POST /api/v1/matchmaking/leave  — Leave the queue
GET  /api/v1/matchmaking/status — Check current queue status
GET  /api/v1/matchmaking/queue-size — How many players are in queue
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_active_user
from app.core.redis import redis_manager
from app.models.user import User
from app.services.matchmaking import MatchmakingService

router = APIRouter()


class MatchmakingStatusResponse(BaseModel):
    in_queue: bool
    queue_size: int
    match_found: bool
    match_id: Optional[int] = None


@router.post(
    "/join",
    summary="Join the matchmaking queue",
    status_code=status.HTTP_200_OK,
)
async def join_queue(
    current_user: User = Depends(get_current_active_user),
):
    """
    Adds the authenticated user to the matchmaking queue.

    If an opponent is immediately found within ±100 rating:
    - Both users are removed from queue
    - A match record is created
    - Returns match_found=True with match_id

    Otherwise returns match_found=False and the client
    should poll or wait for a WebSocket notification.
    """
    service = MatchmakingService(redis_manager)
    result = await service.join_queue(current_user)
    return result


@router.post(
    "/leave",
    summary="Leave the matchmaking queue",
    status_code=status.HTTP_200_OK,
)
async def leave_queue(
    current_user: User = Depends(get_current_active_user),
):
    """Removes the authenticated user from the matchmaking queue."""
    await redis_manager.remove_from_matchmaking_queue(str(current_user.id))
    return {"message": "Successfully removed from matchmaking queue"}


@router.get(
    "/queue-size",
    summary="Get current matchmaking queue size",
)
async def get_queue_size():
    """Returns how many players are currently searching for a match."""
    size = await redis_manager.get_queue_size()
    return {"queue_size": size}


@router.get(
    "/status",
    response_model=MatchmakingStatusResponse,
    summary="Check if I'm in the matchmaking queue",
)
async def get_matchmaking_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Checks if the current user is still in the queue,
    and returns current queue size.
    """
    queue_size = await redis_manager.get_queue_size()

    # Check if user is in queue by trying to find them
    all_entries = await redis_manager.client.zrange(
        redis_manager.MATCHMAKING_QUEUE_KEY, 0, -1
    )

    import json
    in_queue = any(
        json.loads(entry).get("user_id") == str(current_user.id)
        for entry in all_entries
    )

    return MatchmakingStatusResponse(
        in_queue=in_queue,
        queue_size=queue_size,
        match_found=False,
    )
