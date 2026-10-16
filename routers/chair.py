from fastapi import APIRouter, Depends, HTTPException
from models.requests import ChairMessGetRequest, ChairRespawnNoticeRequest
from services.auth import validate_session
from services.character import ensure_character
from database import get_db
from typing import Dict
from dependencies import get_json_body

router = APIRouter(prefix="/chair_messenger", tags=["chair_messenger"])

@router.post("/get")
async def chair_messenger_get(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChairMessGetRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    chair_list = []
    for warp in req.WarpInfoList:
        warp_id = warp.get("WarpInfoId")
        channel_id = warp.get("ChannelId", 0)
        if warp_id is not None:
            c.execute(
                "SELECT SUM(count) as total FROM chair_messages WHERE warp_info_id = ? AND channel_id = ?",
                (warp_id, channel_id)
            )
            row = c.fetchone()
            total = row["total"] if row and row["total"] else 0
            if total > 0:
                chair_list.append({"WarpInfoId": warp_id, "ChairMessCount": total})
    conn.close()
    return {
        "ChairMessList": chair_list,
        "ResKind": 0,
        "MessageId": "ChairMessGetListResponse"
    }

@router.post("/update")
async def chair_messenger_update(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChairRespawnNoticeRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chair_messages (warp_info_id, channel_id, chara_id, user_id, count) VALUES (?, ?, ?, ?, 1) "
        "ON CONFLICT(warp_info_id, channel_id, chara_id) DO UPDATE SET count = count + 1",
        (req.WarpInfoId, req.ChannelId, str(req.CharaId), req.UserId)
    )
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "ChairMessRespawnPointNoticeResponse"}