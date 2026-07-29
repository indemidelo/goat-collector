"""
Recupera l'immagine di una carta Yu-Gi-Oh! da YGOPRODeck
(db.ygoprodeck.com), un database pubblico e gratuito molto usato per
progetti come questo. Nessuna chiave API richiesta.
"""

import requests

YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


def get_card_image_url(card_name):
    """
    Ritorna l'URL dell'immagine della carta (versione leggera), oppure
    None se la carta non viene trovata o c'è un errore di rete/API.
    """
    try:
        resp = requests.get(YGOPRODECK_API, params={"name": card_name}, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    cards = data.get("data") or []
    if not cards:
        return None

    images = cards[0].get("card_images") or []
    if not images:
        return None

    return images[0].get("image_url_small") or images[0].get("image_url")
