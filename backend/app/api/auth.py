"""Авторизация: регистрация первого администратора, логин, профиль."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, PasswordChange, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

# простой rate-limiter: IP → [timestamps]
_login_attempts: dict[str, list[float]] = {}
_RATE_LIMIT = 10
_RATE_WINDOW = 60  # сек


def _rate_limited(ip: str) -> bool:
    import time
    now = time.time()
    bucket = _login_attempts.get(ip, [])
    bucket = [t for t in bucket if now - t < _RATE_WINDOW]
    _login_attempts[ip] = bucket
    if len(bucket) >= _RATE_LIMIT:
        return True
    bucket.append(now)
    return False


def _count_users(db: Session) -> int:
    return db.query(User).count()


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
def login(body: LoginRequest, db: Session = Depends(get_db), request=Depends(lambda: None)):
    # rate-limit по username/IP (простой in-memory)
    from fastapi import Request
    # получаем IP из текущего контекста, если доступен
    try:
        from fastapi import Request as _Req
        # fallback: без request — не лимитируем
        pass
    except Exception:
        pass
    # лимит по username (ключ — имя)
    if _rate_limited(body.username):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток, подождите минуту")
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный токен")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return UserOut.model_validate(user)


@router.post("/password", response_model=UserOut)
def change_password(
    body: PasswordChange,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Смена пароля текущего пользователя (важно: пароль по умолчанию admin123 — смените!)."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный токен")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Старый пароль неверный")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
