from fastapi import APIRouter, Depends, HTTPException
from models.requests import (TombMessGetListRequest, TombMessCreateRequest,
                             DeathVisionGetRequest, TombMessRemoveRequest)
from services.auth import validate_session
from services.character import ensure_character, get_messenger_shell, \
    DEFAULT_SHELL_INFO, DEFAULT_SHELL_INFO_VERSION
from services.utils import generate_id
from database import get_db
from typing import Dict
from dependencies import get_json_body

router = APIRouter(prefix="/tomb_messenger", tags=["tomb_messenger"])

# Hard cap on the TOTAL number of tomb messages in one reply. The game keeps them in a fixed-size
# heap; a guest asks for many areas at once and an over-full reply makes it run out of memory
# (DL_PANIC "Transaction failed"). The client's GetMaxCount is also honored as a total.
MAX_TOMB_TOTAL = 50

@router.post("/message_area")
async def tomb_messenger_message_area(req_data: Dict = Depends(get_json_body)):
    try:
        req = TombMessGetListRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    max_total = max(0, min(req.GetMaxCount, MAX_TOMB_TOTAL))
    candidates = []
    seen = set()
    for area_info in req.AreaInfoList:
        area_id = area_info.get("AreaId")
        area_region_id = area_info.get("AreaRegionId")
        channel_id = area_info.get("ChannelId")
        get_count = area_info.get("GetCount", 30)
        c.execute('''
            SELECT tomb_mess_id, tomb_data, mess_shell_info, mess_shell_info_version, created_at
            FROM tomb_messages
            WHERE area_id = ? AND area_region_id = ? AND (channel_id = ? or ? = 0)
            ORDER BY created_at DESC
            LIMIT ?
        ''', (area_id, area_region_id, channel_id, channel_id, min(get_count, max_total)))
        for row in c.fetchall():
            if row["tomb_mess_id"] not in seen:
                seen.add(row["tomb_mess_id"])
                candidates.append(row)
    conn.close()
    # the newest across all requested areas, never more than the total cap
    candidates.sort(key=lambda r: r["created_at"] or "", reverse=True)
    tomb_list = [{
        "TombMessId": int(row["tomb_mess_id"]),
        "TombData": row["tomb_data"],
        "MessShellInfo": row["mess_shell_info"] or DEFAULT_SHELL_INFO,
        "MessShellInfoVersion": row["mess_shell_info_version"] or DEFAULT_SHELL_INFO_VERSION
    } for row in candidates[:max_total]]
    return {"ResKind": 0, "MessageId": "TombMessGetListResponse", "TombMessList": tomb_list}

@router.post("/create")
async def tomb_messenger_create(req_data: Dict = Depends(get_json_body)):
    try:
        req = TombMessCreateRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    shell_data, shell_version = get_messenger_shell(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    tomb_mess_id = generate_id()
    c.execute('''
        INSERT INTO tomb_messages (
            tomb_mess_id, area_id, area_region_id, channel_id,
            tomb_data, tomb_data_version,
            death_vision_data, death_vision_data_version,
            mess_shell_info, mess_shell_info_version,
            user_id, chara_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        tomb_mess_id,
        req.AreaId,
        req.AreaRegionId,
        req.ChannelId,
        req.TombData,
        req.TombDataVersion,
        req.DeathVisionData,
        req.DeathVisionDataVersion,
        shell_data,
        shell_version,
        req.UserId,
        str(req.CharaId)
    ))
    conn.commit()
    conn.close()
    return {
        "TombMessId": int(tomb_mess_id),
        "ResKind": 0,
        "MessageId": "TombMessCreateResponse"
    }

@router.post("/death_vision_get")
async def tomb_messenger_death_vision_get(req_data: Dict = Depends(get_json_body)):
    try:
        req = DeathVisionGetRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT death_vision_data, death_vision_data_version FROM tomb_messages WHERE tomb_mess_id = ?", (str(req.TombMessId),))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "DeathVisionData": row["death_vision_data"],
            "DeathVisionDataVersion": row["death_vision_data_version"],
            "ResKind": 0,
            "MessageId": "DeathVisionGetResponse"
        }
    else:
        raise HTTPException(status_code=404, detail="Tomb message not found")


@router.post("/delete")
async def tomb_messenger_delete(req_data: Dict = Depends(get_json_body)):
    try:
        req = TombMessRemoveRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    # Ownership check: only the player who died may remove their tombstone.
    c.execute(
        "DELETE FROM tomb_messages WHERE tomb_mess_id = ? AND user_id = ?",
        (str(req.TombMessId), req.UserId))
    conn.commit()
    conn.close()

    return {"ResKind": 0, "MessageId": "TombMessRemoveResponse"}