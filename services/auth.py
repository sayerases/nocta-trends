import hashlib
import os
import time
from typing import Optional
from fastapi import Request, Response, HTTPException, status
from sqlmodel import Session, select
from core.database import get_session, engine
from models.database import User

# In-memory session store for simplicity
# Maps session_id (str) -> user_id (int)
_sessions = {}
SESSION_COOKIE_NAME = "nocta_session"

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 (for MVP only, use passlib/bcrypt for prod)."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def create_session(user_id: int, response: Response) -> str:
    session_id = os.urandom(24).hex()
    _sessions[session_id] = {
        "user_id": user_id,
        "expires_at": time.time() + (7 * 24 * 3600) # 7 days
    }
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
    )
    return session_id

def destroy_session(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    response.delete_cookie(SESSION_COOKIE_NAME)

def get_current_user_id(request: Request) -> Optional[int]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id or session_id not in _sessions:
        return None
    session_data = _sessions[session_id]
    if time.time() > session_data["expires_at"]:
        del _sessions[session_id]
        return None
    return session_data["user_id"]

def get_current_user(request: Request, session: Session) -> Optional[User]:
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    user = session.get(User, user_id)
    return user

def require_auth(request: Request, session: Session) -> User:
    user = get_current_user(request, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user

def require_admin(request: Request, session: Session) -> User:
    user = require_auth(request, session)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

def deduct_tokens(user: User, amount: int, session: Session) -> bool:
    """Deduct tokens and save. Returns True if successful, False if insufficient tokens."""
    if user.role == "admin":
        return True # Admin has unlimited
        
    if user.tokens >= amount:
        user.tokens -= amount
        session.add(user)
        session.commit()
        return True
    return False

def init_admin_user(session: Session):
    """Ensure at least one admin exists"""
    admin = session.exec(select(User).where(User.email == "admin@nocta.app")).first()
    if not admin:
        new_admin = User(
            email="admin@nocta.app",
            name="Admin",
            password_hash=hash_password("admin123"),
            role="admin",
            tokens=999999
        )
        session.add(new_admin)
        session.commit()
