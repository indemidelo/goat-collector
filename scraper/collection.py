"""
Gestione della collezione dell'utente e dello storico dei mazzi già
processati, salvati in un piccolo database SQLite (data/state.db).
"""

import csv
import sqlite3
from pathlib import Path

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
    """Importa/aggiorna la collezione da un file CSV (card_name, quantity)."""
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
