import pytest
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import patch, MagicMock

from core.config import Settings
from api.auth_router import verify_token, login, LoginRequest

# Create a sample hashed password for testing
TEST_PASSWORD = "secure_admin_password"
TEST_HASH = bcrypt.hashpw(TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# Mock Settings for JWT testing
@pytest.fixture
def mock_settings():
    return Settings(
        gemini_api_key="test-key-123",
        jwt_secret_key="super_secret_test_key",
        jwt_algorithm="HS256",
        jwt_expiration_minutes=15,
        admin_password_hash=TEST_HASH
    )

def test_generate_and_verify_token_success(mock_settings):
    """Test generating a valid JWT token and validating it successfully."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        # Generate token through login logic
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "admin_user",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "Enterprise-RAG-Backend",
            "aud": "Enterprise-RAG-Frontend",
            "type": "access"
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm=mock_settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        username = verify_token(credentials)
        assert username == "admin_user"

def test_login_success(mock_settings):
    """Test login functionality with valid password hash."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        request = LoginRequest(username="admin", password=TEST_PASSWORD)
        
        async def run_test():
            res = await login(request)
            assert res.username == "admin"
            assert res.access_token is not None
            
            # Decode generated token
            decoded = jwt.decode(
                res.access_token,
                mock_settings.jwt_secret_key,
                algorithms=[mock_settings.jwt_algorithm],
                audience="Enterprise-RAG-Frontend",
                issuer="Enterprise-RAG-Backend"
            )
            assert decoded["sub"] == "admin"
            assert decoded["type"] == "access"
            
        import asyncio
        asyncio.run(run_test())

def test_login_invalid_password(mock_settings):
    """Test login with an incorrect password fails."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        request = LoginRequest(username="admin", password="wrongpassword")
        
        async def run_test():
            with pytest.raises(HTTPException) as exc_info:
                await login(request)
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Invalid username or password"
            
        import asyncio
        asyncio.run(run_test())

def test_verify_token_invalid_signature(mock_settings):
    """Test that a JWT with an invalid signature is rejected."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "admin_user",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "Enterprise-RAG-Backend",
            "aud": "Enterprise-RAG-Frontend",
            "type": "access"
        }
        # Sign with incorrect key
        token = jwt.encode(payload, "wrong_secret_key", algorithm=mock_settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

def test_verify_token_modified_payload(mock_settings):
    """Test that tampered token payload fails verification."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "admin_user",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "Enterprise-RAG-Backend",
            "aud": "Enterprise-RAG-Frontend",
            "type": "access"
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm=mock_settings.jwt_algorithm)
        
        # Split token and manipulate the payload (middle segment)
        parts = token.split(".")
        # Replace middle segment with a custom base64 encoded block (claims tampered to sub: hacker)
        parts[1] = parts[1][:-2] + "AA"
        tampered_token = ".".join(parts)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tampered_token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

def test_verify_token_expired(mock_settings):
    """Test that an expired token is rejected."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        now = datetime.now(timezone.utc) - timedelta(minutes=30)
        payload = {
            "sub": "admin_user",
            "iat": now,
            "exp": now + timedelta(minutes=15), # Expired 15 mins ago
            "iss": "Enterprise-RAG-Backend",
            "aud": "Enterprise-RAG-Frontend",
            "type": "access"
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm=mock_settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token has expired"

def test_verify_token_invalid_type_claim(mock_settings):
    """Test that token without type: access is rejected."""
    with patch("api.auth_router.get_settings", return_value=mock_settings):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "admin_user",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "Enterprise-RAG-Backend",
            "aud": "Enterprise-RAG-Frontend",
            "type": "refresh" # Wrong type
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm=mock_settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(credentials)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token type"
