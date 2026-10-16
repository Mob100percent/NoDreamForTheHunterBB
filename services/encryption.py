# SPDX-FileCopyrightText: Copyright 2026 Bloodborne Private Server
# SPDX-License-Identifier: MIT
#
# SENB body encryption for the Bloodborne private server.
#
# Mirrors the client's senc_body.{h,cpp} (vendored Monocypher):
#   key  = BLAKE2b-256(keyed: psk as key, "shadnet-bb-enc-v1" as message)
#   body = "SENB" | u8 ver=1 | u8[3] zeros | nonce[24] | tag[16] | ciphertext
#   AAD  = b"SENB" + b"\x01" + b"\x00\x00\x00"   (XChaCha20-Poly1305 IETF)
#
# Modes (config.BB_ENC_MODE):
#   off       - no encryption (original behavior)
#   optional  - accept encrypted AND plaintext requests; encrypted requests
#               get encrypted responses, plaintext ones stay plaintext
#   required  - reject request bodies that are not SENB (empty bodies pass,
#               e.g. GETs); all non-empty responses are encrypted
import hashlib
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

import config

logger = logging.getLogger(__name__)

MAGIC = b"SENB"
VERSION = 1
AAD = MAGIC + bytes([VERSION]) + b"\x00\x00\x00"
NONCE_SIZE = 24
TAG_SIZE = 16
HEADER_SIZE = 4 + 1 + 3 + NONCE_SIZE + TAG_SIZE  # 48

_mode = None
_key = None
_key_path = None  # resolved absolute path of the key file (for logging)


def _resolve_key_path() -> str:
    path = getattr(config, "BB_ENC_KEY_FILE", "bb_enc_key.txt")
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    return path


def _load_key() -> bytes | None:
    """Load the BB PSK file and derive the SENB key. None when unavailable."""
    global _key_path
    path = _resolve_key_path()
    _key_path = path
    if not os.path.exists(path):
        logger.warning("SENB: key file %s not found - encryption disabled", path)
        return None
    with open(path, "rb") as f:
        psk = f.read().strip()
    if not psk:
        logger.warning("SENB: key file %s is empty - encryption disabled", path)
        return None
    return hashlib.blake2b(b"shadnet-bb-enc-v1", digest_size=32, key=psk).digest()


def mode() -> str:
    """Normalized current mode (off/optional/required)."""
    global _mode
    if _mode is None:
        _mode = str(getattr(config, "BB_ENC_MODE", "off")).strip().lower()
        if _mode not in ("off", "optional", "required"):
            logger.warning("SENB: unknown BB_ENC_MODE %r - falling back to 'off'", _mode)
            _mode = "off"
    return _mode


def key() -> bytes | None:
    global _key
    if _key is None:
        _key = _load_key()
        if _key is not None:
            logger.info("SENB: mode=%s key loaded (psk %d chars)", mode(),
                        os.path.getsize(_key_path) if _key_path else 0)
        else:
            if mode() == "required":
                logger.error("SENB: mode=required but no key available - "
                             "all request bodies will be rejected")
    return _key


def looks_encrypted(body: bytes) -> bool:
    return body[:4] == MAGIC


def encrypt_body(plain: bytes) -> bytes | None:
    k = key()
    if not k or not plain:
        return None
    try:
        import nacl.bindings  # libsodium: XChaCha20-Poly1305 IETF
    except ImportError:
        logger.error("SENB: PyNaCl not installed - cannot encrypt")
        return None
    nonce = os.urandom(NONCE_SIZE)
    ct_tag = nacl.bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(plain, AAD, nonce, k)
    tag, ct = ct_tag[-TAG_SIZE:], ct_tag[:-TAG_SIZE]
    return MAGIC + bytes([VERSION]) + b"\x00\x00\x00" + nonce + tag + ct


def decrypt_body(wrapped: bytes) -> bytes | None:
    k = key()
    if not k or not looks_encrypted(wrapped) or len(wrapped) < HEADER_SIZE:
        return None
    if wrapped[4] != VERSION:
        return None
    try:
        import nacl.bindings
    except ImportError:
        logger.error("SENB: PyNaCl not installed - cannot decrypt")
        return None
    nonce = wrapped[8:8 + NONCE_SIZE]
    tag = wrapped[8 + NONCE_SIZE:8 + NONCE_SIZE + TAG_SIZE]
    ct = wrapped[8 + NONCE_SIZE + TAG_SIZE:]
    try:
        return nacl.bindings.crypto_aead_xchacha20poly1305_ietf_decrypt(ct + tag, AAD, nonce, k)
    except Exception:
        logger.warning("SENB: body decrypt failed (bad tag / wrong key)")
        return None


def _replace_request_body(request, body: bytes) -> None:
    """Swap the request body downstream code will read (Starlette caches
    request._body and request.body() returns it)."""
    request._body = body  # noqa: SLF001 - intentional cache injection
    # Keep headers honest (drop old content-length, add the plaintext size).
    headers = []
    for name, value in request.scope.get("headers", []):
        if name.lower() != b"content-length":
            headers.append((name, value))
    headers.append((b"content-length", str(len(body)).encode()))
    request.scope["headers"] = headers


class SencRequestMiddleware(BaseHTTPMiddleware):
    """Decrypt SENB request bodies before the JSON parsing middleware.

    Registered AFTER the parse_json_body middleware in main.py, so it wraps
    it on requests: this runs first, parse_json_body then sees plaintext.
    """

    async def dispatch(self, request, call_next):
        request.state.senc_request_encrypted = False
        m = mode()
        if m == "off":
            return await call_next(request)
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if body:
                if looks_encrypted(body):
                    plain = decrypt_body(body)
                    if plain is None:
                        return JSONResponse({"error": "invalid encrypted body"},
                                            status_code=400,
                                            headers={"sp-res-kind": "0"})
                    _replace_request_body(request, plain)
                    request.state.senc_request_encrypted = True
                elif m == "required":
                    return JSONResponse({"error": "encryption required"},
                                        status_code=403,
                                        headers={"sp-res-kind": "0"})
        return await call_next(request)


class SencResponseMiddleware(BaseHTTPMiddleware):
    """Encrypt responses for encrypted requests (and always in required mode).

    Registered BEFORE GZipMiddleware so this runs first on the way out:
    encrypted responses carry Content-Encoding: senc, which makes GZip
    skip them. The client's HTTP stack leaves 'senc' bodies alone and the
    emulator decrypts them before the game reads them.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        m = mode()
        if m == "off":
            return response
        should_encrypt = m == "required" or getattr(request.state,
                                                    "senc_request_encrypted", False)
        if not should_encrypt:
            return response
        # Collect the body (plain Response/JSONResponse or streaming).
        try:
            if hasattr(response, "body"):
                body = response.body
            else:
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
                body = b"".join(chunks)
        except Exception:
            body = b""
        if not body:
            return response
        wrapped = encrypt_body(body)
        if wrapped is None:
            logger.error("SENB: response encryption failed - sending plaintext")
            return response
        # Rebuild the header dict WITHOUT any existing content-length /
        # content-encoding (Starlette Headers keys are lowercase; a leftover
        # plaintext content-length alongside ours would make h11 reject the
        # body as "Too much data for declared Content-Length").
        headers = {k: v for k, v in response.headers.items()
                   if k not in ("content-length", "content-encoding")}
        headers["content-length"] = str(len(wrapped))
        headers["content-encoding"] = "senc"
        headers["x-senc"] = "1"
        return Response(content=wrapped, status_code=response.status_code, headers=headers,
                        media_type=None)
