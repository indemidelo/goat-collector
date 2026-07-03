"""
Orchestratore principale. Eseguito ogni giorno dal workflow GitHub Actions
(vedi .github/workflows/daily.yml), ma puoi lanciarlo anche a mano:

    python main.py
"""

import sys
from pathlib import Path

from scraper import collection, compare, notify_telegram
from scraper import fetch_decks

COLLECTION_CSV = Path(__file__).resolve().parent / "collection.csv"


def main():
    print("→ Import collezione da CSV...")
    n = collection.import_collection_csv(COLLECTION_CSV)
    print(f"  {n} carte importate/aggiornate.")

    owned = collection.get_collection()
    seen_event_ids = collection.get_seen_event_ids()
    seen_deck_ids = collection.get_seen_deck_ids()
    print(f"  Eventi già visti in precedenza: {len(seen_event_ids)}")

    print("→ Controllo nuovi eventi/mazzi Goat Format su formatlibrary.com...")
    try:
        new_decks, processed_events = fetch_decks.fetch_new_decks(seen_event_ids, seen_deck_ids)
    except Exception as e:
        print(f"❌ Errore durante lo scraping: {e}", file=sys.stderr)
        print("   Controlla scraper/selectors.py: gli endpoint API potrebbero")
        print("   essere cambiati rispetto a quanto confermato nel codice sorgente.")
        sys.exit(1)

    print(f"  Nuovi eventi processati: {len(processed_events)}")
    print(f"  Nuovi mazzi trovati: {len(new_decks)}")

    if new_decks:
        report = compare.build_report(new_decks, owned)
        print(f"  {len(report)} mazzi hanno carte mancanti nella tua collezione.")
        notify_telegram.send_report(report)
        collection.mark_decks_seen(new_decks)
    else:
        print("  Nessun mazzo nuovo, nessuna notifica da inviare.")

    if processed_events:
        collection.mark_events_seen(processed_events)

    print("✅ Fatto.")


if __name__ == "__main__":
    main()
