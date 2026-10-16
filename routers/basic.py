from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from models.requests import LoginRequest, SimpleRequest, EmergencyNoticeRequest
from services.auth import get_or_create_user, create_session, validate_session
from database import get_db
from typing import Dict
from dependencies import get_json_body

router = APIRouter(prefix="/basic_utils", tags=["basic_utils"])

@router.post("/login")
async def login(req_data: Dict = Depends(get_json_body)):
    try:
        req = LoginRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    user_id = get_or_create_user(
        req.PlatformAccountId,
        req.LanguageId,
        req.RegionId,
        req.IssuerId
    )
    session_id = create_session(user_id)
    warning_b64 = "V2VsY29tZSB0byBObyBEcmVhbSBmb3IgdGhlIEh1bnRlcg=="
    return {
        "ServerVersion": 1,
        "UserStatus": 0,
        "SessionId": session_id,
        "PlatformAccountId": req.PlatformAccountId,
        "LanguageId": float(req.LanguageId),
        "UserId": user_id,
        "MessageId": "LoginResponse",
        "WarningMessage": warning_b64,
        "IssuerId": float(req.IssuerId),
        "ResKind": 0
    }

@router.post("/get_normal_notice")
async def get_normal_notice(req_data: Dict = Depends(get_json_body)):
    session_id = req_data.get("SessionId")
    user_id = req_data.get("UserId")
    if not session_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing SessionId or UserId")
    if not validate_session(session_id, user_id):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, content FROM notices WHERE is_emergency = 0")
    rows = c.fetchall()
    conn.close()
    notice_list = [{"Id": row["id"], "Title": row["title"], "Notice": row["content"]} for row in rows]
    return {"ResKind": 0, "MessageId": "NoticeNormalGetResponse", "NoticeList": notice_list}

@router.post("/get_emergency_notice")
async def get_emergency_notice(req_data: Dict = Depends(get_json_body)):
    try:
        req = EmergencyNoticeRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, content FROM notices WHERE is_emergency = 1")
    rows = c.fetchall()
    conn.close()
    notice_list = [{"Id": row["id"], "Title": row["title"], "Notice": row["content"]} for row in rows]
    return {
        "ResKind": 0,
        "MessageId": "EmergencyNoticeGetResponse",
        "NoticeList": notice_list,
        "CheckTime": req.CheckTime
    }

@router.post("/get_user_agreement")
async def get_user_agreement(req_data: Dict = Depends(get_json_body)):
    try:
        req = SimpleRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    return {"ResKind": 0, "MessageId": "UserAgreementGetResponse", "Agreements": []}

@router.post("/get_datetime")
async def get_datetime(req_data: Dict = Depends(get_json_body)):
    try:
        req = SimpleRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ts = int(datetime.utcnow().timestamp() * 1000)
    return {"ResKind": 0, "MessageId": "DateTimeResponse", "Timestamp": ts}

@router.post("/sync_chara_id")
async def sync_chara_id(req_data: Dict = Depends(get_json_body)):
    try:
        req = SimpleRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    # The game asks the server to publish its character IDs. This server
    # has no chara-id registry: it publishes nothing, mirroring the
    # reference response the game accepts (empty PublishCharacterIdList).
    # The game then continues with its own sentinel CharaId.
    return {"PublishCharacterIdList": [], "ResKind": 0, "MessageId": "SyncCharaIdResponse"}