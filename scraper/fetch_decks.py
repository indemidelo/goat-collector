"""
Scarica eventi -> mazzi -> carte da formatlibrary.com usando gli endpoint
API reali del sito (confermati leggendo il codice sorgente pubblico,
vedi selectors.py). Rispetta la gerarchia:

    eventi recenti del formato -> dettaglio evento (mazzi top) -> carte del mazzo
"""

import time
import requests

from . import selectors


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GoatCollectorBot/1.0; personal collection tracker)",
    "Accept": "application/json",
}


def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    if selectors.SESSION_COOKIE:
        s.headers["Cookie"] = selectors.SESSION_COOKIE
    return s


def fetch_recent_events(format_name=None):
    """Livello 1: ritorna gli eventi recenti del formato (default: Goat)."""
    format_name = format_name or selectors.FORMAT_NAME
    s = _session()
    url = selectors.EVENTS_RECENT_URL.format(format=format_name)
    resp = s.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    cfg = selectors.EVENT_FIELDS
    events = []
    for item in payload.get("events", []):
        events.append({
            "id": item.get(cfg["id_field"]),
            "abbreviation": item.get(cfg["abbreviation_field"]),
            "name": item.get(cfg["name_field"]),
            "date": item.get(cfg["date_field"]),
        })
    return events


def fetch_event_detail(abbreviation):
    """Livello 2: dettaglio evento, ritorna la lista dei suoi mazzi top."""
    s = _session()
    url = selectors.EVENT_DETAIL_URL.format(abbreviation=abbreviation)
    resp = s.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    cfg = selectors.DECK_SUMMARY_FIELDS
    decks = []
    for item in payload.get("topDecks", []):
        decks.append({
            "id": item.get(cfg["id_field"]),
            "type": item.get(cfg["type_field"]),
            "builder": item.get(cfg["builder_field"]),
            "placement": item.get(cfg["placement_field"]),
        })
    return decks


def fetch_deck_detail(deck_id):
    """
    Livello 3: dettaglio mazzo. Ritorna sia le carte (main+extra+side,
    tallied per nome) sia type/builder letti dal dettaglio stesso — la
    stessa fonte dati che alimenta la pagina del mazzo sul sito, quindi
    più affidabile del campo "type" restituito nel riepilogo topDecks
    dell'evento (che a volte risulta vuoto).
    """
    s = _session()
    url = selectors.DECK_DETAIL_URL.format(deck_id=deck_id)
    resp = s.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    counts = {}
    for section in selectors.DECK_DETAIL_SECTIONS:
        for card in payload.get(section, []):
            name = card.get("name")
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1

    return {
        "type": payload.get("type"),
        "builder": payload.get("builder"),
        "cards": [{"name": name, "quantity": qty} for name, qty in counts.items()],
    }


def _capitalize_words(s):
    """Replica la funzione capitalize(str, eachWord=true) del sito originale."""
    if not s:
        return s
    return " ".join(word[:1].upper() + word[1:] if word else word for word in s.split(" "))


def fetch_new_decks(seen_event_ids, seen_deck_ids, max_events=None, delay_seconds=1.5):
    """
    Ritorna: (nuovi_mazzi_con_carte, eventi_processati)

    nuovi_mazzi_con_carte: lista di dict {id, name, url, cards: [...], event_name}
    eventi_processati: lista di dict evento, da segnare come "visti"
    """
    events = fetch_recent_events()
    new_events = [e for e in events if e["id"] not in seen_event_ids]

    if max_events:
        new_events = new_events[:max_events]

    all_new_decks = []
    processed_events = []

    for event in new_events:
        try:
            deck_summaries = fetch_event_detail(event["abbreviation"])
        except Exception as e:
            print(f"  ⚠️  Errore leggendo evento {event['abbreviation']}: {e}")
            continue

        for deck in deck_summaries:
            if deck["id"] in seen_deck_ids:
                continue
            time.sleep(delay_seconds)  # gentile col server
            try:
                detail = fetch_deck_detail(deck["id"])
            except Exception as e:
                print(f"  ⚠️  Errore leggendo mazzo {deck['id']}: {e}")
                continue

            # Preferiamo type/builder dal dettaglio del mazzo (più
            # affidabile); se anche quello è vuoto, ripieghiamo sul
            # riepilogo dell'evento, poi sull'id come ultima risorsa.
            raw_type = detail.get("type") or deck.get("type")
            builder = detail.get("builder") or deck.get("builder")

            deck_name = _capitalize_words(raw_type) or f"Deck {deck['id']}"
            display_name = f"{deck_name} ({builder})" if builder else deck_name

            all_new_decks.append({
                "id": deck["id"],
                "name": display_name,
                "url": f"https://formatlibrary.com/decks/{deck['id']}",
                "cards": detail["cards"],
                "event_name": event["name"],
            })

        processed_events.append(event)
        time.sleep(delay_seconds)

    return all_new_decks, processed_events
