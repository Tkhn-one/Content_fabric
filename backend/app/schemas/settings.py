from datetime import datetime

from pydantic import BaseModel


class ProviderSave(BaseModel):
    provider_type: str
    provider_name: str
    label: str = ""
    payload: dict = {}          # ключи/токены (api_key, voice_id, channel_id ...)
    is_default: bool = False


class ProviderOut(BaseModel):
    id: int
    provider_type: str
    provider_name: str
    label: str
    is_enabled: bool
    is_default: bool
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class LicenseActivate(BaseModel):
    key: str


class ResellerKeyRequest(BaseModel):
    tier: str = "pro"
    channels: int = 1
    customer: str = ""
    support_until: str = ""
    features: list[str] | None = None

