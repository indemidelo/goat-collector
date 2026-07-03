"""
Confronta le carte richieste da un mazzo con la collezione dell'utente e
ritorna solo ciò che manca.
"""


def missing_cards_for_deck(deck, owned_collection):
    """
    deck: {"id", "name", "cards": [{"name", "quantity"}, ...], ...}
    owned_collection: {card_name: quantity_owned}

    Ritorna una lista di dict: [{"name", "needed", "owned", "missing"}, ...]
    Solo le carte con missing > 0 vengono incluse.
    """
    missing = []
    for card in deck.get("cards", []):
        name = card["name"]
        needed = card.get("quantity", 1)
        owned = owned_collection.get(name, 0)
        gap = needed - owned
        if gap > 0:
            missing.append({
                "name": name,
                "needed": needed,
                "owned": owned,
                "missing": gap,
            })
    return missing


def build_report(new_decks, owned_collection):
    """
    Ritorna una lista di dict per i mazzi che hanno almeno una carta
    mancante: [{"deck_name", "deck_url", "missing_cards": [...]}, ...]
    """
    report = []
    for deck in new_decks:
        missing = missing_cards_for_deck(deck, owned_collection)
        if missing:
            report.append({
                "deck_id": deck["id"],
                "deck_name": deck.get("name") or deck["id"],
                "deck_url": deck.get("url"),
                "event_name": deck.get("event_name"),
                "missing_cards": missing,
            })
    return report
