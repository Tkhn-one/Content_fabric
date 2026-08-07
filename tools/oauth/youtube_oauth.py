"""Получение refresh_token для YouTube Data API (OAuth 2.0, desktop).

ШАГИ:
1. Google Cloud Console → проект → включить «YouTube Data API v3»
2. OAuth consent screen → External → добавить себя в test users
   (scopes добавляются автоматически из кода ниже)
3. Credentials → Create OAuth client ID → Desktop → client_id / client_secret
4. Запустить:  python youtube_oauth.py --client-id XXX --client-secret YYY
5. Открыть ссылку, войти каналом, разрешить доступ
6. Скрипт сам поймает code и напечатает refresh_token + channel_id
7. Эти значения вставить в панель: Подключения → publish → youtube

Требуется: python3 + httpx (pip install httpx)
"""
import argparse
import http.server
import threading
import urllib.parse

import httpx

SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube",
    ]
)
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT = "http://127.0.0.1:8080/"


def exchange(client_id: str, client_secret: str, code: str) -> dict:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    return resp.json()


def channel_id(access_token: str) -> str:
    resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet,contentDetails", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0]["id"] if items else ""


def main():
    parser = argparse.ArgumentParser(description="OAuth для YouTube Data API")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument(
        "--manual", action="store_true",
        help="вручную вставить code (если браузер не открывает localhost)",
    )
    args = parser.parse_args()

    auth_url = (
        f"{AUTH_URL}?client_id={args.client_id}&redirect_uri={urllib.parse.quote(REDIRECT)}"
        f"&response_type=code&scope={urllib.parse.quote(SCOPES)}&access_type=offline&prompt=consent"
    )
    print("1) Откройте ссылку и войдите аккаунтом, на который будете публиковать:")
    print("\n   " + auth_url + "\n")

    if args.manual:
        code = input("2) Вставьте code из адресной строки (после ?code=): ").strip()
    else:
        code_holder: dict = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                code_holder["code"] = q.get("code", [""])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK, можно закрыть вкладку")

            def log_message(self, *a):  # тишина
                pass

        server = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
        threading.Thread(target=server.handle_request, daemon=True).start()
        print("2) После авторизации браузер откроет 127.0.0.1:8080 — скрипт подхватит code сам")
        print("   (если не сработает — запустите с флагом --manual)")
        while not code_holder.get("code"):
            import time

            time.sleep(0.3)
        code = code_holder["code"]

    tokens = exchange(args.client_id, args.client_secret, code)
    refresh = tokens["refresh_token"]
    access = tokens["access_token"]
    cid = channel_id(access)
    print("\n=== РЕЗУЛЬТАТ (вставьте в панель) ===")
    print(f"client_id:     {args.client_id}")
    print(f"client_secret: {args.client_secret}")
    print(f"refresh_token: {refresh}")
    print(f"channel_id:    {cid}")
    print("\nПанель: Подключения → publish → youtube → заполнить 4 поля → Сохранить.")


if __name__ == "__main__":
    main()
