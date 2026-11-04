# Bot Telegram interpelli A041

Controlla ogni 10 minuti i siti degli uffici scolastici e manda un messaggio Telegram per ogni nuovo interpello A041,
con regione, scuola, ore, durata, scadenza e link all'avviso.

## 1. Crea il bot su Telegram (5 minuti)

1. Su Telegram apri **@BotFather**, invia `/newbot` e segui le istruzioni.
2. Copia il **token** che ti restituisce. È una password: non condividerlo con nessuno.
3. Apri il tuo nuovo bot e premi **Avvia**, altrimenti non potrà scriverti.
4. Installa la libreria che legge i PDF:
   ```
   python -m pip install -r requirements.txt
   ```
5. Copia `.env.example` in un nuovo file `.env` e incolla il token dopo `TELEGRAM_TOKEN=`.
6. Ricava il tuo chat id:
   ```
   python bot.py --chat-id
   ```
   Copia la riga `TELEGRAM_CHAT_ID=...` nel file `.env`.
7. Prova il collegamento: deve arrivarti un messaggio.
   ```
   python bot.py --test
   ```

## 2. Scegli dove farlo girare

### Opzione A: GitHub Actions (consigliata, gratis, PC spento)

1. Crea un account su github.com e un repository **pubblico**, ad esempio `interpelli-a041`.
   I minuti gratuiti di un repository privato non bastano per una scansione ogni 10 minuti.
2. Carica tutti i file di questa cartella, compresa `.github`. **Non caricare `.env`**: il file `.gitignore` lo esclude già.
3. Nel repository vai in **Settings → Secrets and variables → Actions → New repository secret** e crea
   `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID`.
4. Vai in **Actions → Interpelli A041 → Run workflow** per il primo avvio.

GitHub esegue le attività pianificate quando ha capacità disponibile: nelle ore di punta l'attesa reale può superare i 10 minuti.
Nel repository pubblico sarà visibile anche `state.json`, che contiene solo i link agli avvisi già inviati.

### Opzione B: il tuo PC

Fai doppio clic su `avvia_bot.bat`. Il bot funziona finché il PC è acceso e connesso. Se resta spento,
alla riaccensione recupera gli avvisi pubblicati nel frattempo, quelli ancora aperti.

## Cosa aspettarsi

- **Primo avvio:** ricevi gli avvisi degli ultimi 14 giorni non ancora scaduti. Non vengono inviati quelli delle pagine senza data.
- **Ogni giorno:** un messaggio conferma che il bot è attivo e segnala le fonti ferme da oltre 24 ore.
- **Filtrare le regioni:** su Telegram cerca ad esempio `#Lombardia` nella chat. Per ricevere solo alcune regioni imposta
  `REGIONI=Lazio,Campania` nel file `.env` (su GitHub: variabile `REGIONI` nella stessa pagina dei secret).
  Gli avvisi senza regione riconosciuta arrivano comunque.
- **Dati da verificare:** ore, scadenza e località sono ricavate in automatico. Prima di candidarti controlla sempre l'avviso originale.

## Limiti della copertura

Non esiste un elenco nazionale unico: il bot legge gli uffici territoriali. Non può quindi garantire di trovare ogni interpello,
in particolare quelli pubblicati soltanto sul sito della singola scuola.

Province senza lettura diretta, coperte solo quando un altro ufficio ripubblica l'avviso:

| Regione | Province | Motivo |
| --- | --- | --- |
| Campania | Salerno | certificato di sicurezza del sito non verificabile |
| Campania | Benevento | il sito rifiuta le richieste automatiche |
| Lazio | Viterbo | il sito rifiuta le richieste automatiche |
| Lazio | Latina | indirizzo non trovato |
| Puglia | Lecce, Taranto | indirizzo non trovato o nessun avviso leggibile |
| Marche | Ancona, Macerata, Fermo | indirizzo non trovato |
| Toscana | Grosseto, Livorno, Pisa | pagina non leggibile o spostata |
| Abruzzo | Teramo | indirizzo non trovato |
| Valle d'Aosta, Trentino-Alto Adige | tutte | non cercate: hanno un'organizzazione scolastica propria |

Per aggiungere un ufficio basta una riga in `tools/build_sources.py`, poi `python tools/build_sources.py`.

## Comandi utili

| Comando | A cosa serve |
| --- | --- |
| `python bot.py --dry-run --backfill 14` | mostra gli avvisi recenti senza inviare nulla |
| `python bot.py --report` | stato di ogni fonte, per regione |
| `python -m unittest test_bot` | esegue i test |
