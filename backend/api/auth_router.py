from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import bcrypt

from core.config import get_settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    username: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate Bearer token and return username if successful."""
    settings = get_settings()
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience="Enterprise-RAG-Frontend",
            issuer="Enterprise-RAG-Backend"
        )
        
        # Verify custom access type claim
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        return payload.get("sub", "enterprise_user")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    settings = get_settings()
    
    # 1. Verify password: allow plaintext dev password if set, otherwise verify bcrypt hash
    valid_password = False
    # Dev plaintext fallback (useful when bcrypt tooling is unavailable)
    if getattr(settings, "admin_plain_password", None):
        if request.password == settings.admin_plain_password:
            valid_password = True

    if not valid_password:
        try:
            hashed = settings.admin_password_hash.encode("utf-8")
            password_bytes = request.password.encode("utf-8")
            valid_password = bcrypt.checkpw(password_bytes, hashed)
        except Exception:
            valid_password = False

    if not valid_password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
        
    # 2. Generate standard JWT claims
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=settings.jwt_expiration_minutes)
    
    payload = {
        "sub": request.username,
        "iat": now,
        "exp": expiration,
        "iss": "Enterprise-RAG-Backend",
        "aud": "Enterprise-RAG-Frontend",
        "type": "access"
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    return LoginResponse(
        access_token=token,
        username=request.username
    )
