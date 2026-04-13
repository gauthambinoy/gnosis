from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import uuid
from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter()

# In-memory user store (will be replaced with DB queries when p1-db-models wires up)
_users: dict[str, dict] = {}
_users_by_email: dict[str, str] = {}


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    if data.email in _users_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": data.email,
        "full_name": data.full_name,
        "hashed_password": hash_password(data.password),
        "is_active": True,
        "llm_preset": "balanced",
    }
    _users[user_id] = user
    _users_by_email[data.email] = user_id

    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": user_id, "email": data.email, "full_name": data.full_name},
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user_id = _users_by_email.get(data.email)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = _users[user_id]
    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": user_id, "email": user["email"], "full_name": user["full_name"]},
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if user_id not in _users:
        raise HTTPException(status_code=401, detail="User not found")

    user = _users[user_id]
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user={"id": user_id, "email": user["email"], "full_name": user["full_name"]},
    )


@router.get("/me")
async def get_me():
    """Get current user profile — placeholder until wired to get_current_user_id dependency."""
    return {"message": "Wire up get_current_user_id dependency after DB models"}
