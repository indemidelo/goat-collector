# Goat Collector Bot

Bot che ogni giorno controlla i nuovi mazzi Goat Format su formatlibrary.com,
confronta le carte richieste con la tua collezione personale, e ti manda su
Telegram la lista delle carte che ti mancano.

## Struttura del progetto

```
goat-collector/
├── collection.csv          # La tua collezione (tu la mantieni)
├── data/
│   └── state.db              # DB SQLite: eventi/mazzi già visti + collezione
├── scraper/
│   ├── fetch_decks.py         # Eventi -> mazzi -> carte (API reale)
│   ├── selectors.py           # Endpoint API confermati dal codice sorgente
│   ├── collection.py          # Import CSV + gestione collezione + stato
│   ├── compare.py             # Confronto carte mancanti
│   └── notify_telegram.py     # Invio notifica Telegram
├── main.py                    # Orchestratore, eseguito dal workflow
├── requirements.txt
└── .github/workflows/daily.yml # Il cron che fa girare tutto ogni giorno
```

## Come funziona lo scraping — gerarchia a 3 livelli

Il sito organizza i dati così: **formato → eventi → mazzi → carte**. Il bot
segue esattamente questa gerarchia, usando le stesse API interne che usa il
sito nel browser (confermate leggendo il codice sorgente pubblico del sito,
MIT license: github.com/dwmcnelis/formatlibrary-backup):

1. `GET /api/events/recent/Goat` → gli eventi Goat Format più recenti
2. `GET /api/events/{abbreviation}` → per ogni evento nuovo, i mazzi top
   (es. `formatlibrary.com/events/SESB18`)
3. `GET /api/decks/{id}` → per ogni mazzo nuovo, le carte (main/extra/side)
   (es. `formatlibrary.com/decks/79777`)

Questi endpoint restituiscono solo ciò che è **già pubblicamente visibile**
sul sito (rispettano lo stesso flag di visibilità usato dal frontend), quindi
non serve nessun login per i mazzi pubblici. Il bot tiene traccia sia degli
eventi sia dei mazzi già processati in `data/state.db`, così ogni giorno
controlla solo le novità.

Se in futuro il sito cambia struttura e gli endpoint smettono di funzionare,
i valori da aggiornare sono tutti centralizzati in `scraper/selectors.py`.

## Passo 1 — La tua collezione (Google Sheets, sempre aggiornata)

Il bot legge la collezione direttamente dal tuo Google Sheet ad ogni
esecuzione — non serve più esportare/caricare un CSV a mano. Le 4 schede
collegate (Mostri Effetto, Mostri Fusione, Magie, Trappole) sono già
configurate in `scraper/selectors.py` (`COLLECTION_SHEET_URLS`).

Una riga nel foglio = una copia posseduta; viene contata solo se ha un
valore nella colonna **Prezzo** (senza prezzo = non ancora acquisita).
Ogni volta che modifichi il foglio, la versione pubblicata si aggiorna da
sola dopo qualche minuto — il prossimo run del bot vedrà i dati freschi.

Se in futuro aggiungi/rimuovi schede o cambi struttura al foglio, aggiorna
`COLLECTION_SHEET_URLS` e `COLLECTION_SHEET_COLUMNS` in
`scraper/selectors.py` di conseguenza. Il file `collection.csv` nel
progetto resta solo come riferimento/fallback manuale (funzione
`import_collection_csv`, non più usata da `main.py`).

## Passo 2 — Bot Telegram

1. Su Telegram cerca **@BotFather**, invia `/newbot`, segui le istruzioni →
   ottieni un **token**
2. Scrivi un messaggio al tuo nuovo bot (qualsiasi cosa, es. "ciao")
3. Vai su `https://api.telegram.org/bot<TOKEN>/getUpdates` nel browser →
   trovi il tuo **chat_id** nel JSON di risposta (`message.chat.id`)

## Passo 3 — GitHub

1. Crea un repository (anche privato) e carica questi file
2. Vai su Settings → Secrets and variables → Actions → New repository secret
   e aggiungi:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Il workflow in `.github/workflows/daily.yml` gira ogni giorno alle 9:00
   UTC automaticamente. Puoi anche lanciarlo a mano da Actions → "Daily Goat
   Scan" → "Run workflow"

## Notifiche Telegram: lista sempre aggiornata, non uno storico

Il bot **non accumula messaggi**: ad ogni esecuzione cancella il/i
messaggio/i precedenti e ne invia uno nuovo con lo stato attuale completo
delle carte mancanti. In questo modo la chat resta sempre con un'unica
lista aggiornata, raggruppata per carta (non per mazzo), con l'elenco dei
mazzi che la richiedono e il link a ciascuno.

Il ricalcolo è **completo ad ogni run**: confronta la collezione con
*tutti* i mazzi mai visti (non solo quelli nuovi di quel giorno). Questo
significa che se compri una carta, sparisce dalla lista al run successivo
anche se quel giorno non è stato pubblicato nessun mazzo nuovo.

Nota tecnica: Telegram permette ai bot di cancellare i propri messaggi solo
entro 48 ore dall'invio. Nell'uso quotidiano previsto (un run al giorno)
non è un problema; se il bot resta fermo per più di 2 giorni, il messaggio
più vecchio potrebbe non essere cancellabile e ne comparirà uno nuovo
accanto (il bot logga un avviso in quel caso, senza bloccarsi).

## Rispetto del sito

Il bot fa **una sola scansione al giorno**, con un piccolo ritardo tra le
richieste (`time.sleep`) per non sovraccaricare il server. Se il sito
richiede login/abbonamento per vedere certi mazzi, il bot userà solo la tua
sessione autenticata (cookie che fornisci tu) — non aggira in alcun modo
paywall o restrizioni di accesso.
