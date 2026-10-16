# main.py
import base64
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

from config import DEBUG, SS_INFO_FILE, US_SS_INFO_FILE, ASIA_SS_INFO_FILE
from services.encryption import (SencRequestMiddleware, SencResponseMiddleware,
                                 decrypt_body)
from routers import (
    basic,
    penalty,
    blood,
    tomb,
    wandering,
    chair,
    channel,
    messenger_shell
)

# ------------------------------
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

debug_logger = logging.getLogger("debug_logger")
debug_logger.setLevel(logging.DEBUG)
if not debug_logger.handlers:
    fh = logging.FileHandler("debug.log")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    fh.setFormatter(formatter)
    debug_logger.addHandler(fh)

# ------------------------------
# Lifespan (startup / shutdown)
ss_info_base64 = None
us_ss_info_base64 = None
asia_ss_info_base64 = None

DEFAULT_SS_XML = """<ss>0</ss>
<msg2>...</msg2>
<gameurl2>...</gameurl2>
<ReloadServerStatusInfoInterval2>300</ReloadServerStatusInfoInterval2>
"""


def _load_ss_info(path: str, label: str):
    """Read an ss.info XML file and return its base64 encoding."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        logger.info(f"{label} loaded")
        return base64.b64encode(xml_content.encode("utf-8")).decode("utf-8")
    except FileNotFoundError:
        logger.warning(f"{path} not found, using minimal default")
        return base64.b64encode(DEFAULT_SS_XML.encode("utf-8")).decode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ss_info_base64, us_ss_info_base64, asia_ss_info_base64
    # Startup
    ss_info_base64 = _load_ss_info(SS_INFO_FILE, "ss.info")
    us_ss_info_base64 = _load_ss_info(US_SS_INFO_FILE, "us_ss.info")
    asia_ss_info_base64 = _load_ss_info(ASIA_SS_INFO_FILE, "asia_ss.info")
    yield
    # Shutdown (nothing needed)

# ------------------------------
# Create FastAPI app with lifespan
app = FastAPI(title="Bloodborne Private Server API", version="1.0", lifespan=lifespan)
# SENB response encryption must run BEFORE GZip on the way out (innermost):
# encrypted responses carry Content-Encoding: senc, which GZip respects and
# skips. Registered first so it sits inside GZip in the stack.
app.add_middleware(SencResponseMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ------------------------------
# Exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    body_repr = None
    if hasattr(exc, "body") and exc.body is not None:
        try:
            if isinstance(exc.body, bytes):
                body_repr = exc.body.decode("utf-8", errors="replace")
            else:
                body_repr = str(exc.body)
        except Exception:
            body_repr = str(exc.body)
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors(), "body": body_repr},
        headers={"sp-res-kind": "0"}
    )

# ------------------------------
# Middleware: parse JSON body
@app.middleware("https")
async def parse_json_body(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()
        request.state.raw_body = body
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
                request.state.json_body = data
            except json.JSONDecodeError as e:
                request.state.json_body = None
                request.state.json_error = str(e)
        else:
            request.state.json_body = None
    else:
        request.state.raw_body = None
        request.state.json_body = None
    response = await call_next(request)
    response.headers["sp-res-kind"] = "0"
    return response

# SENB request decryption must run BEFORE parse_json_body on the way in, so
# parse_json_body reads plaintext. Registered after parse_json_body, which
# makes it outer in the stack (requests hit it first).
app.add_middleware(SencRequestMiddleware)

# ------------------------------
# Debug logging middleware
@app.middleware("https")
async def log_requests(request: Request, call_next):
    if not DEBUG:
        return await call_next(request)
    debug_logger.info(f"=== REQUEST: {request.method} {request.url.path} ===")
    debug_logger.info(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    # After call_next the body is plaintext: SencRequestMiddleware has already
    # decrypted it and parse_json_body has captured/parsed it.
    raw = getattr(request.state, "raw_body", None)
    if raw:
        try:
            debug_logger.info(f"Raw Body: {raw.decode('utf-8')}")
        except Exception:
            debug_logger.info(f"Raw Body (bytes): {raw!r}")
    else:
        try:
            body = await request.body()
            if body:
                try:
                    debug_logger.info(f"Raw Body (fallback): {body.decode('utf-8')}")
                except Exception:
                    debug_logger.info(f"Raw Body (fallback bytes): {body!r}")
        except Exception:
            pass
    body = getattr(request.state, "json_body", None)
    if body is not None:
        debug_logger.info(f"Parsed Body: {json.dumps(body, indent=2)}")
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk
    debug_logger.info(f"=== RESPONSE: {response.status_code} ===")
    debug_logger.info(f"Headers: {dict(response.headers)}")
    if response.headers.get("content-encoding") == "senc" or \
            response.headers.get("x-senc") == "1":
        plain = decrypt_body(response_body)
        if plain is not None:
            try:
                debug_logger.info(f"Body (decrypted): {plain.decode('utf-8')}")
            except Exception:
                debug_logger.info(f"Body (decrypted bytes): {plain}")
        else:
            debug_logger.info("Body: <encrypted; decryption unavailable>")
    else:
        try:
            debug_logger.info(f"Body: {response_body.decode('utf-8')}")
        except Exception:
            debug_logger.info(f"Body: <not UTF-8>")
    return Response(content=response_body, status_code=response.status_code,
                    headers=dict(response.headers), media_type=response.media_type)

# ------------------------------
# Include routers
app.include_router(basic.router)
app.include_router(penalty.router)
app.include_router(blood.router)
app.include_router(tomb.router)
app.include_router(wandering.router)
app.include_router(chair.router)
app.include_router(channel.router)
app.include_router(messenger_shell.router)

# ------------------------------
# ss.info endpoint
@app.get("/bb-eu/ss.info", response_class=PlainTextResponse)
async def get_ss_info():
    return ss_info_base64


@app.get("/bb-us/ss.info", response_class=PlainTextResponse)
async def get_us_ss_info():
    return us_ss_info_base64


@app.get("/bb-asia/ss.info", response_class=PlainTextResponse)
async def get_asia_ss_info():
    return asia_ss_info_base64

# ------------------------------
# Main entry
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=20443)