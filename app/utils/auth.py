from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jwcrypto import jwk, jwe
import json
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
from binascii import unhexlify
from base64 import urlsafe_b64encode

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Encryption key setup (32 bytes = AES-256)
encryption_key_bytes = unhexlify(settings.ENCRYPTION_KEY)
if len(encryption_key_bytes) != 32:
    raise ValueError("ENCRYPTION_KEY must be 32 bytes for A256GCM encryption")

# Create JWK key object for jwcrypto
jwk_key = jwk.JWK(kty="oct", k=urlsafe_b64encode(encryption_key_bytes).decode("utf-8"))


# ------------------- Password Helpers ------------------- #
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ------------------- Token Helpers ------------------- #
def _create_jwe_token(data: dict, expires_delta: timedelta) -> str:
    """Helper to create encrypted JWE tokens with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": int(expire.timestamp())})

    # Protected header for AES-256 GCM direct encryption
    protected_header = {"alg": "dir", "enc": "A256GCM"}

    payload = json.dumps(to_encode)
    token = jwe.JWE(payload.encode("utf-8"), json.dumps(protected_header))
    token.add_recipient(jwk_key)
    return token.serialize(compact=True)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create encrypted JWE access token."""
    return _create_jwe_token(data, expires_delta or timedelta(minutes=15))


def create_refresh_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create encrypted JWE refresh token."""
    return _create_jwe_token(data, expires_delta or timedelta(days=7))


def create_temp_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create encrypted JWE temporary token for 2FA."""
    return _create_jwe_token(data, expires_delta or timedelta(minutes=5))


def decrypt_token(token: str) -> dict:
    """Decrypt JWE token back into a dict payload."""
    try:
        decrypted = jwe.JWE()
        decrypted.deserialize(token, key=jwk_key)
        payload = json.loads(decrypted.payload)
        if (
            payload.get("exp")
            and datetime.now(timezone.utc).timestamp() > payload["exp"]
        ):
            raise ValueError("Token expired")
        return payload
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {e}")


# ------------------- Per-User Data Encryption Helpers ------------------- #
def get_user_encryption_key(user_id: str) -> bytes:
    """
    Derive a unique 32-byte Fernet key for a specific user using HMAC-SHA256.
    """
    import hmac
    import hashlib
    import base64
    # encryption_key_bytes is derived from settings.ENCRYPTION_KEY
    h = hmac.new(encryption_key_bytes, user_id.encode("utf-8"), hashlib.sha256)
    return base64.urlsafe_b64encode(h.digest())


def encrypt_user_data(data: str, user_id: str) -> str:
    """Encrypt sensitive string data using a user-specific derived key."""
    if not data:
        return data
    from cryptography.fernet import Fernet
    key = get_user_encryption_key(user_id)
    f = Fernet(key)
    return f.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_user_data(encrypted_data: str, user_id: str) -> str:
    """Decrypt sensitive string data using a user-specific derived key."""
    if not encrypted_data:
        return encrypted_data
    from cryptography.fernet import Fernet
    try:
        key = get_user_encryption_key(user_id)
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback to returning data as-is if it's not encrypted (e.g. legacy database records)
        return encrypted_data

