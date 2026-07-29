"""
Invia il report delle carte mancanti su Telegram: un messaggio-foto per
ogni carta mancante (immagine da YGOPRODeck + didascalia con i mazzi che
la richiedono). Se l'immagine non si trova, fa fallback a solo testo.
"""

import os
import time
import requests

from . import card_images

TELEGRAM_MAX_LEN = 4000  # margine di sicurezza sotto il limite reale di 4096
PHOTO_CAPTION_MAX_LEN = 1000  # margine sotto il limite di 1024 per le didascalie foto


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


def _send_photo(photo_url, caption):
    """Ritorna il message_id del messaggio-foto inviato."""
    url = f"https://api.telegram.org/bot{_bot_token()}/sendPhoto"
    resp = requests.post(url, data={
        "chat_id": _chat_id(),
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }, timeout=20)
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


def _format_card_caption(entry):
    """Didascalia per un singolo messaggio-foto, entro il limite di 1024 caratteri."""
    lines = [f"🃏 <b>{entry['card_name']}</b>"]
    decks = entry["decks"]

    shown = 0
    for deck in decks:
        label = deck["deck_name"]
        if deck.get("event_name"):
            label += f" — {deck['event_name']}"
        if deck.get("deck_url"):
            label = f'<a href="{deck["deck_url"]}">{label}</a>'
        line = f"  • mancano {deck['missing']} — {label}"

        candidate_len = len("\n".join(lines + [line]))
        if candidate_len > PHOTO_CAPTION_MAX_LEN:
            remaining = len(decks) - shown
            lines.append(f"  … e altri {remaining} mazzi")
            break

        lines.append(line)
        shown += 1

    return "\n".join(lines)


def replace_report_with_images(report, previous_message_ids):
    """
    Come replace_report, ma invia un messaggio-foto per ogni carta mancante
    (immagine da YGOPRODeck + didascalia con i mazzi che la richiedono).
    Se l'immagine non si trova, fa fallback a un messaggio di solo testo
    per quella carta. Ritorna la lista dei nuovi message_id inviati.
    """
    for message_id in previous_message_ids:
        _delete_message(message_id)

    if not report:
        return [_send_message("✅ Nessuna carta mancante al momento su tutti i mazzi conosciuti.")]

    new_ids = []
    for entry in report:
        caption = _format_card_caption(entry)
        image_url = card_images.get_card_image_url(entry["card_name"])

        message_id = None
        if image_url:
            try:
                message_id = _send_photo(image_url, caption)
            except requests.RequestException as e:
                print(f"  ⚠️  Errore inviando foto per '{entry['card_name']}': {e}")

        if message_id is None:
            # Fallback: niente immagine trovata, o invio foto fallito
            message_id = _send_message(caption)

        new_ids.append(message_id)
        time.sleep(0.3)  # gentile con l'API di YGOPRODeck e con Telegram

    return new_ids
