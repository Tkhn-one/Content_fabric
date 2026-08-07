"""Получение chat_id для Telegram-публикации.

ШАГИ:
1. @BotFather → /newbot → получить bot_token
2. Написать боту любое сообщение (/start)
3. Запустить:  python telegram_chat.py --token BOT_TOKEN
4. Скрипт покажет chat_id — вставить в панель: publish → telegram → chat_id

Требуется: python3 + httpx
"""
import argparse

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="bot token от @BotFather")
    args = parser.parse_args()

    resp = httpx.get(f"https://api.telegram.org/bot{args.token}/getUpdates", timeout=30)
    resp.raise_for_status()
    updates = resp.json().get("result", [])
    if not updates:
        print("Нет сообщений. Напишите боту в Telegram любое сообщение и запустите ещё раз.")
        return
    chat = updates[0]["message"]["chat"]
    print(f"\nchat_id: {chat['id']}")
    print(f"название: {chat.get('title', chat.get('first_name', ''))} (тип: {chat.get('type')})")
    print("\nПанель: Подключения → publish → telegram → bot_token + chat_id → Сохранить.")


if __name__ == "__main__":
    main()
