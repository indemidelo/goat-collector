"""
Endpoint API di formatlibrary.com, confermati leggendo il codice sorgente
pubblico (MIT license) del sito: github.com/dwmcnelis/formatlibrary-backup
(file server/api/events.js e server/api/decks.js). Non sono placeholder
indovinati: sono le stesse rotte usate dal sito stesso nel browser.

Gerarchia a 3 livelli:
  1. Eventi recenti di un formato  -> EVENTS_RECENT_URL
  2. Dettaglio evento (mazzi top)  -> EVENT_DETAIL_URL
  3. Dettaglio mazzo (carte)       -> DECK_DETAIL_URL

Nota bene: questi endpoint restituiscono solo ciò che il sito mostra
pubblicamente (rispettano lo stesso flag "display" usato dal frontend), non
serve nessuna sessione/abbonamento per i mazzi pubblici.
"""

FORMAT_NAME = "Goat"  # nome esatto del formato come atteso dall'API (case-insensitive)

# Livello 1: eventi recenti per formato. Ritorna gli ultimi 6 eventi.
# Risposta: {"events": [...], "winners": [...]}
EVENTS_RECENT_URL = "https://formatlibrary.com/api/events/recent/{format}"

# Livello 2: dettaglio di un evento, tramite la sua "abbreviation" (es. SESB18).
# Risposta: {"event": {...}, "winner": {...}, "topDecks": [{id, type, builder, placement}, ...], "metagame": {...}}
EVENT_DETAIL_URL = "https://formatlibrary.com/api/events/{abbreviation}"

# Livello 3: dettaglio di un mazzo, tramite il suo id numerico (es. 79777).
# Risposta include: main, extra, side -> liste di oggetti carta con "name" già risolto
DECK_DETAIL_URL = "https://formatlibrary.com/api/decks/{deck_id}"

# Campi usati dal parser per ogni livello (nomi confermati dal codice sorgente)
EVENT_FIELDS = {
    "id_field": "id",
    "abbreviation_field": "abbreviation",
    "name_field": "name",
    "date_field": "startDate",
}

DECK_SUMMARY_FIELDS = {  # dentro topDecks
    "id_field": "id",
    "type_field": "type",       # nome archetipo/mazzo, es. "Chaos Control"
    "builder_field": "builder",  # nome di chi ha caricato/giocato il mazzo
    "placement_field": "placement",
}

DECK_DETAIL_SECTIONS = ["main", "extra", "side"]  # ognuna è una lista di {"name": ...}

# Se in futuro servisse una sessione autenticata (es. per contenuti premium
# a cui hai legittimamente accesso), imposta qui i cookie della TUA sessione
# (da DevTools -> Application -> Cookies dopo login manuale nel browser).
# NON committare mai questo valore reale su un repo pubblico: usa un GitHub
# Secret (vedi README). Ad oggi non è necessario per i mazzi pubblici.
SESSION_COOKIE = None  # es: "session=abc123; other=xyz"

# Collezione: schede Google Sheets pubblicate come CSV (File -> Condividi ->
# Pubblica sul web -> singola scheda -> formato CSV). Ogni volta che il
# foglio viene modificato, questi link restituiscono automaticamente i dati
# aggiornati (con qualche minuto di ritardo per la ripubblicazione).
COLLECTION_SHEET_URLS = {
    "Mostri Effetto": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQT99FFtHxN6zc8-o0wp3LtZUSW74FrDaMwxu-_9E7ySSpMvALbWSZG1qlesCrUMQcDshlaUu5aZ82S/pub?gid=0&single=true&output=csv",
    "Mostri Fusione": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQT99FFtHxN6zc8-o0wp3LtZUSW74FrDaMwxu-_9E7ySSpMvALbWSZG1qlesCrUMQcDshlaUu5aZ82S/pub?gid=974724877&single=true&output=csv",
    "Magie": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQT99FFtHxN6zc8-o0wp3LtZUSW74FrDaMwxu-_9E7ySSpMvALbWSZG1qlesCrUMQcDshlaUu5aZ82S/pub?gid=1167948534&single=true&output=csv",
    "Trappole": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQT99FFtHxN6zc8-o0wp3LtZUSW74FrDaMwxu-_9E7ySSpMvALbWSZG1qlesCrUMQcDshlaUu5aZ82S/pub?gid=903842204&single=true&output=csv",
}

# Nomi delle colonne nel Google Sheet (devono combaciare con l'intestazione
# reale del foglio). Una carta viene contata come posseduta solo se ha un
# valore non vuoto nella colonna Prezzo.
COLLECTION_SHEET_COLUMNS = {
    "name_column": "Nome",
    "price_column": "Prezzo",
}
