from fastapi import APIRouter, Depends, HTTPException
from models.requests import MessengerShellUploadRequest
from services.auth import validate_session
from services.character import ensure_character
from database import get_db
from typing import Dict
from dependencies import get_json_body

router = APIRouter(prefix="/messenger_shell", tags=["messenger_shell"])

@router.post("/upload")
async def messenger_shell_upload(req_data: Dict = Depends(get_json_body)):
    try:
        req = MessengerShellUploadRequest(**req_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not validate_session(req.SessionId, req.UserId):
        raise HTTPException(status_code=400, detail="Invalid session")
    ensure_character(str(req.CharaId), req.UserId)
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM messenger_shells WHERE chara_id = ? AND user_id = ?",
        (str(req.CharaId), req.UserId)
    )
    row = c.fetchone()
    if row:
        c.execute(
            "UPDATE messenger_shells SET shell_data = ?, shell_data_version = ? WHERE id = ?",
            (req.ShellData, req.ShellDataVersion, row["id"])
        )
    else:
        c.execute(
            "INSERT INTO messenger_shells (chara_id, user_id, shell_data, shell_data_version) VALUES (?, ?, ?, ?)",
            (str(req.CharaId), req.UserId, req.ShellData, req.ShellDataVersion)
        )
    conn.commit()
    conn.close()
    return {"ResKind": 0, "MessageId": "MessengerShellUploadResponse"}