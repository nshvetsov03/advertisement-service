import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, Token

# Настройки
TOKEN_TTL_SECONDS = 48 * 60 * 60  # 48 часов
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user: User, db: Session) -> Token:
    token = Token(
        token=str(uuid.uuid4()),
        user_id=user.id,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Извлекает токен из заголовка Authorization: Bearer <token>"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Возвращает пользователя, если токен валиден, иначе None."""
    token_str = get_token_from_header(authorization)
    if not token_str:
        return None

    token = db.query(Token).filter(Token.token == token_str).first()
    if not token:
        return None

    # Проверка срока действия (48 часов)
    if token.created_at < datetime.utcnow() - timedelta(seconds=TOKEN_TTL_SECONDS):
        db.delete(token)
        db.commit()
        return None

    return token.user


def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """Требует авторизации. Если пользователь не авторизован — 401."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """Требует роль admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user