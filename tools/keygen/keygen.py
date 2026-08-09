"""Генератор лицензий (только у продавца!). Формат: base64(payload).base64(ed25519-sig).

Использование:
    python keygen.py genkey                        # создать пару ключей (private.pem / public.b64)
    python keygen.py issue --tier pro --customer "Иван" --support-until 2027-12-31
    python keygen.py public                        # вывести публичный ключ для CF_LICENSE_PUBKEY
"""
import argparse
import base64
import json
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

try:
    from backend.app.core.license import TIERS  # запуск из корня репо
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from backend.app.core.license import TIERS  # запуск из любой директории

HERE = Path(__file__).resolve().parent
PRIVATE_KEY = HERE / "private.pem"
PUBLIC_KEY = HERE / "public.b64"


def _load_private() -> Ed25519PrivateKey:
    if not PRIVATE_KEY.exists():
        raise SystemExit(f"Нет приватного ключа. Сначала: python keygen.py genkey ({PRIVATE_KEY})")
    return serialization.load_pem_private_key(PRIVATE_KEY.read_bytes(), password=None)


def genkey() -> None:
    key = Ed25519PrivateKey.generate()
    PRIVATE_KEY.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub = base64.b64encode(
        key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode()
    PUBLIC_KEY.write_text(pub)
    print(f"Приватный ключ:  {PRIVATE_KEY}")
    print(f"Публичный ключ:  {PUBLIC_KEY} = {pub}")


def issue(tier: str, customer: str, support_until: str, channels: int | None = None) -> None:
    if tier not in TIERS:
        raise SystemExit(f"Тариф должен быть одним из: {', '.join(TIERS)}")
    tpl = TIERS[tier]
    payload = {
        "tier": tier,
        "features": tpl["features"],
        "channels": channels or tpl["channels"],
        "customer": customer,
        "support_until": support_until or date.today().replace(year=date.today().year + 1).isoformat(),
        "issued": date.today().isoformat(),
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    priv = _load_private()
    sig = base64.b64encode(priv.sign(payload_b64.encode())).decode()
    print(f"{payload_b64}.{sig}")


def show_public() -> None:
    if not PUBLIC_KEY.exists():
        raise SystemExit("Публичный ключ не создан. Сначала: python keygen.py genkey")
    print(PUBLIC_KEY.read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Factory keygen")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("genkey", help="создать пару ключей")
    sub.add_parser("public", help="вывести публичный ключ")
    p_issue = sub.add_parser("issue", help="выпустить лицензию")
    p_issue.add_argument("--tier", required=True, choices=list(TIERS))
    p_issue.add_argument("--customer", default="")
    p_issue.add_argument("--support-until", default="")
    p_issue.add_argument("--channels", type=int, default=None)
    args = parser.parse_args()
    if args.cmd == "genkey":
        genkey()
    elif args.cmd == "issue":
        issue(args.tier, args.customer, args.support_until, args.channels)
    elif args.cmd == "public":
        show_public()
