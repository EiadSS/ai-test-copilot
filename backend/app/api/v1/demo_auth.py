from __future__ import annotations

import re
import time
import secrets
from typing import Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# In-memory demo store (good enough for MVP/CI)
_USERS: Dict[str, dict] = {}          # email -> {password, profile}
_TOKENS: Dict[str, str] = {}          # token -> email
_LOGIN_ATTEMPTS: Dict[str, list] = {} # ip -> [timestamps]


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _rate_limit(ip: str, limit: int = 5, window_s: int = 60) -> None:
    now = time.time()
    arr = _LOGIN_ATTEMPTS.setdefault(ip, [])
    arr[:] = [t for t in arr if now - t <= window_s]
    if len(arr) >= limit:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    arr.append(now)


def _require_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth.split(" ", 1)[1].strip()
    email = _TOKENS.get(token)
    if not email:
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return email


class AuthBody(BaseModel):
    email: str
    password: str = Field(min_length=1)


class ProfilePatch(BaseModel):
    name: str | None = None
    bio: str | None = None
    avatarUrl: str | None = None


@router.post("/auth/register", status_code=201)
def register(body: AuthBody):
    if not _is_valid_email(body.email):
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be 8+ chars")
    if body.email in _USERS:
        raise HTTPException(status_code=409, detail="User already exists")

    _USERS[body.email] = {
        "password": body.password,
        "profile": {"email": body.email, "name": "", "bio": "", "avatarUrl": ""},
    }
    return {"ok": True}


@router.post("/auth/login")
def login(body: AuthBody, request: Request):
    ip = request.client.host if request.client else "unknown"

    u = _USERS.get(body.email)
    if not u or u["password"] != body.password:
        _rate_limit(ip)  # count only failed attempts
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # successful login shouldn't contribute to rate limit
    _LOGIN_ATTEMPTS.pop(ip, None)

    token = secrets.token_urlsafe(24)
    _TOKENS[token] = body.email
    return {"token": token}


@router.get("/me")
def me(request: Request):
    email = _require_token(request)
    return _USERS[email]["profile"]


@router.patch("/me")
def patch_me(body: ProfilePatch, request: Request):
    email = _require_token(request)
    prof = _USERS[email]["profile"]
    for k, v in body.model_dump(exclude_none=True).items():
        prof[k] = v
    return prof


@router.post("/auth/logout")
def logout(request: Request):
    email = _require_token(request)
    # invalidate token used
    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1].strip()
    _TOKENS.pop(token, None)
    return {"ok": True}