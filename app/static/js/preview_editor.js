/**
 * Preview Editor Engine - 
 * 
 * Questo script gestisce l'interattività della pagina di preview:
 * 1. Sincronizza in tempo reale le textarea (editor) con i mockup grafici (Telegram/Email).
 * 2. Converte il Markdown di base in HTML per la visualizzazione.
 * 3. Protegge l'integrità dei dati critici (Link, Date, Codici) provenienti da Notion.
 */

const PreviewEditor = {
    // Registro che memorizza i valori originali e quante volte appaiono inizialmente in ogni editor.
    // Questo serve per la validazione basata sul conteggio.
    // Struttura esempio: { 'telegram-0': { 'link-teams': { value: 'https://...', initialCount: 1 } } }
    editorRegistry: {},
    
    // Master list dei valori vitali estratti dall'HTML (Nome, Data, Link, ecc.)
    vitalValues: {},

    /**
     * Punto di ingresso: scansiona la pagina e imposta i listener.
     */
    init() {
        
        // --- 1. ESTRAZIONE DATI VITALI ---
        // Cerchiamo tutti gli elementi che hanno l'attributo 'data-vital-field' (es: Nome, Data, Link) (che noi abbiamo messo nel template HTML)
        const fieldElements = document.querySelectorAll('[data-vital-field]');
        fieldElements.forEach(el => {
            const fieldName = el.dataset.vitalField; // es: "nome", "codice", "link-teams"
            // Se l'elemento è un link (<a>), prendiamo l'URL grezzo (href), altrimenti il testo interno.
            // Usiamo getAttribute('href') per evitare che il browser aggiunga slash finali automatici.
            const value = el.tagName === 'A' ? el.getAttribute('href') : el.textContent.trim();
            
            // Salviamo solo se il valore è utile (non vuoto o N/A)
            if (value && value !== 'N/A') {
                this.vitalValues[fieldName] = value;
            }
        });


        // --- 2. SETUP EDITORS TELEGRAM ---
        // Troviamo tutte le textarea dedicate ai messaggi Telegram  (riconosciute dalla classe 'telegram-editor-js')
        const telegramEditors = document.querySelectorAll('.telegram-editor-js');
        
        // Qui dobbiamo iterare siccome possiamo avere più messaggi Telegram (uno per ogni area)
        telegramEditors.forEach(editor => {
            // Ogni editor ha un index univoco (data-index, messo da noi nell'HTML) che ci serve per collegarlo al suo mockup e al suo registro.
            const index = editor.dataset.index; 
            const editorId = `telegram-${index}`; 
                        
            // Analizziamo il testo iniziale per capire quali e quanti dati Notion sono presenti
            this.registerEditorState(editorId, editor.value);
            
            // Mettiamo un listener su ogni editor Telegram per intercettare ogni input dell'utente
            editor.addEventListener('input', (e) => {
                this.updateTelegram(e.target.value, index); // e chiamare la funzione di aggiornamento
            });
            
            // Questo serve per avere all'inzio la preview già popolata correttamente
            this.updateTelegram(editor.value, index);
        });

        // --- 3. SETUP EDITOR EMAIL ---
        // Troviamo la textarea dedicata al corpo dell'email
        const emailEditor = document.querySelector('.email-editor-js');
        // N.B.: qui non c'è nessun ciclo perché abbiamo un solo editor per l'email
        if (emailEditor) {
            const editorId = 'email-body';
            
            // Analizziamo il testo iniziale dell'email (esattamente come prima)
            this.registerEditorState(editorId, emailEditor.value);
            
            // Listener per l'email (esattamente come prima)
            emailEditor.addEventListener('input', (e) => {
                this.updateEmail(e.target.value);
            });
            
            // Popoliamo il mockup email iniziale (esattamente come prima)
            this.updateEmail(emailEditor.value);
        }
    },

    /**
     * Analizza il testo di un editor e conta quante volte appare ogni dato vitale.
     * Serve per sapere "cosa deve esserci" per non dare errore.
     */
    registerEditorState(editorId, content) {
        this.editorRegistry[editorId] = {}; // Inizializziamo il registro per questo editor
        
        // Cicliamo su tutti i valori vitali (Nome, Link, ecc.)
        Object.entries(this.vitalValues).forEach(([fieldName, value]) => {
            // Contiamo quante volte appare nel testo iniziale
            const count = this.countOccurrences(content, value);
            
            // Se il dato è presente nel template originale, lo mettiamo sotto sorveglianza
            if (count > 0) {
                this.editorRegistry[editorId][fieldName] = {
                    value: value,
                    initialCount: count
                };
            }
        });
    },

    /**
     * Conta quante volte una stringa appare in un testo.
     * Usa le Regex per una ricerca globale accurata.
     */
    countOccurrences(text, search) {
        if (!search) return 0;
        
        // Puliamo la stringa di ricerca: i link hanno punti e slash che rompono le regex,
        // quindi mettiamo un backslash \ davanti a ogni carattere speciale.
        const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // Creiamo una Regex con flag 'g' (global) per trovare tutte le occorrenze
        const regex = new RegExp(escapedSearch, 'g');
        const matches = text.match(regex);
        
        // Se non ci sono match, ritorniamo 0, altrimenti il numero di match trovati
        return matches ? matches.length : 0;
    },

    /**
     * Aggiorna graficamente il fumetto di Telegram.
     */
    updateTelegram(content, index) {
        const editorId = `telegram-${index}`;
        const previewEl = document.getElementById(`telegram-preview-${index}`);
        
        // 1. Aggiorna il testo nel mockup
        if (previewEl) {
            previewEl.innerHTML = this.parseTelegramFormat(content);
        }
        
        // 2. Esegui la validazione
        const validation = this.validateIntegrity(editorId, content);
        
        // 3. Mostra i feedback visivi (bordi rossi ecc.)
        this.showValidationUI(validation, index, 'telegram');
    },

    /**
     * Aggiorna graficamente l'anteprima dell'Email.
     */
    updateEmail(content) {
        const editorId = 'email-body';
        const previewEl = document.getElementById('email-preview-body');
        
        // 1. Aggiorna il corpo email nel mockup (inniettiamo HTML direttamente)
        if (previewEl) {
            previewEl.innerHTML = content;
        }
        
        // 2. Esegui la validazione specifica per l'email
        const validation = this.validateIntegrity(editorId, content);
        
        // 3. Mostra feedback visivi
        this.showValidationUI(validation, 0, 'email');
    },

    /**
     * Converte il testo dell'editor in HTML così che il mockup possa mostrarlo formattato (grassetto, corsivo, link, ecc.).
     */
    parseTelegramFormat(text) {
        if (!text) return '';
        
        // Trasformiamo i tag che Telegram supporta in vero HTML leggibile dal browser
        let html = text
            // Grassetto Markdown: **testo** -> <strong>testo</strong>
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Grassetto HTML: <b>testo</b> -> <strong>testo</strong>
            .replace(/<b>(.*?)<\/b>/g, '<strong>$1</strong>')
            // Corsivo Markdown: _testo_ -> <em>testo</em>
            .replace(/_(.*?)_/g, '<em>$1</em>')
            // Corsivo HTML: <i>testo</i> -> <em>testo</em>
            .replace(/<i>(.*?)<\/i>/g, '<em>$1</em>')
            // Link Markdown: [testo](url) -> <a href="url">testo</a>
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
            // A capo: \n -> <br> (fondamentale per mantenere la formattazione)
            .replace(/\n/g, '<br>');
            
        return html;
    },

    /**
     * Verifica se il contenuto attuale dell'editor rispetta i conteggi iniziali.
     */
    validateIntegrity(editorId, currentContent) {
        let missingItems = [];
        const monitoredFields = this.editorRegistry[editorId] || {};

        // Controlliamo ogni campo che avevamo registrato all'inizio
        Object.entries(monitoredFields).forEach(([fieldName, info]) => {
            const currentCount = this.countOccurrences(currentContent, info.value);
            
            // Se il conteggio è diminuito, significa che l'utente ha cancellato qualcosa
            if (currentCount < info.initialCount) {
                
                // Creiamo un nome leggibile per l'alert
                const label = fieldName.includes('area') ? `Area` : 
                              fieldName === 'nome' ? 'Nome Formazione' : 
                              fieldName === 'data' ? 'Data/Ora' : 
                              fieldName === 'codice' ? 'Codice' : 'Link Teams';
                
                missingItems.push(label);
            }
        });

        // Ritorniamo lo stato: isBroken è true se manca almeno un pezzo
        return { 
            isBroken: missingItems.length > 0, 
            missingItems: [...new Set(missingItems)] // Togliamo i duplicati dalle etichette
        };
    },


    /**
     * Gestisce gli stili di errore (bordi, alert rossi).
     */
    showValidationUI(validation, index, type) {
        // Cerchiamo la textarea corrispondente
        const editor = document.querySelector(`.${type}-editor-js[data-index="${index}"]`) || document.querySelector(`.${type}-editor-js`);
        if (!editor) return;

        const alertId = `val-alert-${type}-${index}`;
        let alertEl = document.getElementById(alertId);

        if (validation.isBroken) {
            // --- STATO ERRORE ---
            editor.style.borderLeft = "5px solid #dc3545"; // Bordo rosso marcato
            editor.style.backgroundColor = "#fff8f8"; // Sfondo rosato
            
            // Creiamo dinamicamente il div dell'alert se non c'è
            if (!alertEl) {
                alertEl = document.createElement('div');
                alertEl.id = alertId;
                alertEl.className = "alert alert-danger py-2 px-3 mt-2 mb-0 extra-small d-flex align-items-center";
                editor.parentNode.appendChild(alertEl);
            }
            // Aggiorniamo il testo dell'errore
            alertEl.innerHTML = `<i class="bi bi-exclamation-octagon-fill me-2"></i> 
                                 <div><strong>Dati Manomessi!</strong> Reinserisci: ${validation.missingItems.join(', ')}</div>`;
            
            this.toggleSubmit(false); // Avvisa il bottone che c'è un problema
        } else {
            // --- STATO OK ---
            editor.style.borderLeft = "";
            editor.style.backgroundColor = "";
            if (alertEl) alertEl.remove(); // Cancella l'alert se la situazione è risolta
            
            // Riabilita il bottone solo se non ci sono altri alert di errore in tutta la pagina
            if (document.querySelectorAll('[id^="val-alert-"]').length === 0) {
                this.toggleSubmit(true);
            }
        }
    },

    /**
     * Gestisce il cambio di colore e testo del tasto "Conferma e Invia".
     */
    toggleSubmit(enabled) {
        const submitBtn = document.querySelector('button[type="submit"]');
        if (!submitBtn) return;

        // Memorizziamo il testo originale solo la prima volta
        const originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
        if (!submitBtn.dataset.originalText) submitBtn.dataset.originalText = originalText;
        
        if (!enabled) {
            // --- MODALITÀ PERICOLO (Soft Validation) ---
            submitBtn.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i> Invia Comunque (Dati Manomessi)';
            submitBtn.classList.replace('btn-jemore-giallo', 'btn-danger');
            submitBtn.dataset.isBroken = "true"; // Questo flag attiva il window.confirm in handleConfirm()
        } else {
            // --- MODALITÀ SICURA ---
            submitBtn.innerHTML = originalText;
            submitBtn.classList.replace('btn-danger', 'btn-jemore-giallo');
            submitBtn.dataset.isBroken = "false";
        }
    }
};

// Avviamo tutto non appena il browser ha finito di caricare l'HTML
document.addEventListener('DOMContentLoaded', () => PreviewEditor.init());
