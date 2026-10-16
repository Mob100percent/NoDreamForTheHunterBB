from fastapi import Request, HTTPException
import json

async def get_json_body(request: Request) -> dict:
    """
    Parse and return the JSON body from the request.
    Works with the middleware that stores raw_body and json_body in request.state.
    """
    if hasattr(request.state, "json_body"):
        if request.state.json_body is not None:
            return request.state.json_body
        else:
            raw = getattr(request.state, "raw_body", None)
            if raw:
                try:
                    data = json.loads(raw.decode("utf-8"))
                    request.state.json_body = data
                    return data
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
            raise HTTPException(status_code=400, detail="Empty request body")
    # Fallback: read body directly
    body = await request.body()
    if body:
        try:
            return json.loads(body.decode("utf-8"))
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    return {}