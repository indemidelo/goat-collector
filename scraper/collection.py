"""
Gestione della collezione dell'utente e dello storico dei mazzi già
processati, salvati in un piccolo database SQLite (data/state.db).
"""

import csv
import io
import sqlite3
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
