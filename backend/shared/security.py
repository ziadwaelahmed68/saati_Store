import base64
import hashlib
import hmac
import json
import os
import time
from functools import wraps
from flask import g, request
from shared.config import Config
from shared.http import err

# Fallback ephemeral key only for local test runs if AUTH_SECRET_KEY is not set
_FALLBACK_KEY = os.urandom(32).hex()


def _secret() -> bytes:
    key = Config.AUTH_SECRET_KEY or _FALLBACK_KEY
    return key.encode("utf-8")


def issue_token(email: str, name: str, role: str) -> str:
    if role not in ("admin", "customer"):
        role = "customer"
    payload = {
        "sub": email.lower().strip(),
        "name": name,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + Config.TOKEN_TTL,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")
    sig = hmac.new(_secret(), b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify_token(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(_secret(), b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        pad = "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(b64 + pad).decode("utf-8"))
        if payload.get("exp", 0) <= time.time():
            return None
        if payload.get("role") not in ("admin", "customer"):
            return None
        return payload
    except Exception:
        return None


def get_authenticated_user() -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    return verify_token(token)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return err("Authentication required. Please sign in.", 401)
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_authenticated_user()
            if not user:
                return err("Authentication required. Please sign in.", 401)
            if user.get("role") not in allowed_roles:
                return err("Forbidden: insufficient permissions.", 403)
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator