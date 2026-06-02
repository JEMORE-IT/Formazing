# 🧪 Testing & Quality Assurance - Formazing

**Sistema di test completo per validazione e quality assurance del progetto Formazing**

---

## � Contenuto Cartella Testing

### 📚 Guide Complete
- **[🧪 E2E Integration Testing](e2e-integration-testing.md)** - Sistema test end-to-end con dati reali
- **[🔧 Fixture Testing Guide](fixture-testing-guide.md)** - Guida dettagliata alle 39 fixture modulari
- **[📋 Fixture Quick Reference](fixture-quick-reference.md)** - Reference rapido per sviluppo
- **[📱 Telegram Testing](telegram-testing.md)** - Test bot, comandi, invii reali
- **[🔗 Notion Testing](notion-testing.md)** - Test API, query, parsing, CRUD
- **[🔷 Microsoft Testing](microsoft-testing.md)** - Test Teams integration, calendario, email

---


## 📊 Sistema di Test Implementato

### **📈 Statistiche Complete**
- **106 test unitari** in **1.2 secondi** (unit/)
- **4 test E2E** con **dati reali** (e2e/)
- **39 fixture modulari** in 6 file specializzati
- **86 test NotionService** (5 moduli completi)
- **20 test TelegramFormatter** (unit test puri)

### **🏗️ Architettura Testing**
```
tests/
├── 🔧 conftest.py                   # Core fixture (ridotto da 900 a 70 righe)
├── 📁 fixtures/                     # Fixture modulari (39 totali)
│   ├── telegram_fixtures.py         # 5 fixture bot & training
│   ├── notion_fixtures.py           # 8 fixture base Notion
│   ├── query_builder_fixtures.py    # 6 fixture query construction
│   ├── crud_fixtures.py            # 8 fixture CRUD operations
│   ├── client_fixtures.py          # 7 fixture auth & environment
│   └── facade_fixtures.py          # 4 fixture integration
├── 📁 unit/                        # Unit test (106 test, 1.2s)
│   ├── notion/                     # Test 5 moduli NotionService
│   └── test_telegram_formatter.py  # Test formatter messaggi
├── 📁 e2e/                         # End-to-end test (dati reali)
│   ├── test_real_config.py        # Verifica connessioni
│   ├── test_real_formatting.py    # Formattazione con dati reali
│   ├── test_real_send.py          # Invio controllato reale
│   └── test_workflow.py           # Workflow completo
└── 📁 integration/                 # Integration test legacy
    └── test_real_telegram.py       # Test bot completi
```
---

## 📝 Struttura Directory Testing

### **🔧 tests/fixtures/** - Sistema Fixture Modulari
```
fixtures/
├── __init__.py              # Auto-import tutte le fixture
├── telegram_fixtures.py     # 5 fixture: bot, training, mock services
├── notion_fixtures.py       # 8 fixture: dati base, response simulate
├── query_builder_fixtures.py # 6 fixture: query construction, filtri  
├── crud_fixtures.py         # 8 fixture: operazioni CRUD, batch ops
├── client_fixtures.py       # 7 fixture: auth, env, configuration
└── facade_fixtures.py       # 4 fixture: integration, service completi
```

### **⚡ tests/unit/** - Unit Test (106 test, 1.2s)
```
unit/
├── test_telegram_formatter.py  # 20 test: template, markdown, escape
└── notion/                     # 86 test: tutti moduli NotionService
    ├── test_query_builder.py   # Test costruzione query
    ├── test_data_parser.py      # Test parsing response
    ├── test_crud_operations.py  # Test operazioni database
    ├── test_diagnostics.py     # Test monitoring e health
    └── test_notion_client.py    # Test auth e connessione
```

### **🌐 tests/e2e/** - End-to-End Test (Dati Reali)
```
e2e/
├── test_real_config.py      # Verifica connessioni Notion+Telegram
├── test_real_formatting.py  # Formattazione con 27+ formazioni reali
├── test_real_send.py        # Invio controllato con conferme triple
└── test_workflow.py         # Workflow completo con analytics
```

---

## 📚 Dettaglio Comandi Quick Test

### **🔍 Mappatura Comando → Python/Pytest**

Questa sezione spiega **esattamente** cosa fa ogni comando `quick_test` e a quale comando Python/pytest corrisponde.

#### **🔧 Comandi di Setup e Verifica**

**`check`** - Verifica Ambiente
```bash
# Comando quick_test
.\quick_test.bat check

# Equivalente Python
python -c "import pytest; print('✅ pytest disponibile')"
```
**Cosa fa**: Verifica che l'ambiente sia configurato correttamente:
- Controlla esistenza file `.env`, `test_telegram_groups.json`, `test_message_templates.yaml`
- Verifica che pytest sia installato
- **Non esegue nessun test**, solo controlli di ambiente

