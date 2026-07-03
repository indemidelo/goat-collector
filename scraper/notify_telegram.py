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
    """Trasforma il report (raggruppato per carta) in una lista di stringhe."""
    if not report:
        return ["✅ Nessun nuovo mazzo Goat Format con carte mancanti oggi."]

    n_cards = len(report)
    label = "carta mancante" if n_cards == 1 else "carte mancanti"
    lines = [f"🐐 <b>{n_cards} {label} nei nuovi mazzi</b>\n"]

    for entry in report:
        lines.append(f"\n🃏 <b>{entry['card_name']}</b>")
        for deck in entry["decks"]:
            label = deck["deck_name"]
            if deck.get("event_name"):
                label += f" — {deck['event_name']}"
            if deck.get("deck_url"):
                label = f'<a href="{deck["deck_url"]}">{label}</a>'
            lines.append(f"  • mancano {deck['missing']} — {label}")

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
