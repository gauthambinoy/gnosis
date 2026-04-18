import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user_id,
)
from app.core.audit_log import audit_log
from app.core.rate_limiter import require_rate_limit
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, RefreshRequest,
    TokenResponse, UserResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory fallback (demo mode when PostgreSQL is unavailable)
# ---------------------------------------------------------------------------
_users: dict[str, dict] = {}
_users_by_email: dict[str, str] = {}
_users_lock = asyncio.Lock()


def _use_db() -> bool:
    """Return True when PostgreSQL is reachable."""
    from app.core.database import db_available as _flag
    return _flag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_dict(user_id: str, email: str, full_name: str | None) -> dict:
    return {"id": str(user_id), "email": email, "full_name": full_name or ""}


def _token_response(user_id: str, email: str, full_name: str | None) -> TokenResponse:
    uid = str(user_id)
    return TokenResponse(
        access_token=create_access_token({"sub": uid}),
        refresh_token=create_refresh_token({"sub": uid}),
        user=_user_dict(uid, email, full_name),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
              dependencies=[Depends(require_rate_limit)])
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            id=uuid.uuid4(),
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        await db.flush()
        await audit_log.log("auth.register", "system", {"email": data.email}, user_id=str(user.id))
        return _token_response(user.id, user.email, user.full_name)

    # Fallback: in-memory
    async with _users_lock:
        if data.email in _users_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        user_id = str(uuid.uuid4())
        _users[user_id] = {
            "id": user_id, "email": data.email, "full_name": data.full_name,
            "hashed_password": hash_password(data.password),
        }
        _users_by_email[data.email] = user_id
    await audit_log.log("auth.register", "system", {"email": data.email}, user_id=user_id)
    return _token_response(user_id, data.email, data.full_name)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(require_rate_limit)])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    if _use_db():
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalars().first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        await audit_log.log("auth.login", "system", {"email": data.email}, user_id=str(user.id))
        return _token_response(user.id, user.email, user.full_name)

    # Fallback
    async with _users_lock:
        uid = _users_by_email.get(data.email)
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        u = _users[uid]
    if not verify_password(data.password, u["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await audit_log.log("auth.login", "system", {"email": data.email}, user_id=uid)
    return _token_response(uid, u["email"], u["full_name"])


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(require_rate_limit)])
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")

    if _use_db():
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return _token_response(user.id, user.email, user.full_name)

    # Fallback
    if user_id not in _users:
        raise HTTPException(status_code=401, detail="User not found")
    u = _users[user_id]
    return _token_response(user_id, u["email"], u["full_name"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return current user profile from JWT."""
    if _use_db():
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_dict(user.id, user.email, user.full_name)

    # Fallback
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    u = _users[user_id]
    return _user_dict(user_id, u["email"], u["full_name"])