---

#### **⚡ Unit Test (Zero Dipendenze Esterne)**

**`unit`** - Tutti i Test Unitari (106 test)
```bash
# Comando quick_test
.\quick_test.bat unit

# Equivalente Python  
python -m pytest tests/unit/ -v
```
**Cosa fa**: Esegue **tutti** i test unitari del progetto (106 test in 1.2s):
- **86 test NotionService**: query_builder, data_parser, crud_operations, diagnostics, notion_client
- **20 test TelegramFormatter**: template rendering, markdown escaping, formattazione
- **Zero invii reali**, solo logica business pura
- **Mock completi** per tutte le dipendenze esterne

**`notion`** - Solo Moduli NotionService (86 test)  
```bash
# Comando quick_test
.\quick_test.bat notion

# Equivalente Python
python -m pytest tests/unit/notion/ -v
```
**Cosa fa**: Testa **solo** i 5 moduli del NotionService (86 test in 0.9s):
- **query_builder**: Costruzione query filtri per database Notion
- **data_parser**: Parsing response API Notion → formato interno
- **crud_operations**: Operazioni CRUD (update status, batch operations)
- **diagnostics**: Health check, validazione, monitoring
- **notion_client**: Autenticazione, configurazione, connessione base

---

#### **🌐 Test E2E (Dati Reali, Zero Invii)**

**`config`** - Verifica Connessioni Reali
```bash
# Comando quick_test  
.\quick_test.bat config

# Equivalente Python
python tests/e2e/test_real_config.py
```
**Cosa fa**: Testa connessioni **reali** senza inviare messaggi:
- **Notion**: Autentica e recupera formazioni dal database reale
- **Telegram**: Verifica token bot e connessione API (senza invii)
- **Validazione dati**: Controlla che le formazioni abbiano campi obbligatori
- **Report connessioni**: Token mascherati per sicurezza

**`preview`** - Formattazione con Dati Reali
```bash
# Comando quick_test
.\quick_test.bat preview

# Equivalente Python  
python tests/e2e/test_real_formatting.py
```
**Cosa fa**: Testa formattazione messaggi con **27+ formazioni reali**:
- **Recupera formazioni** dal database Notion reale (tutti gli stati)
- **Applica template** YAML per messaggi training/feedback
- **Valida formato** Markdown, lunghezza, caratteri speciali
- **Genera preview** complete senza inviare nulla

**`workflow`** - Workflow Completo (Safe Mode)
```bash
# Comando quick_test
.\quick_test.bat workflow

# Equivalente Python
python tests/e2e/test_workflow.py --limit 3
```
**Cosa fa**: Simula **intero workflow produzione** senza invii reali:
- **Processa 3 formazioni** reali in stato "Programmata"
- **Genera codici** univoci, **crea link Teams** fittizi
- **Formatta messaggi** email/Telegram con template
- **Aggiorna stato** → "Calendarizzata" (solo in memoria, non salva)
- **Report completo** con metriche performance e risultati

**`all`** - Suite Completa Pre-Commit (Sincronizzata!)
```bash
# Comando quick_test (Windows)
.\quick_test.bat all

# Comando quick_test (Linux/macOS)
./quick_test.sh all

# Equivalente: 4 comandi in sequenza interattiva
```
**Cosa fa**: Suite **interattiva step-by-step** per validazione pre-commit, ora disponibile su tutte le piattaforme:
- **Step 1**: Test unitari (106 test, 1.2s) con conferma (INVIO)
- **Step 2**: Verifica connessioni Notion + Telegram con conferma (INVIO)
- **Step 3**: Test formattazione template con dati reali con conferma (INVIO)
- **Step 4**: Workflow simulazione completa con conferma (INVIO)
- **Nessun timeout**: Il passaggio tra gli step è immediato dopo la tua conferma.
- **Report finale** con riepilogo test eseguiti

---

#### **🔴 Test con Invii Reali (Attenzione)**

**`send`** - Invio Controllato con Conferme Triple
```bash
# Comando quick_test
.\quick_test.bat send

# Equivalente Python
python tests/e2e/test_real_send.py
```
**Cosa fa**: Invia messaggi **reali** con controlli di sicurezza:
- **Selezione interattiva** di 1 formazione dal database reale
- **Preview completa** del messaggio da inviare
- **Conferma tripla** esplicita prima dell'invio
- **Invio reale** a gruppi Telegram configurati
- **Tracking risultati** con conferma delivery

