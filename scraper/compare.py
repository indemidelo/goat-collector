"""
Confronta le carte richieste dai mazzi con la collezione dell'utente e
ritorna le carte mancanti, raggruppate per carta (non per mazzo).
"""


def missing_cards_for_deck(deck, owned_collection, excluded_names=None):
    """
    deck: {"id", "name", "cards": [{"name", "quantity"}, ...], ...}
    owned_collection: {card_name: quantity_owned}
    excluded_names: set di nomi carta da ignorare sempre (es. Unwanted Cards)

    Ritorna una lista di dict: [{"name", "needed", "owned", "missing"}, ...]
    Solo le carte con missing > 0 vengono incluse.
    """
    excluded_names = excluded_names or set()
    missing = []
    for card in deck.get("cards", []):
        name = card["name"]
        if name in excluded_names:
            continue
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


def build_report(new_decks, owned_collection, excluded_names=None):
    """
    Raggruppamento per CARTA mancante (non per mazzo).

    excluded_names: set di nomi carta da escludere sempre dal report
    (es. dalla scheda "Unwanted Cards"), indipendentemente da prezzo o
    possesso.

    Ritorna una lista ordinata alfabeticamente per nome carta:
    [
      {
        "card_name": "Sinister Serpent",
        "decks": [
          {"deck_name", "deck_url", "event_name", "missing"},
          ...
        ]
      },
      ...
    ]
    "missing" qui è quanto manca di quella carta PER QUEL SPECIFICO mazzo
    (può variare da mazzo a mazzo se ne servono quantità diverse).
    """
    by_card = {}

    for deck in new_decks:
        missing = missing_cards_for_deck(deck, owned_collection, excluded_names)
        for card in missing:
            entry = by_card.setdefault(card["name"], [])
            entry.append({
                "deck_name": deck.get("name") or deck["id"],
                "deck_url": deck.get("url"),
                "event_name": deck.get("event_name"),
                "missing": card["missing"],
            })

    report = [
        {"card_name": name, "decks": decks}
        for name, decks in sorted(by_card.items())
    ]
    return report
