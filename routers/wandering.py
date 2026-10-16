# routers/wandering.py
from fastapi import APIRouter, Depends, HTTPException
from models.requests import WanderingGhostCreateRequest, WanderingGhostGetRequest
from services.auth import validate_session
from services.character import ensure_character
from services.utils import generate_id
from database import get_db
from typing import Dict
from dependencies import get_json_body
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wandering_ghost", tags=["wandering_ghost"])

@router.post("/create")
async def wandering_ghost_create(req_data: Dict = Depends(get_json_body)):
    try:
        req = WanderingGhostCreateRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ensure_character(str(req.CharaId), req.UserId)

    conn = get_db()
    c = conn.cursor()
    ghost_id = generate_id()

    c.execute('''
        INSERT INTO wandering_ghosts (
            wandering_ghost_id, area_id, area_region_id, channel_id,
            chara_id, matching_level, wandering_ghost_data,
            wandering_ghost_data_version, user_id, reject_ignore
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ghost_id,
        req.AreaId,
        req.AreaRegionId,
        req.ChannelId,
        str(req.CharaId),
        req.MatchingLevel,
        req.WanderingGhostData,
        req.WanderingGhostDataVersion,
        req.UserId,
        req.RejectIgnore
    ))

    conn.commit()
    conn.close()

    return {
        "WanderingGhostId": int(ghost_id),
        "ResKind": 0,
        "MessageId": "WanderingGhostCreateResponse"
    }

@router.post("/get")
async def wandering_ghost_get(req_data: Dict = Depends(get_json_body)):
    try:
        req = WanderingGhostGetRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    ghost_list = []

    # Ghosts the client already received: (CharaId, UserId) pairs.
    joined_pairs = [
        (str(item.get("CharaId")), item.get("UserId"))
        for item in (req.JoinedCharaIdList or [])
        if isinstance(item, dict)
    ]

    for area_info in req.AreaList:
        area_id = area_info.get("AreaId")
        area_region_id = area_info.get("AreaRegionId")
        channel_id = area_info.get("ChannelId", 0)
        get_count = area_info.get("GetCount", 5)

        # The game queries the global/recent ghost feed with
        # AreaId=4294967295 / AreaRegionId=-1: any area, newest first.
        global_feed = (area_id == 4294967295) or (area_region_id == -1)
        
        
        if channel_id == 0:
            query = """
                SELECT wandering_ghost_id, wandering_ghost_data, wandering_ghost_data_version,
                       chara_id, user_id
                FROM wandering_ghosts
                WHERE area_id = ? AND area_region_id = ?
            """
            params = [area_id, area_region_id]
        else:
            query = """
                SELECT wandering_ghost_id, wandering_ghost_data, wandering_ghost_data_version,
                       chara_id, user_id
                FROM wandering_ghosts
                WHERE area_id = ? AND area_region_id = ? AND channel_id = ?
            """
            params = [area_id, area_region_id, channel_id]

        # Exclude ghosts the client already joined (matches on the
        # (chara_id, user_id) pair - never on chara_id alone, since every
        # player currently shares the sentinel chara id).
        if joined_pairs:
            placeholders = ",".join("(?,?)" for _ in joined_pairs)
            query += f" AND (chara_id, user_id) NOT IN ({placeholders})"
            for p in joined_pairs:
                params.extend(p)

        limit = min(get_count, req.GetMaxCount)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        c.execute(query, params)
        rows = c.fetchall()

        for row in rows:
            ghost_list.append({
                "WanderingGhostId": int(row["wandering_ghost_id"]),
                "WanderingGhostData": row["wandering_ghost_data"],
                "WanderingGhostDataVersion": row["wandering_ghost_data_version"]
            })

    conn.close()

    return {
        "ResKind": 0,
        "MessageId": "WanderingGhostGetResponse",
        "WanderingGhostList": ghost_list
    }