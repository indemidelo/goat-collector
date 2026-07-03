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


def _delete_message(message_id):
    url = f"https://api.telegram.org/bot{_bot_token()}/deleteMessage"
    try:
        resp = requests.post(url, data={
            "chat_id": _chat_id(),
            "message_id": message_id,
        }, timeout=15)
        # Non solleviamo eccezioni: un messaggio già cancellato o più
        # vecchio di 48 ore fa fallire la delete, ma non deve bloccare
        # l'invio del nuovo report. Controlliamo sia lo status HTTP sia il
        # campo "ok" nel body (Telegram a volte risponde 200 con ok:false).
        body = resp.json()
        if not resp.ok or not body.get("ok", False):
            print(f"  ⚠️  Impossibile cancellare il messaggio {message_id}: {body}")
        else:
            print(f"  🗑️  Messaggio {message_id} cancellato.")
    except requests.RequestException as e:
        print(f"  ⚠️  Errore cancellando il messaggio {message_id}: {e}")


def _send_message(text):
    """Ritorna il message_id del messaggio inviato."""
    url = f"https://api.telegram.org/bot{_bot_token()}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": _chat_id(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["result"]["message_id"]


def format_report(report):
    """Trasforma il report (raggruppato per carta) in una lista di stringhe."""
    if not report:
        return ["✅ Nessuna carta mancante al momento su tutti i mazzi conosciuti."]

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


def replace_report(report, previous_message_ids):
    """
    Cancella tutti i messaggi precedenti (previous_message_ids) e invia il
    nuovo report, così la chat resta sempre con un'unica lista aggiornata
    di carte mancanti. Ritorna la lista dei nuovi message_id inviati (da
    salvare per la prossima esecuzione).
    """
    for message_id in previous_message_ids:
        _delete_message(message_id)

    new_ids = []
    for chunk in format_report(report):
        new_ids.append(_send_message(chunk))
    return new_ids
