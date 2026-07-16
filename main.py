"""
Orchestratore principale. Eseguito ogni giorno dal workflow GitHub Actions
(vedi .github/workflows/daily.yml), ma puoi lanciarlo anche a mano:

    python main.py
"""

import sys

from scraper import collection, compare, notify_telegram
from scraper import fetch_decks


def main():
    print("→ Import collezione da Google Sheets...")
    n_copies, n_unique = collection.import_collection_from_sheets()
    print(f"  {n_unique} carte uniche, {n_copies} copie totali importate.")

    print("→ Import carte indesiderate (Unwanted Cards)...")
    unwanted = collection.get_unwanted_cards()
    print(f"  {len(unwanted)} carte da escludere sempre dalle notifiche.")

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
        collection.save_deck_requirements(new_decks)
        collection.mark_decks_seen(new_decks)
    if processed_events:
        collection.mark_events_seen(processed_events)

    # Ricalcolo COMPLETO: confrontiamo la collezione aggiornata con TUTTI i
    # mazzi mai visti (non solo quelli nuovi di oggi), così se nel frattempo
    # hai comprato una carta, sparisce dalla lista anche senza nuovi mazzi.
    all_known_decks = collection.get_all_known_decks()
    report = compare.build_report(all_known_decks, owned, excluded_names=unwanted)
    print(f"  {len(report)} carte mancanti in totale su {len(all_known_decks)} mazzi conosciuti.")

    previous_message_ids = collection.get_last_message_ids()
    print(f"  Message_id precedenti trovati in state.db: {previous_message_ids}")

    new_message_ids = notify_telegram.replace_report(report, previous_message_ids)
    print(f"  Nuovi message_id inviati: {new_message_ids}")

    collection.set_last_message_ids(new_message_ids)
    print(f"  Salvati in state.db per il prossimo run.")

    print("✅ Fatto.")


if __name__ == "__main__":
    main()
