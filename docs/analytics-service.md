# 📊 Analytics & Reporting - Documentazione Tecnica

**Sistema di Business Intelligence per l'analisi storica e strategica delle formazioni**

---

## 📋 Indice

1. [🚀 Panoramica](#-panoramica)
2. [🏗️ Architettura](#️-architettura)
3. [📈 Indicatori e Grafici](#-indicatori-e-grafici)
4. [⚙️ Logica di Calcolo](#️-logica-di-calcolo)
5. [⚡ Performance e Cache](#-performance-e-cache)

---

## 🚀 Panoramica

Il modulo **Analytics** trasforma i dati operativi raccolti su Notion in informazioni strategiche. Permette al Board e ai responsabili delle formazioni di monitorare il volume delle attività, il bilanciamento tra le aree e la crescita dell'associazione nel tempo.

La pagina è accessibile dalla barra di navigazione principale e offre una visione sia storica (dall'inizio dei dati) che annuale.

---

## 🏗️ Architettura

Il sistema segue la filosofia modulare del progetto, separando la logica di calcolo dalla visualizzazione:

- **`AnalyticsService` (`app/services/analytics_service.py`)**: Il "motore" che processa i dati grezzi.
- **`Analytics View` (`app/routes.py`)**: La rotta Flask che coordina il recupero dati e il rendering.
- **`Chart.js Engine` (`app/templates/pages/analytics.html`)**: Il frontend che trasforma i JSON in grafici interattivi.

---

## 📈 Indicatori e Grafici

### 1. KPI Cards (I "Numeroni")
- **Area Regina**: L'area con il maggior volume di formazioni erogate.
- **Media Accademica**: Media mensile calcolata dall'ultimo Settembre ad oggi.
- **Media Globale**: Media storica mensile allineata all'inizio dell'anno accademico di partenza.
- **Formazioni Totali**: Conteggio complessivo di tutti gli eventi in archivio.

### 2. Distribuzione per Area (Soci vs In Prova)
Un grafico a **barre raggruppate (Stacked Bar)** che mostra per ogni macro-area:
- Il volume dei **Soci Effettivi** (colore pieno).
- Il volume dei **Soci in Prova** (colore semitrasparente).
- Il **totale** dell'area visualizzato sopra ogni barra.

### 3. Crescita Storica (Timeline Totale)
Grafico a linee continuo che mostra l'andamento mese per mese dalla primissima formazione registrata. Utile per identificare trend di crescita pluriennali.

### 4. Dettaglio Annuale (con Selettore)
Grafico a barre focalizzato su un singolo anno solare. Un menu a tendina permette di cambiare l'anno visualizzato istantaneamente senza ricaricare la pagina.

### 5. Volume per Periodo
Analisi della distribuzione degli eventi tra i vari periodi associativi (SPRING, AUTUMN, EXT, etc.) con indicazione della percentuale di incidenza sul totale.

---

## ⚙️ Logica di Calcolo

### Allineamento Accademico
Per evitare medie sfasate nei primi mesi di utilizzo, il sistema allinea i calcoli all'anno accademico (che per JEMORE inizia a **Settembre**):
- Se la prima formazione registrata è a Novembre 2024, la **Media Globale** conterà i mesi partendo da Settembre 2024.
- La **Media Accademica** si resetta ogni 1° Settembre.

### Raggruppamento Aree
Le aree vengono normalizzate per evitare frammentazione:
- "IT" e "IT in prova" vengono raggruppate sotto la macro-area "IT".
- Le aree generiche "In Prova" vengono aggregate alla categoria **"All"**.

---

## ⚡ Performance e Cache

Il modulo Analytics è progettato per essere estremamente leggero:
1. **Zero Traffico API Extra**: Utilizza i dati già scaricati per la Dashboard.
2. **Server-Side Processing**: Tutti i calcoli complessi avvengono in Python prima di inviare i dati al browser.
3. **Integrazione Cache**: Se i dati della Dashboard sono in cache, il caricamento degli Analytics è istantaneo.
4. **Aggiornamento Manuale**: Il pulsante "Aggiorna da Notion" permette di invalidare la cache e forzare una nuova lettura dal database.

---
*Documentazione aggiornata al 01/06/2026 - Versione 1.0*
