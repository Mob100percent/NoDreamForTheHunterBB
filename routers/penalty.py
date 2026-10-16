import json
from fastapi import APIRouter, Depends, HTTPException
from models.requests import (UserPropertiesMoveCountCheckRequest,
                             UserPropertiesMoveCountRequest,
                             MultiPlayNetErrorRequest)
from services.auth import validate_session
from typing import Dict
from dependencies import get_json_body
from database import get_db

router = APIRouter(prefix="/penalty", tags=["penalty"])

@router.post("/check_user_priority_move_count")
async def check_user_priority_move_count(req_data: Dict = Depends(get_json_body)):
    try:
        req = UserPropertiesMoveCountCheckRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    return {"ResKind": 0, "MessageId": "UserPropertiesMoveCountCheckResponse"}

@router.post("/notify_user_properties_move_count")
async def notify_user_properties_move_count(req_data: Dict = Depends(get_json_body)):
    try:
        req = UserPropertiesMoveCountRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    return {"ResKind": 0, "MessageId": "UserPropertiesMoveCountResponse"}

@router.post("/notify_multi_play_error")
async def notify_multi_play_error(req_data: Dict = Depends(get_json_body)):
    try:
        req = MultiPlayNetErrorRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    # The game reports a multiplayer error (penalty tracking). The request
    # carries no error-specific fields beyond the envelope, so we store the
    # full body for anti-cheat review.
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO multi_play_error_reports (user_id, request_body) VALUES (?, ?)",
        (req.UserId, json.dumps(req_data, default=str)))
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "MultiPlayNetErrorResponse"}