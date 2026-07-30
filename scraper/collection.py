"""
Gestione della collezione dell'utente e dello storico dei mazzi già
processati, salvati in un piccolo database SQLite (data/state.db).
"""

import csv
import io
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

import requests

from . import selectors

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "state.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collection (
            card_name TEXT PRIMARY KEY,
            quantity INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_decks (
            deck_id TEXT PRIMARY KEY,
            deck_name TEXT,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_events (
            event_id TEXT PRIMARY KEY,
            abbreviation TEXT,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deck_requirements (
            deck_id TEXT,
            card_name TEXT,
            needed INTEGER NOT NULL,
            deck_name TEXT,
            deck_url TEXT,
            event_name TEXT,
            PRIMARY KEY (deck_id, card_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_messages (
            message_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    return conn


def import_collection_csv(csv_path):
    """Importa/aggiorna la collezione da un file CSV locale (card_name, quantity)."""
    conn = init_db()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [(r["card_name"].strip(), int(r["quantity"])) for r in reader]

    conn.executemany(
        """INSERT INTO collection (card_name, quantity) VALUES (?, ?)
           ON CONFLICT(card_name) DO UPDATE SET quantity = excluded.quantity""",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def import_collection_from_sheets():
    """
    Importa/aggiorna la collezione leggendo le schede Google Sheets
    pubblicate (vedi selectors.COLLECTION_SHEET_URLS). Una riga = una copia
    posseduta; viene contata solo se ha un valore non vuoto nella colonna
    Prezzo (le carte senza prezzo si considerano non ancora acquisite).

    Sostituisce interamente la collezione precedente in DB con quella
    ricalcolata dal foglio (così eventuali rimozioni sul foglio si
    riflettono anche nel bot).
    """
    name_col = selectors.COLLECTION_SHEET_COLUMNS["name_column"]
    price_col = selectors.COLLECTION_SHEET_COLUMNS["price_column"]

    counter = Counter()
    for sheet_label, url in selectors.COLLECTION_SHEET_URLS.items():
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        # Il CSV pubblicato da Google può includere un BOM UTF-8
        text = resp.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            name = (row.get(name_col) or "").strip()
            price = (row.get(price_col) or "").strip()
            if not name:
                continue
            if not price:
                continue  # nessun prezzo -> non ancora posseduta
            counter[name] += 1

    conn = init_db()
    conn.execute("DELETE FROM collection")  # ricalcolo completo da zero
    conn.executemany(
        "INSERT INTO collection (card_name, quantity) VALUES (?, ?)",
        list(counter.items()),
    )
    conn.commit()
    conn.close()
    return sum(counter.values()), len(counter)


def get_unwanted_cards():
    """
    Legge la scheda "Unwanted Cards" (colonne Nome + URL, dove ogni riga è
    un MAZZO da escludere per intero): scarica ciascun mazzo elencato
    tramite lo stesso meccanismo usato per gli eventi, e unisce tutte le
    sue carte in un set di nomi da escludere sempre dalle notifiche,
    indipendentemente da prezzo o possesso.
    """
    # Import qui (non in cima al file) per evitare un giro di import
    # circolare: fetch_decks non importa collection, quindi va bene, ma
    # teniamolo locale per chiarezza del perché serve solo qui.
    from . import fetch_decks

    url_col = selectors.UNWANTED_DECKS_URL_COLUMN
    name_col = selectors.UNWANTED_DECKS_NAME_COLUMN

    resp = requests.get(selectors.UNWANTED_CARDS_SHEET_URL, timeout=20)
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    unwanted = set()
    for row in reader:
        deck_url = (row.get(url_col) or "").strip()
        label = (row.get(name_col) or "").strip()
        if not deck_url:
            continue

        match = re.search(r"/decks/(\d+)", deck_url)
        if not match:
            print(f"  ⚠️  URL mazzo non riconosciuto in Unwanted Cards ({label or deck_url})")
            continue
        deck_id = match.group(1)

        try:
            detail = fetch_decks.fetch_deck_detail(deck_id)
        except Exception as e:
            print(f"  ⚠️  Errore leggendo mazzo unwanted {deck_id} ({label}): {e}")
            continue

        for card in detail["cards"]:
            unwanted.add(card["name"])

        time.sleep(1.0)  # gentile col server, come per gli altri fetch

    return unwanted


def get_collection():
    """Ritorna un dict {card_name: quantity}."""
    conn = init_db()
    rows = conn.execute("SELECT card_name, quantity FROM collection").fetchall()
    conn.close()
    return {name: qty for name, qty in rows}


def get_seen_deck_ids():
    conn = init_db()
    rows = conn.execute("SELECT deck_id FROM seen_decks").fetchall()
    conn.close()
    return {r[0] for r in rows}


def mark_decks_seen(decks):
    """decks: lista di dict con almeno 'id' e 'name'."""
    conn = init_db()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_decks (deck_id, deck_name) VALUES (?, ?)",
        [(d["id"], d.get("name")) for d in decks],
    )
    conn.commit()
    conn.close()


def get_seen_event_ids():
    conn = init_db()
    rows = conn.execute("SELECT event_id FROM seen_events").fetchall()
    conn.close()
    return {r[0] for r in rows}


def mark_events_seen(events):
    """events: lista di dict con almeno 'id' e 'abbreviation'."""
    conn = init_db()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_events (event_id, abbreviation) VALUES (?, ?)",
        [(e["id"], e.get("abbreviation")) for e in events],
    )
    conn.commit()
    conn.close()


def save_deck_requirements(decks):
    """
    Salva TUTTE le carte richieste da ciascun mazzo (non solo quelle
    mancanti al momento), così che ai run successivi si possa ricalcolare
    cosa manca in base alla collezione aggiornata, anche per mazzi già
    visti in passato.

    decks: lista di dict {id, name, url, event_name, cards: [{name, quantity}]}
    """
    conn = init_db()
    rows = []
    for deck in decks:
        for card in deck.get("cards", []):
            rows.append((
                deck["id"],
                card["name"],
                card.get("quantity", 1),
                deck.get("name"),
                deck.get("url"),
                deck.get("event_name"),
            ))
    conn.executemany(
        """INSERT OR REPLACE INTO deck_requirements
           (deck_id, card_name, needed, deck_name, deck_url, event_name)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    conn.close()


def get_all_known_decks():
    """
    Ricostruisce, da deck_requirements, tutti i mazzi mai visti nel formato
    atteso da compare.build_report: [{id, name, url, event_name, cards: [...]}]
    """
    conn = init_db()
    rows = conn.execute(
        "SELECT deck_id, card_name, needed, deck_name, deck_url, event_name FROM deck_requirements"
    ).fetchall()
    conn.close()

    decks_by_id = {}
    for deck_id, card_name, needed, deck_name, deck_url, event_name in rows:
        deck = decks_by_id.setdefault(deck_id, {
            "id": deck_id,
            "name": deck_name,
            "url": deck_url,
            "event_name": event_name,
            "cards": [],
        })
        deck["cards"].append({"name": card_name, "quantity": needed})

    return list(decks_by_id.values())


def get_last_message_ids():
    conn = init_db()
    rows = conn.execute("SELECT message_id FROM sent_messages").fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_last_message_ids(message_ids):
    conn = init_db()
    conn.execute("DELETE FROM sent_messages")
    conn.executemany(
        "INSERT INTO sent_messages (message_id) VALUES (?)",
        [(mid,) for mid in message_ids],
    )
    conn.commit()
    conn.close()
