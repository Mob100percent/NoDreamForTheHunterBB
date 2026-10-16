# routers/channel.py
import json
import logging
import sqlite3
import traceback
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from dependencies import get_json_body
from models.requests import (
    ChannelGetDetailsInfoRequest,
    ChannelGetInfoRequest,
    ChannelRandomJoinRequest,
    ChannelSearchRequest,
    ChannelUploadRequest,
    ChannelWordSearchRequest,
    ChannelShareRequest,
    ChannelAddMaterialRequest,
    ChannelAddMaterialCompleteNotifyRequest,
)
from services.auth import ensure_user_exists, validate_session
from services.character import ensure_character
from services.utils import generate_discernment_word

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channel", tags=["channel"])


def _build_channel_response(row) -> Dict[str, Any]:
    """Build a channel response using row['id'] as ChannelId."""
    return {
        "ChannelId": row["id"],                 # now auto‑increment
        "ShareLevel": row["share_level"],
        "Status": row["status"],
        "TurnoutLevel": row["turnout_level"],
        "FormDataVersion": row["form_data_version"],
        "FormData": row["form_data"],
        "DiscernmentWord": row["discernment_word"],
        "RitualLevel": row["ritual_level"],
        "HolyGrailTypeId": row["holy_grail_type_id"],
        "FixedOrGeneral": row["fixed_or_general"],
        "SubFeatureFlag": row["sub_feature_flag"],
        "CreateUserId": row["create_user_id"] if row["create_user_id"] is not None else 0,
        "CreateCharaId": int(row["create_chara_id"]) if row["create_chara_id"] is not None else 0,
        "CreateDate": row["create_date"],
        "LastPlayDate": row["last_play_date"],
        "WishMaterialList": json.loads(row["wish_material_list"]) if row["wish_material_list"] else [],
        "UnlockFlagList": [],   # filled separately
    }


