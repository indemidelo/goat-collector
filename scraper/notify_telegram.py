"""
Invia il report delle carte mancanti su Telegram, splittando in più
messaggi se troppo lungo (limite Telegram: 4096 caratteri per messaggio).
"""

import os
import requests

TELEGRAM_MAX_LEN = 4000  # margine di sicurezza sotto il limite reale di 4096


def _bot_token():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Variabile d'ambiente TELEGRAM_BOT_TOKEN mancante")
    return token


def _chat_id():
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("Variabile d'ambiente TELEGRAM_CHAT_ID mancante")
    return chat_id


def _send_message(text):
    url = f"https://api.telegram.org/bot{_bot_token()}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": _chat_id(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=15)
    resp.raise_for_status()


def format_report(report):
    """Trasforma il report in una lista di stringhe (una per chunk di messaggio)."""
    if not report:
        return ["✅ Nessun nuovo mazzo Goat Format con carte mancanti oggi."]

    lines = [f"🐐 <b>{len(report)} nuovo/i mazzo/i Goat Format con carte mancanti</b>\n"]

    for entry in report:
        header = f"\n<b>{entry['deck_name']}</b>"
        if entry.get("event_name"):
            header += f" — {entry['event_name']}"
        lines.append(header)
        if entry.get("deck_url"):
            lines.append(entry["deck_url"])
        for card in entry["missing_cards"]:
            lines.append(
                f"  • {card['name']}: hai {card['owned']}/{card['needed']} "
                f"(mancano {card['missing']})"
            )

    full_text = "\n".join(lines)

    # Split in chunk se troppo lungo
    chunks = []
    current = ""
    for line in full_text.split("\n"):
        if len(current) + len(line) + 1 > TELEGRAM_MAX_LEN:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    return chunks


def send_report(report):
    for chunk in format_report(report):
        _send_message(chunk)
