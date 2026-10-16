from fastapi import APIRouter, Depends, HTTPException
from models.requests import (
    BloodMessSearchAddRequest,
    BloodMessCreateRequest,
    BloodMessGetListRequest,
    BloodMessGetEvaluateRequest,
    BloodMessEvaluateRequest,
    BloodMessRemoveRequest
)
from services.auth import validate_session
from services.character import ensure_character, get_messenger_shell, \
    DEFAULT_SHELL_INFO, DEFAULT_SHELL_INFO_VERSION
from services.utils import generate_id
from database import get_db
from typing import Dict
from dependencies import get_json_body

router = APIRouter(prefix="/blood_messenger", tags=["blood_messenger"])

@router.post("/exist_messages")
async def blood_messenger_exist_messages(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessSearchAddRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    evaluations = []
    lost = []
    for bm_id in req.BloodMessIdList:
        c.execute("SELECT evaluate_plus, evaluate_minus FROM blood_messages WHERE blood_mess_id = ?", (str(bm_id),))
        row = c.fetchone()
        if row:
            evaluations.append({
                "BloodMessId": bm_id,
                "EvaluatePlus": row["evaluate_plus"],
                "EvaluateMinus": row["evaluate_minus"]
            })
        else:
            lost.append(bm_id)
    conn.close()
    return {
        "BloodMessEvaluationList": evaluations,
        "LostBloodMessIdList": lost,
        "ResKind": 0,
        "MessageId": "BloodMessSearchAddResponse"
    }

@router.post("/create")
async def blood_messenger_create(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessCreateRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    shell_data, shell_version = get_messenger_shell(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    for msg in req.BloodMessList:
        blood_mess_id = generate_id()
        msg_shell = msg.get("MessShellInfo")
        if not isinstance(msg_shell, str) or not msg_shell:
            msg_shell = shell_data
        msg_shell_version = msg.get("MessShellInfoVersion")
        if msg_shell_version is None:
            msg_shell_version = shell_version
        c.execute('''
            INSERT INTO blood_messages (
                blood_mess_id, area_id, area_region_id, channel_id,
                blood_data, blood_data_version, chara_data, chara_data_version,
                evaluate_minus, evaluate_plus, prev_blood_mess_id,
                user_id, chara_id, mess_shell_info, mess_shell_info_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            blood_mess_id,
            msg.get("AreaId"),
            msg.get("AreaRegionId"),
            msg.get("ChannelId"),
            msg.get("BloodData"),
            msg.get("BloodDataVersion"),
            msg.get("CharaData", False),
            msg.get("CharaDataVersion"),
            msg.get("EvaluateMinus", 0),
            msg.get("EvaluatePlus", 0),
            str(msg.get("PrevBloodMessId")) if msg.get("PrevBloodMessId") else None,
            req.UserId,
            str(req.CharaId),
            msg_shell,
            msg_shell_version
        ))
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "BloodMessCreateResponse"}

@router.post("/message_area")
async def blood_messenger_message_area(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessGetListRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    blood_mess_list = []
    for area_info in req.AreaInfoList:
        area_id = area_info.get("AreaId")
        area_region_id = area_info.get("AreaRegionId")
        channel_id = area_info.get("ChannelId")
        get_count = area_info.get("GetCount", 30)
        c.execute('''
            SELECT blood_mess_id, blood_data, blood_data_version,
                   evaluate_minus, evaluate_plus,
                   mess_shell_info, mess_shell_info_version
            FROM blood_messages
            WHERE area_id = ? AND area_region_id = ? AND (channel_id = ? or ? = 0)
            ORDER BY created_at DESC
            LIMIT ?
        ''', (area_id, area_region_id, channel_id,channel_id, min(get_count, req.GetMaxCount)))
        rows = c.fetchall()
        for row in rows:
            blood_mess_list.append({
                "BloodMessId": int(row["blood_mess_id"]),
                "BloodData": row["blood_data"],
                "BloodDataVersion": row["blood_data_version"],
                "EvaluatePlus": row["evaluate_plus"],
                "EvaluateMinus": row["evaluate_minus"],
                "MessShellInfo": row["mess_shell_info"] or DEFAULT_SHELL_INFO,
                "MessShellInfoVersion": row["mess_shell_info_version"] or DEFAULT_SHELL_INFO_VERSION
            })
    conn.close()
    return {"ResKind": 0, "MessageId": "BloodMessGetListResponse", "BloodMessList": blood_mess_list}

@router.post("/evaluation")
async def blood_messenger_evaluation(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessGetEvaluateRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    evals = []
    for bm_id in req.BloodMessIdList:
        c.execute("SELECT evaluate_plus, evaluate_minus FROM blood_messages WHERE blood_mess_id = ?", (str(bm_id),))
        row = c.fetchone()
        if row:
            evals.append({
                "BloodMessId": bm_id,
                "EvaluatePlus": row["evaluate_plus"],
                "EvaluateMinus": row["evaluate_minus"]
            })
    conn.close()
    return {"ResKind": 0, "MessageId": "BloodMessGetEvaluateResponse", "BloodMessEvaluationList": evals}

@router.post("/evaluate_message")
async def blood_messenger_evaluate_message(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessEvaluateRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    # Update evaluation
    c.execute("SELECT evaluate_kind FROM blood_message_evaluations WHERE blood_mess_id = ? AND user_id = ?",
              (str(req.BloodMessId), req.UserId))
    row = c.fetchone()
    if row:
        old_kind = row["evaluate_kind"]
        if old_kind != req.EvaluateKind:
            if old_kind == 1:
                c.execute("UPDATE blood_messages SET evaluate_plus = evaluate_plus - 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
            elif old_kind == -1:
                c.execute("UPDATE blood_messages SET evaluate_minus = evaluate_minus - 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
            if req.EvaluateKind == 1:
                c.execute("UPDATE blood_messages SET evaluate_plus = evaluate_plus + 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
            elif req.EvaluateKind == -1:
                c.execute("UPDATE blood_messages SET evaluate_minus = evaluate_minus + 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
            c.execute("UPDATE blood_message_evaluations SET evaluate_kind = ? WHERE blood_mess_id = ? AND user_id = ?",
                      (req.EvaluateKind, str(req.BloodMessId), req.UserId))
    else:
        if req.EvaluateKind == 1:
            c.execute("UPDATE blood_messages SET evaluate_plus = evaluate_plus + 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
        elif req.EvaluateKind == -1:
            c.execute("UPDATE blood_messages SET evaluate_minus = evaluate_minus + 1 WHERE blood_mess_id = ?", (str(req.BloodMessId),))
        c.execute("INSERT INTO blood_message_evaluations (blood_mess_id, user_id, evaluate_kind) VALUES (?, ?, ?)",
                  (str(req.BloodMessId), req.UserId, req.EvaluateKind))
    conn.commit()
    c.execute("SELECT blood_mess_id, blood_data, blood_data_version, evaluate_plus, evaluate_minus, mess_shell_info, mess_shell_info_version FROM blood_messages WHERE blood_mess_id = ?", (str(req.BloodMessId),))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "BloodMessList": [{
                "BloodMessId": int(row["blood_mess_id"]),
                "BloodData": row["blood_data"],
                "BloodDataVersion": row["blood_data_version"],
                "EvaluatePlus": row["evaluate_plus"],
                "EvaluateMinus": row["evaluate_minus"],
                "MessShellInfo": row["mess_shell_info"],
                "MessShellInfoVersion": row["mess_shell_info_version"]
            }],
            "ResKind": 0,
            "MessageId": "BloodMessEvaluateResponse"
        }
    else:
        raise HTTPException(status_code=404, detail="Blood message not found")


@router.post("/delete")
async def blood_messenger_delete(req_data: Dict = Depends(get_json_body)):
    try:
        req = BloodMessRemoveRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")

    conn = get_db()
    c = conn.cursor()
    lost = []
    for blood_mess_id in req.BloodMessIdList:
        # Ownership check: only the author may remove their message.
        c.execute(
            "DELETE FROM blood_messages WHERE blood_mess_id = ? AND user_id = ?",
            (str(blood_mess_id), req.UserId))
        if c.rowcount == 0:
            lost.append(blood_mess_id)
        else:
            c.execute(
                "DELETE FROM blood_message_evaluations WHERE blood_mess_id = ?",
                (str(blood_mess_id),))
    conn.commit()
    conn.close()

    return {
        "LostBloodMessIdList": lost,
        "ResKind": 0,
        "MessageId": "BloodMessRemoveResponse"
    }