@router.post("/search")
async def channel_search(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelSearchRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()

    # Types the player selected (0/1/2, one or several). null inside an item
    # is ignored.
    fg_list = [fg["FixedOrGeneral"] for fg in (req.FixedOrGeneralList or [])
               if isinstance(fg, dict) and fg.get("FixedOrGeneral") is not None]

    # Optional filters: only applied when the game actually sent a value.
    # null = "this condition does not matter".
    conds = []
    params = []
    if fg_list:
        placeholders = ",".join(["?"] * len(fg_list))
        conds.append("fixed_or_general IN ({})".format(placeholders))
        params.extend(fg_list)
    if req.Status is not None:
        conds.append("status = ?")
        params.append(req.Status)
    if req.HolyGrailTypeId is not None:
        conds.append("holy_grail_type_id = ?")
        params.append(req.HolyGrailTypeId)
    if req.RitualLevel is not None:
        conds.append("ritual_level = ?")
        params.append(req.RitualLevel)
    if req.SubFeatureFlag is not None:
        conds.append("sub_feature_flag = ?")
        params.append(req.SubFeatureFlag)
    limit = max(int(req.GetCount or 1), 1)
    where = " AND ".join(conds) if conds else "1=1"

    # 1) Normal channels first (public dungeons only).
    query = ("SELECT * FROM channels WHERE share_level = 2 AND "
             "{} ORDER BY created_at DESC LIMIT ?").format(where)
    c.execute(query, params + [limit])
    rows = c.fetchall()

    channel_list = []
    if rows:
        for row in rows:
            c2 = conn.cursor()
            c2.execute("SELECT unlock_flag FROM channel_unlock_flags WHERE channel_id = ?",
                       (row["id"],))
            flags = [f["unlock_flag"] for f in c2.fetchall()]
            c2.close()
            data = _build_channel_response(row)
            data["UnlockFlagList"] = [{"UnlockFlag": f} for f in flags]
            channel_list.append(data)
        conn.close()
        return {"ResKind": 0, "MessageId": "ChannelSearchResponse", "ChannelList": channel_list}

    # 2) Fallback: nothing in `channels` -> old fixed-dungeon logic:
    #    materialize instance(s) from the fixed_dungeons catalog the same way
    #    the legacy code did (insert into channels + unlock flags, fresh
    #    unique glyph word, requester as the owner).
    fquery = ("SELECT * FROM fixed_dungeons WHERE {} "
              "ORDER BY id ASC LIMIT ?").format(where)
    c.execute(fquery, params + [limit])
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    for fixed in c.fetchall():
        # Check the generated word doesn't already exist in the DB before inserting.
        while True:
            discernment_word = generate_discernment_word()
            if not conn.execute(
                    "SELECT 1 FROM channels WHERE discernment_word = ? LIMIT 1",
                    (discernment_word,)).fetchone():
                break
        c.execute("""
            INSERT INTO channels (
                fixed_or_general, form_data, form_data_version,
                holy_grail_type_id, ritual_level, status, sub_feature_flag,
                share_level, turnout_level, discernment_word,
                create_user_id, create_chara_id, create_date, last_play_date,
                wish_material_list, user_id, chara_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fixed["fixed_or_general"],
            fixed["form_data"],
            fixed["form_data_version"],
            fixed["holy_grail_type_id"],
            fixed["ritual_level"],
            fixed["status"],
            fixed["sub_feature_flag"],
            fixed["share_level"],
            0,                      # turnout_level default
            discernment_word,
            req.UserId,
            str(req.UserId),
            now,
            now,
            fixed["wish_material_list"],
            req.UserId,
            str(req.UserId)
        ))
        new_channel_id = c.lastrowid

        unlock_flags = json.loads(fixed["unlock_flag_list"])
        for flag in unlock_flags:
            c.execute("INSERT INTO channel_unlock_flags (channel_id, unlock_flag) VALUES (?, ?)",
                      (new_channel_id, flag))

        c2 = conn.cursor()
        row = c2.execute("SELECT * FROM channels WHERE id = ?", (new_channel_id,)).fetchone()
        flags = [f["unlock_flag"] for f in c2.execute(
            "SELECT unlock_flag FROM channel_unlock_flags WHERE channel_id = ?",
            (new_channel_id,)).fetchall()]
        c2.close()
        data = _build_channel_response(row)
        data["UnlockFlagList"] = [{"UnlockFlag": f} for f in flags]
        channel_list.append(data)
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "ChannelSearchResponse", "ChannelList": channel_list}


@router.post("/get_details_info")
async def channel_get_details_info(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelGetDetailsInfoRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    channel_list = []
    lost = []

    for ch_id_dict in req.ChannelIdList:
        ch_id = ch_id_dict.get("ChannelId")
        if ch_id is None:
            continue
        c.execute("SELECT * FROM channels WHERE id = ?", (ch_id,))
        row = c.fetchone()
        if not row:
            lost.append(ch_id)
            continue
        c2 = conn.cursor()
        c2.execute("SELECT unlock_flag FROM channel_unlock_flags WHERE channel_id = ?", (row["id"],))
        flags = [f["unlock_flag"] for f in c2.fetchall()]
        c2.close()
        data = _build_channel_response(row)
        data["UnlockFlagList"] = [{"UnlockFlag": f} for f in flags]
        channel_list.append(data)

    conn.close()
    return {
        "ChannelList": channel_list,
        "LostChannelIdList": lost,
        "ResKind": 0,
        "MessageId": "ChannelGetDetailsInfoResponse",
    }


@router.post("/upload")
async def channel_upload(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelUploadRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ensure_user_exists(req.UserId)
    ensure_character(str(req.CharaId), req.UserId)

    conn = get_db()
    c = conn.cursor()

    try:
        # Check the generated word doesn't already exist in the DB before inserting.
        while True:
            discernment_word = generate_discernment_word()
            if not conn.execute(
                    "SELECT 1 FROM channels WHERE discernment_word = ? LIMIT 1",
                    (discernment_word,)).fetchone():
                break
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        c.execute("""
            INSERT INTO channels (
                fixed_or_general, form_data, form_data_version,
                holy_grail_type_id, ritual_level, status, sub_feature_flag,
                share_level, turnout_level, discernment_word,
                create_user_id, create_chara_id, create_date, last_play_date,
                wish_material_list, user_id, chara_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.FixedOrGeneral,
            req.FormData,
            req.FormDataVersion,
            req.HolyGrailTypeId,
            req.RitualLevel,
            req.Status,
            req.SubFeatureFlag,
            req.ShareLevel,
            0,                      # turnout_level default
            discernment_word,
            req.UserId,
            str(req.CharaId),
            now,
            now,
            json.dumps(req.WishMaterialList),
            req.UserId,
            str(req.CharaId)
        ))
        channel_id = c.lastrowid

        for flag_dict in req.UnlockFlagList:
            c.execute(
                "INSERT INTO channel_unlock_flags (channel_id, unlock_flag) VALUES (?, ?)",
                (channel_id, flag_dict.get("UnlockFlag"))
            )

        conn.commit()
        logger.info(f"Channel created: id={channel_id}, word={discernment_word}")
        return {
            "ChannelId": channel_id,
            "DiscernmentWord": discernment_word,
            "ResKind": 0,
            "MessageId": "ChannelUploadResponse",
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()
        logger.error(f"SQL integrity error: {e}\n{traceback.format_exc()}")
        return {"ResKind": 0, "MessageId": "ChannelUploadResponse"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Channel upload error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        conn.close()


@router.post("/get_info")
async def channel_get_info(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelGetInfoRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    info_list = []
    lost = []

    if req.ChannelIdList:
        for ch_id_dict in req.ChannelIdList:
            ch_id = ch_id_dict.get("ChannelId")
            if ch_id is None:
                continue
            c.execute(
                "SELECT id, status, share_level, turnout_level FROM channels WHERE id = ?",
                (ch_id,)
            )
            row = c.fetchone()
            if row:
                info_list.append({
                    "ChannelId": row["id"],
                    "Status": row["status"],
                    "ShareLevel": row["share_level"],
                    "TurnoutLevel": row["turnout_level"],
                })
            else:
                lost.append(ch_id)
    else:
        c.execute("SELECT id, status, share_level, turnout_level FROM channels")
        rows = c.fetchall()
        for row in rows:
            info_list.append({
                "ChannelId": row["id"],
                "Status": row["status"],
                "ShareLevel": row["share_level"],
                "TurnoutLevel": row["turnout_level"],
            })
    conn.close()
    return {
        "ChannelInfoList": info_list,
        "LostChannelIdList": lost,
        "ResKind": 0,
        "MessageId": "ChannelGetInfoResponse",
    }


@router.post("/word_search")
async def channel_word_search(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelWordSearchRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM channels WHERE discernment_word = ?", (req.SearchWord,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"ResKind": 0, "MessageId": "ChannelWordSearchResponse"}

    c2 = conn.cursor()
    c2.execute("SELECT unlock_flag FROM channel_unlock_flags WHERE channel_id = ?", (row["id"],))
    flags = [f["unlock_flag"] for f in c2.fetchall()]
    c2.close()
    conn.close()

    data = _build_channel_response(row)
    data["UnlockFlagList"] = [{"UnlockFlag": f} for f in flags]
    return {**data, "ResKind": 0, "MessageId": "ChannelWordSearchResponse"}


@router.post("/random_join")
async def channel_random_join(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelRandomJoinRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ensure_character(str(req.CharaId), req.UserId)

    conn = get_db()
    c = conn.cursor()

    targets = req.RandomJoinTargetList
    if not targets:
        raise HTTPException(status_code=400, detail="No targets provided")

    row = None
    for target in targets:
        hgid = target.get("HolyGrailTypeId")
        rlevel = target.get("RitualLevel")
        c.execute(
            "SELECT * FROM channels WHERE holy_grail_type_id = ? AND ritual_level = ? AND status = 1 ORDER BY RANDOM() LIMIT 1",
            (hgid, rlevel)
        )
        row = c.fetchone()
        if row:
            break

    if not row:
        conn.close()
        return {"ResKind": 0, "MessageId": "ChannelRandomJoinResponse"}

    c2 = conn.cursor()
    c2.execute("SELECT unlock_flag FROM channel_unlock_flags WHERE channel_id = ?", (row["id"],))
    flags = [f["unlock_flag"] for f in c2.fetchall()]
    c2.close()
    conn.close()

    data = _build_channel_response(row)
    data["UnlockFlagList"] = [{"UnlockFlag": f} for f in flags]
    return {**data, "ResKind": 0, "MessageId": "ChannelRandomJoinResponse"}


def _channel_ids_from(req) -> list:
    """The game may reference channels by bare ChannelId or ChannelIdList."""
    ids = []
    if getattr(req, "ChannelId", None) is not None:
        ids.append(int(req.ChannelId))
    for entry in (getattr(req, "ChannelIdList", None) or []):
        cid = entry.get("ChannelId") if isinstance(entry, dict) else None
        if cid is not None:
            ids.append(int(cid))
    return ids


def _load_spent(c, channel_id):
    row = c.execute("SELECT spent_material_list FROM channels WHERE id = ?",
                    (channel_id,)).fetchone()
    if not row or not row["spent_material_list"]:
        return []
    try:
        return json.loads(row["spent_material_list"])
    except (ValueError, TypeError):
        return []


def _materials_complete(wish_list, spent_list):
    """All required (wish) materials satisfied by the spent materials."""
    spent = {}
    for m in spent_list or []:
        key = (int(m.get("MaterialMainTypeId", 0)), int(m.get("MaterialSubTypeId", 0)))
        spent[key] = spent.get(key, 0) + int(m.get("MaterialCount", 0))
    for w in wish_list or []:
        key = (int(w.get("WishMaterialMainTypeId", 0)), int(w.get("WishMaterialSubTypeId", 0)))
        if spent.get(key, 0) < int(w.get("WishMaterialCount", 0)):
            return False
    return True


@router.post("/share")
async def channel_share(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelShareRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ids = _channel_ids_from(req)
    if not ids:
        raise HTTPException(status_code=400, detail="No channel specified")

    conn = get_db()
    c = conn.cursor()
    for ch_id in ids:
        # Ownership: only the dungeon's creator may change its share level.
        c.execute("UPDATE channels SET share_level = ? WHERE id = ? AND create_user_id = ?",
                  (req.ShareLevel, ch_id, req.UserId))
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "ChannelShareResponse"}


@router.post("/add_material")
async def channel_add_material(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelAddMaterialRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ids = _channel_ids_from(req)
    if not ids:
        raise HTTPException(status_code=400, detail="No channel specified")

    conn = get_db()
    c = conn.cursor()
    for ch_id in ids:
        row = c.execute("SELECT create_user_id FROM channels WHERE id = ?", (ch_id,)).fetchone()
        if not row or row["create_user_id"] != req.UserId:
            continue
        spent = _load_spent(c, ch_id)
        for m in req.MaterialList or []:
            if not isinstance(m, dict):
                continue
            spent.append({
                "MaterialMainTypeId": int(m.get("MaterialMainTypeId", 0)),
                "MaterialSubTypeId": int(m.get("MaterialSubTypeId", 0)),
                "MaterialCount": int(m.get("MaterialCount", 0)),
            })
        c.execute("UPDATE channels SET spent_material_list = ? WHERE id = ?",
                  (json.dumps(spent), ch_id))
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "ChannelAddMaterialResponse"}


@router.post("/notify_add_material_complete")
async def channel_notify_add_material_complete(req_data: Dict = Depends(get_json_body)):
    try:
        req = ChannelAddMaterialCompleteNotifyRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    ids = _channel_ids_from(req)
    if not ids:
        raise HTTPException(status_code=400, detail="No channel specified")

    conn = get_db()
    c = conn.cursor()
    all_complete = True
    for ch_id in ids:
        row = c.execute("SELECT create_user_id, wish_material_list FROM channels WHERE id = ?",
                        (ch_id,)).fetchone()
        if not row or row["create_user_id"] != req.UserId:
            continue
        try:
            wish = json.loads(row["wish_material_list"]) if row["wish_material_list"] else []
        except (ValueError, TypeError):
            wish = []
        spent = _load_spent(c, ch_id)
        if not _materials_complete(wish, spent):
            all_complete = False
    conn.close()

    return {
        "CompleteFlag": 1 if all_complete else 0,
        "ResKind": 0,
        "MessageId": "ChannelAddMaterialCompleteNotifyResponse",
    }