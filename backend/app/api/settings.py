"""Настройки: подключение API-провайдеров (мастер), лицензия, статус системы."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.license import TIERS, parse_license
from app.core.security import decrypt_secrets, encrypt_secrets
from app.models import LicenseKey, ProviderSettings, SystemSetting, User
from app.providers.registry import PROVIDERS  # справочник доступных провайдеров
from app.schemas.settings import LicenseActivate, ProviderOut, ProviderSave, ResellerKeyRequest

from .deps import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/providers/catalog")
def provider_catalog(user: User = Depends(get_current_user)):
    """Справочник: какие провайдеры поддерживаются и зачем (для мастера настройки)."""
    return [
        {
            "type": ptype,
            "name": name,
            "description": meta.get("description", ""),
            "url": meta.get("url", ""),
            "free": meta.get("free", False),
            "fields": meta.get("fields", []),
        }
        for ptype, name, meta in PROVIDERS
    ]


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(ProviderSettings).order_by(ProviderSettings.provider_type).all()
    out = []
    for r in rows:
        o = ProviderOut.model_validate(r)
        payload = decrypt_secrets(r.encrypted_payload)
        o.label = r.label or (payload.get("note", "") if payload else "")
        out.append(o)
    return out


@router.post("/providers", response_model=ProviderOut)
def save_provider(
    body: ProviderSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.provider_type not in {p[0] for p in PROVIDERS}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный тип провайдера")
    row = (
        db.query(ProviderSettings)
        .filter(
            ProviderSettings.provider_type == body.provider_type,
            ProviderSettings.provider_name == body.provider_name,
        )
        .first()
    )
    if row is None:
        row = ProviderSettings(provider_type=body.provider_type, provider_name=body.provider_name)
        db.add(row)
    row.encrypted_payload = encrypt_secrets(body.payload)
    row.is_enabled = bool(body.payload.get("api_key") or body.payload.get("enabled"))
    row.is_default = body.is_default
    row.label = body.label
    db.commit()
    db.refresh(row)
    return row


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(ProviderSettings, provider_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Провайдер не найден")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- Лицензия -------------------------------------------------------------
@router.get("/license")
def get_license_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(LicenseKey).first()
    info = parse_license(row.key if row else "")
    return {
        "valid": info.valid,
        "demo": info.demo,
        "tier": info.tier,
        "channels": info.channels,
        "customer": info.customer,
        "support_until": info.support_until,
        "key": row.key if row else "",
    }


@router.post("/license")
def activate_license(body: LicenseActivate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    info = parse_license(body.key)
    if not info.valid:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ключ недействителен")
    row = db.query(LicenseKey).first()
    if row is None:
        row = LicenseKey(key=body.key)
        db.add(row)
    else:
        row.key = body.key
    db.commit()
    return {"valid": True, "tier": info.tier, "channels": info.channels, "demo": info.demo}


# --- White-label (брендинг) ------------------------------------------------
def _get_setting(db: Session, key: str) -> str | None:
    row = db.get(SystemSetting, key)
    return row.value if row else None


@router.get("/branding")
def get_branding(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Публичные настройки бренда (для панели)."""
    return {
        "app_name": _get_setting(db, "app_name") or "Content Factory",
        "logo_url": _get_setting(db, "logo_url") or "",
    }


@router.post("/license/reseller/generate")
def generate_reseller_key(body: ResellerKeyRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Unlimited: выпуск лицензий для перепродажи (нужен CF_RESELLER_PRIVATE_KEY)."""
    from datetime import date

    import base64
    import json

    from app.core.config import settings as app_settings
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if not app_settings.reseller_private_key:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Генерация лицензий недоступна: не задан CF_RESELLER_PRIVATE_KEY",
        )
    if body.tier not in TIERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Тариф: {', '.join(TIERS)}")

    try:
        priv = serialization.load_pem_private_key(app_settings.reseller_private_key.encode(), password=None)
        assert isinstance(priv, Ed25519PrivateKey)
    except Exception:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Невалидный CF_RESELLER_PRIVATE_KEY")

    features = body.features if body.features is not None else TIERS[body.tier]["features"]
    payload = {
        "tier": body.tier,
        "features": features,
        "channels": max(1, body.channels),
        "customer": body.customer,
        "support_until": body.support_until or date.today().replace(year=date.today().year + 1).isoformat(),
        "issued": date.today().isoformat(),
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    sig = base64.b64encode(priv.sign(payload_b64.encode())).decode()
    return {"key": f"{payload_b64}.{sig}", "payload": payload}


@router.put("/branding")
def set_branding(body: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """White-label (Unlimited): смена названия и логотипа системы."""
    for key in ("app_name", "logo_url"):
        if key in body:
            row = db.get(SystemSetting, key)
            if row is None:
                db.add(SystemSetting(key=key, value=str(body[key])))
            else:
                row.value = str(body[key])
    db.commit()
    return get_branding(db, user)
