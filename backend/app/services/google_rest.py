"""Google Sheets / Drive через REST API с сервисным аккаунтом (без тяжёлых SDK).

Нужен только service_account_json (скачивается в Google Cloud Console) —
JWT RS256 подписывается библиотекой cryptography.
"""
import json
import logging
import time

import httpx

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"
SHEETS_URI = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_UPLOAD_URI = "https://www.googleapis.com/upload/drive/v3/files"


def _service_token(service_account_json: str | dict) -> str:
    creds = json.loads(service_account_json) if isinstance(service_account_json, str) else service_account_json
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": creds["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive",
        "aud": TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
    }
    import base64

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    signing_input = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(claims).encode())}"
    key = serialization.load_pem_private_key(creds["private_key"].encode(), password=None)
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())

    resp = httpx.post(
        TOKEN_URI,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": f"{signing_input}.{b64(signature)}",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def append_sheet_row(service_account_json: str | dict, spreadsheet_id: str, values: list) -> dict:
    token = _service_token(service_account_json)
    body = {"values": [values]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{SHEETS_URI}/{spreadsheet_id}/values/Журнал!A1:append",
            params={"valueInputOption": "USER_ENTERED"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


async def upload_drive(service_account_json: str | dict, file_path, folder_id: str = "", name: str = "") -> dict:
    token = _service_token(service_account_json)
    metadata = {"name": name or file_path.name}
    if folder_id:
        metadata["parents"] = [folder_id]
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{DRIVE_UPLOAD_URI}?uploadType=multipart",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "metadata": (None, json.dumps(metadata), "application/json; charset=UTF-8"),
                "file": (name or file_path.name, open(file_path, "rb"), "video/mp4"),
            },
        )
        resp.raise_for_status()
        return resp.json()
