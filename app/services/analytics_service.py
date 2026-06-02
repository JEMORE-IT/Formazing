"""
AnalyticsService - Motore per l'elaborazione dei dati statistici.

Questo modulo si occupa di trasformare i dati grezzi di Notion in strutture
dati ottimizzate per la visualizzazione grafica (Chart.js) e il calcolo dei KPI.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service specializzato nell'aggregazione e analisi dei dati delle formazioni.
    
    Responsabilità:
    - Pulizia e preparazione dati temporali
    - Distribuzione per aree (Soci vs In Prova)
    - Serie storiche (Timeline totale e annuale)
    - Calcolo medie (Accademica e Globale)
    """

    def __init__(self):
        self.ita_months_short = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        self.macro_areas = ['IT', 'HR', 'R&D', 'Marketing', 'Commerciale', 'Legale', 'All']

    def get_analytics_data(self, dashboard_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Punto di ingresso principale per l'elaborazione degli analytics.
        """
        try:
            # 0. Preparazione dati
            all_formazioni = self._prepare_data(dashboard_data)
            
            if not all_formazioni:
                return {'total': 0, 'empty': True}

            # Filtriamo solo quelle con data valida per i calcoli temporali
            dated_formazioni = sorted([f for f in all_formazioni if f.get('_dt')], key=lambda x: x['_dt'])

            # 1. In area_stats ci sarà il numero di formazioni per ogni macro-area, divise tra "regular" e "in prova"
            area_stats = self._get_area_stats(all_formazioni)

            # 2. In time_stats ci saranno:
            # - timeline_labels e timeline_values che rappresentano la label del mese-anno e il numero di formazioni in quel mese (per la timeline storica)
            # - available_years: lista degli anni disponibili per il selettore
            # - yearly_data: un dizionario dove la chiave è l'anno e il valore è una lista di 12 elementi che rappresentano il numero di formazioni per ogni mese di quell'anno (per la timeline annuale) 
            time_stats = self._get_time_stats(dated_formazioni)

            # 3. In periodo_stats ci sarà la distribuzione delle formazioni per "Periodo" con conteggio e percentuale per ogni periodo
            periodo_stats = self._get_periodo_stats(all_formazioni)

            # 4. Calcolo KPI e Medie
            kpis = self._calculate_kpis(all_formazioni, dated_formazioni, area_stats['stacked_raw'])

            # Unione di tutti i risultati
            return {
                **area_stats['formatted'],
                **time_stats,
                **kpis,
                'periodo_stats': periodo_stats,
                'total': len(all_formazioni),
                'concluse': len(dashboard_data.get('Conclusa', [])),
                'current_year': datetime.now().year,
                'month_names': self.ita_months_short
            }

        except Exception as e:
            logger.error(f"Errore critico nell'elaborazione analytics: {e}", exc_info=True)
            raise

    def _prepare_data(self, dashboard_data: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Unisce tutte le formazioni da tutti gli stati e arricchisce con oggetti datetime reali.
        Siccome dashboard_data è già diviso per stato, e le date sono in formato stringa
        """
        # Divisione in base allo stato
        all_formazioni = (dashboard_data.get('Programmata', []) + 
                          dashboard_data.get('Calendarizzata', []) + 
                          dashboard_data.get('Conclusa', []))

        # Helper per il parsing delle date Notion "dd/mm/YYYY HH:MM"
        def parse_dt(s):
            try: return datetime.strptime(s, '%d/%m/%Y %H:%M')
            except: return None

        # Arricchiamo le formazioni con oggetti datetime reali
        for f in all_formazioni:
            f['_dt'] = parse_dt(f.get('Data/Ora', ''))
            
        return all_formazioni

    def _get_area_stats(self, all_formazioni: List[Dict]) -> Dict:
        """
        Calcola quante formazioni ci sono per ogni macro-area, distinguendo tra "regular" e "in prova".
        """
        # Lista delle aree: ogni area ha due contatori: regular e prova
        stacked_data = {area: {'regular': 0, 'prova': 0} for area in self.macro_areas}
        
        # Mappatura per lookup veloce case-insensitive
        macro_map = {m.upper(): m for m in self.macro_areas}

        for f in all_formazioni: # iteriamo su tutte le formazioni indipendentemente dallo stato
            for a in f.get('Area', []): # una formazione può avere più aree, quindi iteriamo su tutte
                area_upper = a.upper().strip()
                
                # Caso speciale: "In prova" generico diventa il ramo 'prova' di 'All'
                if area_upper == 'IN PROVA':
                    stacked_data['All']['prova'] += 1
                    continue

                is_prova = 'PROVA' in area_upper # true se è "{{are}} in prova" o simili
                # Pulizia nome area per trovare la macro-area (es. "IT IN PROVA" -> "IT")
                clean_a = area_upper.replace(' IN PROVA', '').strip()
                
                if clean_a in macro_map:
                    m_key = macro_map[clean_a]
                    stacked_data[m_key]['prova' if is_prova else 'regular'] += 1
                else:
                    logger.warning(f"Area non riconosciuta saltata negli analytics: '{a}'")

        # Filtriamo le aree con almeno una formazione
        final_labels = [m for m in self.macro_areas if (stacked_data[m]['regular'] + stacked_data[m]['prova']) > 0]

        return {
            'formatted': {
                'area_labels': final_labels,
                'area_regular': [stacked_data[m]['regular'] for m in final_labels],
                'area_prova': [stacked_data[m]['prova'] for m in final_labels],
            },
            'stacked_raw': stacked_data
        }

    def _get_time_stats(self, dated_formazioni: List[Dict]) -> Dict:
        """
        Genera le serie temporali storica (continua) e annuale (per selettore).
        """
        # 1. Contiamo quante formazioni ci sono per ogni mese-anno (es. "2024-03") per la timeline storica
        timeline_counts = Counter()
        for f in dated_formazioni:
            key = f['_dt'].strftime('%Y-%m') # chiave per mese-anno
            timeline_counts[key] += 1

        full_timeline_labels = []
        full_timeline_values = []
        
        if dated_formazioni:
            # capiamo il range temporale per generare una timeline completa
            first_date = dated_formazioni[0]['_dt']
            last_date = dated_formazioni[-1]['_dt']
            
            curr = datetime(first_date.year, first_date.month, 1)
            while curr <= last_date: # iteriamo mese per mese fino all'ultimo mese con dati
                key = curr.strftime('%Y-%m')
                # E segnamo il mese-anno in formato "Mar 24" per le label, e il conteggio (0 se non c'è) per i valori
                full_timeline_labels.append(f"{self.ita_months_short[curr.month-1]} {curr.strftime('%y')}")
                full_timeline_values.append(timeline_counts[key])
                # Incremento mese
                if curr.month == 12: curr = datetime(curr.year + 1, 1, 1)
                else: curr = datetime(curr.year, curr.month + 1, 1)

        # 2. Timeline per Anno (Dati per selettore in dashboard)
        yearly_data = defaultdict(lambda: [0]*12) # per ogni anno, una lista di 12 mesi con i conteggi
        for f in dated_formazioni: 
            yearly_data[f['_dt'].year][f['_dt'].month - 1] += 1 # incrementiamo il mese corretto (0-based) per l'anno corrispondente

        # Gli anni disponibili per il selettore (ordinati dal più recente al più vecchio)
        available_years = sorted(list(set(f['_dt'].year for f in dated_formazioni)), reverse=True)

        return {
            'timeline_labels': full_timeline_labels,
            'timeline_values': full_timeline_values,
            'available_years': available_years,
            'yearly_data': dict(yearly_data)
        }

    def _get_periodo_stats(self, all_formazioni: List[Dict]) -> List[Dict]:
        """
        Calcola quante formazioni ci sono per ogni "Periodo" e la loro percentuale sul totale
        """
        total_count = len(all_formazioni)
        periodo_counts = Counter()
        for f in all_formazioni: # iteriamo su tutte le formazioni 
            p = f.get('Periodo', 'Altro')
            if p: periodo_counts[p] += 1 # aumentiamo il contatore del periodo

        periodo_stats = []
        for p, count in periodo_counts.items(): # per ogni periodo
            periodo_stats.append({ 
                'label': p, # nome del periodo
                'count': count, # numero di formazioni in quel periodo
                'perc': round((count / total_count * 100), 1) # percentuale sul totale
            })
        return sorted(periodo_stats, key=lambda x: x['count'], reverse=True)

    def _calculate_kpis(self, all_formazioni: List[Dict], dated_formazioni: List[Dict], stacked_data: Dict) -> Dict:
        """
        Calcola i KPI principali: Area Regina, Media Accademica e Media Globale.
        """
        total_count = len(all_formazioni)
        
        # 1. Area Regina (Macro-area con più volume)
        top_area = max(stacked_data.items(), key=lambda x: x[1]['regular'] + x[1]['prova'])[0]

        # 2. Media Accademica (da Settembre scorso ad oggi)
        now = datetime.now()
        academic_start = datetime(now.year, 9, 1) if now.month >= 9 else datetime(now.year - 1, 9, 1)
        
        academic_formazioni = [f for f in dated_formazioni if f['_dt'] >= academic_start]
        months_passed_academic = (now.year - academic_start.year) * 12 + now.month - academic_start.month + 1
        avg_academic = round(len(academic_formazioni) / months_passed_academic, 1) if months_passed_academic > 0 else 0


        # 3. Media Globale (DI SEMPRE): Totale / numero mesi dal primo dato ad oggi
        avg_global = 0
        if dated_formazioni:
            # mese e anno della prima formazione 
            first_date = dated_formazioni[0]['_dt']
            
            # Allineamento all'inizio dell'anno accademico (Settembre) della prima formazione
            start_year = first_date.year if first_date.month >= 9 else first_date.year - 1
            tmp_curr = datetime(start_year, 9, 1)

            # mese e anno attuale
            now = datetime.now()
            limit_date = datetime(now.year, now.month, 1)

            # contiamo quanti mesi ci sono da tmp_curr a limit_date (incluso) 
            total_months = 0
            while tmp_curr <= limit_date:
                total_months += 1
                # Incremento mese
                if tmp_curr.month == 12: tmp_curr = datetime(tmp_curr.year + 1, 1, 1)
                else: tmp_curr = datetime(tmp_curr.year, tmp_curr.month + 1, 1)
            # Calcoliamo la media globale
            avg_global = round(total_count / total_months, 1) if total_months > 0 else 0


        return {
            'top_area': top_area,
            'avg_academic': avg_academic,
            'avg_global': avg_global
        }
