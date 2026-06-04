import logging
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expires = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "exp": expires}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        logger.warning("Expired access token presented")
        raise TokenExpiredError("Access token has expired")
    except JWTError as exc:
        logger.warning("Invalid access token: %s", exc)
        raise TokenInvalidError("Invalid access token")
