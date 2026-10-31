# 📝 Directory Log Formazing

Questa directory contiene i file di log dell'applicazione Formazing.

## 📄 File generati

- `formazing.log` - File di log principale (rotante)
- `formazing.log.1`, `formazing.log.2`, ecc. - File di backup (max 10)

## 🔄 Rotazione automatica

I file di log utilizzano `RotatingFileHandler`:
- **Dimensione massima**: 10 MB per file
- **File di backup**: 10 file mantenuti (≈ 2-4 mesi di storico)
- **Encoding**: UTF-8

Quando `formazing.log` raggiunge 10 MB:
1. Viene rinominato in `formazing.log.1`
2. I backup precedenti vengono spostati (`log.1` → `log.2`, ecc.)
3. Il backup più vecchio (`log.10`) viene eliminato
4. Un nuovo `formazing.log` viene creato

## ⚙️ Configurazione

Le impostazioni del logging possono essere modificate tramite variabili ambiente nel file `.env`:

```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/formazing.log       # Path del file di log
LOG_MAX_BYTES=10485760           # 10 MB in bytes
LOG_BACKUP_COUNT=10              # Numero di backup da mantenere (default: 10 = ~110MB max)
```

## 🔇 Verbosità Controllata

Per evitare che il file cresca inutilmente, alcune categorie di log vengono filtrate:

- **`werkzeug`** → `WARNING`: le richieste HTTP con esito positivo (200/304) non vengono
  scritte nel file. Solo errori (4xx, 5xx) sono registrati.
- **Log di routine Notion** → `DEBUG`: le query intermedie ("Recupero formazioni...",
  "Parsing completato...") sono state abbassate a DEBUG e non appaiono in produzione
  (dove `LOG_LEVEL=INFO`). Rimangono visibili attivando `LOG_LEVEL=DEBUG` per il debug.
- **`telegram`** → `CRITICAL`: la libreria python-telegram-bot è estremamente verbosa;
  vengono registrati solo i crash critici.

## 📊 Formato log

Ogni riga di log contiene:
```
2025-11-09 15:29:47 | INFO     | app.routes                     | 📊 Dashboard caricata | Totale: 15
```

- **Timestamp**: Data e ora (YYYY-MM-DD HH:MM:SS)
- **Livello**: INFO, WARNING, ERROR, ecc.
- **Modulo**: Nome del modulo Python che ha generato il log
- **Messaggio**: Messaggio di log con emoji e contesto

## 🔍 Visualizzazione log

### Comandi PowerShell Base

```powershell
# Ultime 50 righe
Get-Content logs/formazing.log -Tail 50

# Segui il log in tempo reale
Get-Content logs/formazing.log -Wait -Tail 10

# Filtra per errori
Select-String -Path logs/formazing.log -Pattern "ERROR|CRITICAL"

# Filtra per emoji specifica (es. Notion)
Select-String -Path logs/formazing.log -Pattern "🗄️"
```

### Comandi Linux/Mac
```bash
# Ultime 50 righe
tail -n 50 logs/formazing.log

# Segui il log in tempo reale
tail -f logs/formazing.log

# Filtra per errori
grep -E "ERROR|CRITICAL" logs/formazing.log

# Filtra per emoji Notion
grep "🗄️" logs/formazing.log
```

## 🚫 File ignorati da Git

I file `.log` sono automaticamente ignorati da Git (vedi `.gitignore`).
Solo il file `.gitkeep` viene tracciato per mantenere la directory nel repository.

## 🧹 Pulizia manuale

Per eliminare tutti i log:
```powershell
# Windows
Remove-Item logs/*.log

# Linux/Mac
rm logs/*.log
```

La directory verrà ricreata automaticamente al prossimo avvio dell'applicazione.
