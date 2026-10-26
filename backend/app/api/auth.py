"""Авторизация: регистрация первого администратора, логин, профиль, смена пароля."""
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, PasswordChange, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

# Простой in-memory rate-limiter для /login: ключ "ip:username" → список меток времени.
# Защищает от перебора пароля; для одного пользователя на инсталляцию этого достаточно
# (при переходе на несколько воркеров — заменить на Redis/БД).
_login_attempts: dict[str, list[float]] = {}
_RATE_LIMIT = 10
_RATE_WINDOW = 60  # сек


def _rate_limited(key: str) -> bool:
    """True, если с этого ключа слишком много попыток входа за окно."""
    now = time.time()
    bucket = [t for t in _login_attempts.get(key, []) if now - t < _RATE_WINDOW]
    if len(bucket) >= _RATE_LIMIT:
        _login_attempts[key] = bucket
        return True
    bucket.append(now)
    _login_attempts[key] = bucket
    return False


def _count_users(db: Session) -> int:
    return db.query(User).count()


def _current_user(
    creds: HTTPAuthorizationCredentials | None, db: Session
) -> User:
    """Достаёт пользователя из Bearer-токена или бросает 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный токен")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return user


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация доступна только пока нет ни одного пользователя (первый = админ)."""
    if _count_users(db) > 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Регистрация закрыта")
    user = User(username=body.username, password_hash=hash_password(body.password), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Логин по логину/паролю. Лимит попыток: 10 в минуту на пару IP+username."""
    ip = request.client.host if request.client else "unknown"
    if _rate_limited(f"{ip}:{body.username}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Слишком много попыток входа, подождите минуту",
        )
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    return UserOut.model_validate(_current_user(creds, db))


@router.post("/password", response_model=UserOut)
def change_password(
    body: PasswordChange,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Смена пароля текущего пользователя (важно: пароль по умолчанию admin123 — смените!)."""
    user = _current_user(creds, db)
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Старый пароль неверный")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