**`workflow-real`** - Workflow Produzione Completo
```bash
# Comando quick_test  
.\quick_test.bat workflow-real

# Equivalente Python
python tests/e2e/test_workflow.py --real --limit 2
```
**Cosa fa**: Esegue **workflow completo** con invii reali:
- **Processa 2 formazioni** reali in stato "Programmata"  
- **Genera codici** reali, **crea meeting Teams** reali
- **Invia email** reali via Microsoft Graph API
- **Invia messaggi Telegram** reali ai gruppi configurati
- **Aggiorna database** Notion reale → stato "Calendarizzata"
- **Report finale** con analytics completi

---

#### **🔷 Test Microsoft Teams Integration**

**`microsoft`** - Test Microsoft Service Isolato
```bash
# Comando quick_test
.\quick_test.bat microsoft

# Equivalente Python
python test_real_microsoft.py
```
**Cosa fa**: Testa il Microsoft Service in **isolamento** (no Notion):
- **Crea evento Teams** reale con data/ora futura (+5 minuti)
- **Genera meeting link** Microsoft Teams automatico
- **Invia email** reale alla mailing list configurata (es. it@jemore.it)
- **Validazione completa**: verifica token, permessi, configurazione
- **Sicurezza**: Richiede conferma esplicita "SI" prima dell'esecuzione
- **Risultato**: Mostra event ID, Teams link, destinatari email

**`integration`** - Test Integrazione Notion → Microsoft
```bash
# Comando quick_test
.\quick_test.bat integration

# Equivalente Python
python test_notion_microsoft_integration.py
```
**Cosa fa**: Testa **workflow completo** Notion → Microsoft → Notion:
- **Recupera formazioni** reali da Notion (stato "Programmata")
- **Selezione interattiva** della formazione da calendarizzare
- **Crea evento Teams** reale con meeting link
- **Invia email** alle mailing list delle aree configurate
- **Aggiorna Notion** con link Teams e stato "Calendarizzata"
- **Verifica aggiornamento** ricaricando formazione da Notion
- **Sicurezza**: Richiede conferma "SI" + mostra preview dati

**`teams`** - Suite Completa Test Microsoft
```bash
# Comando quick_test
.\quick_test.bat teams

# Esecuzione interattiva in 2 step
```
**Cosa fa**: Suite **interattiva** per validazione completa Microsoft:
- **Step 1**: Test Microsoft Service isolato (conferma richiesta)
  - Crea evento test con dati mock
  - Valida autenticazione e permessi Graph API
  - Testa invio email a mailing list
- **Step 2**: Test integrazione con Notion (conferma richiesta)
  - Workflow completo con formazione reale
  - Aggiornamento database Notion
  - Verifica sincronizzazione link Teams
- **Report finale**: Riepilogo risultati entrambi i test

**Configurazione richiesta** per test Microsoft:
```env
# .env - Variabili Microsoft Graph API
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_CLIENT_ID=your-app-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_USER_EMAIL=organizer@domain.com
```

```json
// config/microsoft_emails.json - Mapping aree → email
{
  "IT": "it@jemore.it",
  "R&D": "rd@jemore.it",
  "HR": "hr@jemore.it",
  "default": "formazioni@jemore.it"
}
```

---

#### **🤖 Test Bot Legacy (Integration)**

**`format`** - Preview Formattazione (Legacy)
```bash
# Comando quick_test
.\quick_test.bat format

# Equivalente Python
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration::test_formatter_preview_messages -s -v --tb=short
```
**Cosa fa**: Test legacy per preview messaggi (usa vecchia architettura)

**`safe`** - Test Sicuri (Legacy)
```bash  
# Comando quick_test
.\quick_test.bat safe

# Equivalente Python
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration::test_formatter_preview_messages -s -v --tb=short
```
**Cosa fa**: Stesso di `format` (comando duplicato per backward compatibility)

**`interactive`** - Test Interattivi Bot
```bash
# Comando quick_test
.\quick_test.bat interactive

# Equivalente Python  
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration -s -v --tb=short
```
**Cosa fa**: Test completi bot Telegram con interazione manuale:
- **Tutti i test** bot con conferme manuali per ogni invio
- **Test comandi** bot (`/oggi`, `/domani`, `/settimana`)
- **Test notifiche** training e feedback con conferma
- **Sessione interattiva** completa ~30-60 secondi

**`training`** - Solo Notifiche Formazione (Legacy)
```bash
# Comando quick_test
.\quick_test.bat training

# Equivalente Python
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration::test_send_training_notification_real -s -v --tb=short
```
**Cosa fa**: Test invio **diretto** notifica formazione (senza conferme)

