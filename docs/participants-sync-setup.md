# Guida per il Test e Setup della Sincronizzazione Partecipanti

Questa documentazione spiega come configurare e testare la funzionalità di sincronizzazione manuale dei partecipanti da Microsoft Teams a Notion, inclusi i permessi necessari lato Notion e Microsoft Graph API.

---

## 1. Configurazione lato Notion

Per salvare i partecipanti all'interno della pagina Notion della formazione, è necessario aggiungere una nuova colonna nel database Notion e configurare i permessi del token d'integrazione.

### A. Aggiungere le colonne su Notion
1. Apri il database delle formazioni su Notion.
2. Crea le seguenti colonne cliccando su `+`:
   - **Colonna 1**:
     - **Nome**: `Partecipanti`
     - **Tipo**: `Persone` (People)
   - **Colonna 2**:
     - **Nome**: `Numero Partecipanti`
     - **Tipo**: `Numero` (Number) -> Formato: Numero intero (facoltativo)
   - **Colonna 3**:
     - **Nome**: `Durata`
     - **Tipo**: `Numero` (Number) -> Formato: Numero decimale

### B. Configurare i permessi del Token d'Integrazione
L'applicazione Formazing deve poter leggere l'elenco degli utenti di Notion per poter associare le email/nomi estratti da Teams agli account Notion reali del workspace.
1. Accedi a [Notion My Integrations](https://www.notion.so/my-integrations).
2. Seleziona l'integrazione configurata nel file `.env` tramite il campo `NOTION_TOKEN`.
3. Sotto la scheda **Capabilities** (Funzionalità), assicurati che la seguente opzione sia abilitata:
   - **Read user information (including email addresses)** (Leggi le informazioni dell'utente, inclusi gli indirizzi email).
4. Salva le modifiche.

---

## 2. Configurazione lato Microsoft Azure (Graph API)

La sincronizzazione effettua chiamate a Microsoft Graph API per conto dell'applicazione stessa (tramite Client Credentials Flow, usando Client ID e Client Secret). Per questo motivo, sono richiesti **permessi di tipo Applicazione** (Application Permissions) nel portale Azure AD.

### A. Aggiungere i permessi in Azure AD
1. Accedi al portale di [Azure Portal](https://portal.azure.com/).
2. Vai su **Azure Active Directory** (o Entra ID) -> **App registrations** (Registrazioni app).
3. Seleziona l'applicazione registrata per Formazing (corrispondente al tuo `MICROSOFT_CLIENT_ID`).
4. Nel menu laterale, seleziona **API permissions** -> **Add a permission** -> **Microsoft Graph**.
5. Seleziona **Application permissions** (Permessi applicazione) e aggiungi i seguenti permessi:
   - **`OnlineMeetings.Read.All`** (o `OnlineMeetings.ReadWrite.All`) — Per cercare la riunione online tramite il link Teams (`joinWebUrl`).
   - **`OnlineMeetingArtifact.Read.All`** — Fondamentale per scaricare i report di presenza della riunione.
   - **`User.Read.All`** — Consente all'app di leggere le informazioni degli utenti associati ai partecipanti.
6. Clicca sul pulsante **"Grant admin consent for [Nome Organizzazione]"** (pulsante con la spunta verde) per approvare i permessi a livello di tenant.

### B. Configurazione della Application Access Policy in Teams (PowerShell)
Di default, in Microsoft 365, un'applicazione con permessi applicativi non è autorizzata ad accedere ai meeting degli utenti a meno che non venga definita una policy. Se l'API Graph risponde con errori del tipo `403 Forbidden` o `404 Not Found`, l'amministratore IT dell'organizzazione dovrà eseguire i seguenti passaggi in **PowerShell**:

1. Apri PowerShell come amministratore ed installa il modulo di Teams (se non già presente):
   ```powershell
   Install-Module -Name MicrosoftTeams -Force -AllowClobber
   ```
2. Connettiti a Microsoft Teams:
   ```powershell
   Connect-MicrosoftTeams
   ```
3. Crea la policy che associa l'applicazione registrata:
   ```powershell
   # Sostituisci YOUR_CLIENT_ID con il valore di MICROSOFT_CLIENT_ID presente nel tuo .env
   New-CsApplicationAccessPolicy -Identity "FormazingSyncPolicy" -AppIds "YOUR_CLIENT_ID" -Description "Consenti all'app Formazing di scaricare i report delle presenze dei meeting"
   ```
4. Assegna la policy all'account dell'organizzatore (la mail configurata in `MICROSOFT_USER_EMAIL` nel tuo `.env`):
   ```powershell
   # Sostituisci con la mail configurata in .env
   Grant-CsApplicationAccessPolicy -PolicyName "FormazingSyncPolicy" -Identity "lucadileo@jemore.it"
   ```

---

## 3. Flusso di Test Passo-Passo

Una volta completata la configurazione dei permessi Notion e Microsoft, puoi procedere al test operativo.

### Passo 1: Verificare la Diagnostica su Formazing
1. Avvia l'applicazione Formazing (`python run.py`).
2. Accedi alla dashboard ed esegui i test di diagnostica per assicurarti che la connessione a Notion sia corretta.
   - Se le colonne `Partecipanti`, `Numero Partecipanti` o `Durata` non sono ancora state create in Notion, la diagnostica mostrerà dei **Warning** spiegando quali campi sono mancanti e come crearli, senza bloccare l'avvio dell'applicazione.
   - Una volta create correttamente su Notion con i tipi indicati, i warning scompariranno.

### Passo 2: Trovare una formazione conclusa
1. Vai alla scheda delle formazioni **"Concluse"** (la terza scheda della dashboard).
2. Se non ci sono elementi, seleziona una formazione nella scheda **"Calendarizzate"**, effettua la preview di feedback e clicca su "Conferma e invia". Questo cambierà lo stato in "Conclusa".
3. Assicurati che la formazione selezionata abbia il campo `Link Teams` popolato con un URL valido di una riunione Teams effettivamente tenutasi.

### Passo 3: Avviae il Sync delle Presenze
1. Sulla riga della formazione conclusa, noterai un pulsante blu **"Importa Presenze"** con l'icona dei partecipanti (👥).
2. Clicca sul pulsante. L'applicazione mostrerà l'overlay grafico: *"Connessione a Microsoft Graph e recupero report presenze da Teams..."*.
3. L'applicazione cercherà il meeting, recupererà il report delle presenze Teams e proverà ad abbinare gli indirizzi email o i nomi dei partecipanti con gli utenti Notion del workspace.

### Passo 4: Controllo e Aggiornamento
- A sincronizzazione ultimata, la dashboard si ricaricherà mostrando un banner verde di conferma (es: *"Sincronizzazione completata: 4 partecipanti trovati (Durata: 1.5h)."*).
- Il pulsante diventerà verde e cambierà dicitura in **"Aggiorna Presenze"** (con icona di reload), permettendo di rieseguire la sincronizzazione in caso di partecipanti che si sono collegati in ritardo.
- Apri Notion e controlla la riga corrispondente:
  - La colonna `Partecipanti` mostrerà gli account degli utenti Notion reali abbinati.
  - La colonna `Numero Partecipanti` conterrà il numero totale di presenti (es: `4`).
  - La colonna `Durata` conterrà la durata effettiva calcolata della call (es: `1.5` per 1 ora e 30 minuti).

---

## 4. Logica di Business e Gestione dei Report

Durante la sincronizzazione, Formazing adotta le seguenti logiche per garantire l'integrità dei dati:

### A. Selezione del Report Principale (Riaperture Meeting)
Se un utente rientra nella riunione Teams dopo la sua conclusione ufficiale, Teams genera nuovi report di presenza distinti e quasi vuoti.
Per evitare di importare report errati, Formazing **scansiona tutti i report disponibili per il meeting e seleziona automaticamente quello con il maggior numero di partecipanti** (`totalParticipantCount`), ignorando riaperture accidentali del link.

### B. Arrotondamento della Durata
La durata calcolata viene memorizzata in Notion seguendo queste regole:
* Viene **arrotondata al multiplo di 0.5 ore più vicino** (es. 1.0h, 1.5h, 2.0h, ecc.).
* Se la riunione si è tenuta (durata maggiore di zero) ma l'arrotondamento la porterebbe a 0.0, viene forzato un **valore minimo di 0.5 ore** (30 minuti).

---

## 5. Risoluzione dei Problemi Comuni

### Errore 3003: User does not have access to lookup meeting
* **Causa:** L'organizzatore del meeting Teams non coincide con l'email impostata in `MICROSOFT_USER_EMAIL` nel file `.env`. L'applicazione non ha l'autorizzazione a leggere i meeting di altri utenti.
* **Soluzione:** 
  1. Assicurati che il link Teams appartenga a un meeting creato dall'utente configurato nel `.env`.
  2. In alternativa, se vuoi usare un organizzatore diverso, aggiorna `MICROSOFT_USER_EMAIL` nel `.env` e assegna ad esso la policy in PowerShell:
     `Grant-CsApplicationAccessPolicy -PolicyName "FormazingSyncPolicy" -Identity "nuovo_utente@domain.com"`

### Errore 3004: Specified meeting is not found
* **Causa:** Microsoft Graph non trova l'oggetto meeting associato al link. Questo succede se:
  1. Il meeting non è mai iniziato (nessuno è entrato nella chiamata).
  2. L'evento è stato eliminato dal calendario dell'organizzatore.
  3. Il meeting è troppo vecchio: Microsoft Graph cancella i metadati per il lookup dei meeting dopo circa **90 giorni**.
* **Soluzione:** Verifica che la riunione sia stata effettivamente avviata ed utilizzata dall'organizzatore corretto entro i limiti temporali previsti.

### Errore: Insufficient privileges to complete the operation
* **Causa:** L'applicazione Azure AD non ha il permesso applicativo **`User.Read.All`** o l'amministratore non ha cliccato su **"Grant admin consent"** nel Portale Azure.
* **Soluzione:** Segui i passaggi descritti al punto **2.A** e assicurati di vedere lo stato verde di approvazione accanto a tutti i permessi.