**`feedback`** - Solo Richieste Feedback (Legacy)  
```bash
# Comando quick_test
.\quick_test.bat feedback

# Equivalente Python
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration::test_send_feedback_notification_real -s -v --tb=short
```
**Cosa fa**: Test invio **diretto** richiesta feedback (senza conferme)

**`bot`** - Test Comandi Bot Live
```bash
# Comando quick_test
.\quick_test.bat bot

# Equivalente Python
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration::test_bot_commands_interactive -s -v --tb=short
```
**Cosa fa**: Attiva bot per 60 secondi e testa comandi dal vivo:
- **Avvia bot** in modalità ascolto per 60 secondi
- **Comandi testabili**: `/oggi`, `/domani`, `/settimana`, `/help`
- **Test manuale**: Invia comandi da Telegram e verifica risposte
- **Timeout automatico** dopo 60 secondi

**`real`** - Tutti i Test Reali
```bash
# Comando quick_test
.\quick_test.bat real

# Equivalente Python  
python -m pytest tests/integration/test_real_telegram.py::TestRealTelegramIntegration -m real_telegram -s -v --tb=short
```
**Cosa fa**: Esegue **tutti** i test con invii reali:
- **Richiede conferma** esplicita prima dell'avvio
- **Tutti i test** training, feedback, bot, interactive
- **Può durare** 60+ secondi con molti invii reali
- **Solo per validazione finale** prima del deploy

---

## 🎯 Comandi Più Utili

### **🔧 Durante Sviluppo (Uso Quotidiano)**
```bash
# ⭐ PIÙ IMPORTANTE - Feedback immediato ogni 2-3 minuti
.\quick_test.bat unit         # 106 test in 1.2s, zero invii

# 🔧 Debug specifico - Quando lavori su Notion
.\quick_test.bat notion       # 86 test in 0.9s, solo Notion

# ✅ Setup iniziale - Prima sessione di lavoro  
.\quick_test.bat check        # Verifica ambiente in 2s
```

### **🚀 Suite Completa Pre-Commit (Nuovo!)**
```bash
# ⭐ RACCOMANDATO - Suite interattiva step-by-step
.\quick_test.bat all          # 4 step con conferme, 10-15s totali
# → 1. Unit test (106 test)
# → 2. Connessioni (Notion + Telegram)  
# → 3. Formattazione (template reali)
# → 4. Workflow simulazione (safe)
```

### **📋 Prima di Commit (Validazione Pre-Push)**
```bash
# ✅ Validazione completa sicura (raccomandato)
.\quick_test.bat unit && .\quick_test.bat preview

# 🔍 Verifica connessioni se hai cambiato configurazioni
.\quick_test.bat config       # Solo se modifiche a .env o config/
```

### **🚀 Prima di Deploy (Validazione Produzione)**
```bash
# 🎯 Workflow completo sicuro - SEMPRE fare
.\quick_test.bat workflow     # Simula produzione senza invii

# 🔷 Test Microsoft Teams (se abilitate notifiche email)
.\quick_test.bat microsoft     # Test service isolato con dati mock

# ⚠️ Test reale controllato - Solo se necessario  
.\quick_test.bat send         # 1 messaggio reale con conferme

# 🚨 Workflow produzione - Solo deploy critico
.\quick_test.bat workflow-real # 2 formazioni reali complete
```

### **🔷 Test Microsoft Teams Integration**
```bash
# 🧪 Test isolato Microsoft service
.\quick_test.bat microsoft     # Crea evento test + email (5s)

# 🔗 Test integrazione completa Notion → Microsoft
.\quick_test.bat integration   # Workflow reale con formazione da Notion

# 📅 Suite completa Microsoft (interattiva)
.\quick_test.bat teams         # 2 step con conferme separate
```

### **🔍 Debug e Troubleshooting**
```bash
# 🔗 Problemi connessione database/bot
.\quick_test.bat config       # Diagnosi connessioni

# 📝 Problemi formattazione messaggi  
.\quick_test.bat preview      # Test template con dati reali

# 🔷 Problemi Microsoft Teams/Graph API
.\quick_test.bat microsoft    # Test autenticazione + creazione eventi

# 🤖 Problemi comandi bot
.\quick_test.bat bot          # Test interattivo 60s
```

### **💎 Raccomandazione Pre-Commit**
```bash
# ⭐ NUOVO STANDARD - Suite interattiva completa
.\quick_test.bat all          # 4 step con conferme, controllo totale

# ⚡ Alternativa veloce per commit frequenti  
.\quick_test.bat unit && .\quick_test.bat preview  # 3-4s totali

# 🔷 Se modifiche a Microsoft integration
.\quick_test.bat unit && .\quick_test.bat microsoft  # Valida service
```

---