"""
NotionQueryBuilder - Costruzione query Notion API

Questo modulo gestisce:
- Costruzione filt            ],
            "sorts": [
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ]
        }
        
        return queryAPI strutturati
- Template query riutilizzabili
- Ordinamenti e configurazioni query
- Ottimizzazioni query per performance
"""

import logging
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class NotionQueryBuilder:
    """
    Builder per costruzione query Notion API strutturate.
    
    RESPONSABILITÀ:
    - Costruzione filtri per diversi tipi campo
    - Templates query per casi d'uso comuni
    - Validazione struttura query
    - Ottimizzazioni query performance
    """
    
    def __init__(self):
        """Inizializza query builder."""
        self.default_page_size = 100
        logger.debug("NotionQueryBuilder inizializzato")
    
    def build_status_filter_query(self, status: str, database_id: str) -> Dict:
        """
        Costruisce query filtrata per status formazione.
        
        QUERY PIÙ UTILIZZATA - per comandi bot e dashboard.
        
        Args:
            status: Status da filtrare ("Programmata", "Calendarizzata", "Conclusa")
            database_id: ID database target
        
        Returns:
            Dict: Query strutturata per API Notion
        """
        logger.debug(f"Costruisco query per status: '{status}'")
        
        query = {
            "database_id": database_id,
            "filter": {
                "property": "Stato",
                "status": {
                    "equals": status
                }
            },
            "sorts": [
                {
                    "property": "Date",
                    "direction": "descending" if status == "Conclusa" else "ascending"
                }
            ],
            "page_size": self.default_page_size
        }
        
        logger.debug(f"Query costruita per status '{status}'")
        return query
    
    def build_date_range_filter_query(self, start_date: str, end_date: str, database_id: str) -> Dict:
        """
        Costruisce query per range di date.
        
        UTILE PER: Query settimane, mesi, periodi specifici.
        
        Args:
            start_date: Data inizio (ISO format)
            end_date: Data fine (ISO format)  
            database_id: ID database target
        
        Returns:
            Dict: Query con filtro date range
        """
        logger.debug(f"Costruisco query per range: {start_date} - {end_date}")
        
        query = {
            "database_id": database_id,
            "filter": {
                "and": [
                    {
                        "property": "Date",
                        "date": {
                            "on_or_after": start_date
                        }
                    },
                    {
                        "property": "Date", 
                        "date": {
                            "on_or_before": end_date
                        }
                    }
                ]
            },
            "sorts": [
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ]
        }
        
        return query
    
    def build_area_filter_query(self, area: str, database_id: str) -> Dict:
        """
        Costruisce query filtrata per area.
        
        UTILE PER: Formazioni specifiche per area aziendale.
        
        Args:
            area: Area da filtrare ("IT", "HR", "Marketing", etc.)
            database_id: ID database target
        
        Returns:
            Dict: Query con filtro area
        """
        logger.debug(f"Costruisco query per area: '{area}'")
        
        query = {
            "database_id": database_id,
            "filter": {
                "property": "Area",
                "multi_select": {
                    "contains": area
                }
            },
            "sorts": [
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ]
        }
        
        return query
    
    def build_combined_filter_query(self, status: str, area: str = None, database_id: str = None) -> Dict:
        """
        Costruisce query con filtri combinati.
        
        UTILE PER: Query complesse con multipli criteri.
        
        Args:
            status: Status obbligatorio
            area: Area opzionale
            database_id: ID database target
        
        Returns:
            Dict: Query con filtri combinati
        """
        logger.debug(f"Costruisco query combinata: status={status}, area={area}")
        
        filters = [
            {
                "property": "Stato",
                "status": {
                    "equals": status
                }
            }
        ]
        
        # Aggiungi filtro area se specificato
        if area:
            filters.append({
                "property": "Area",
                "multi_select": {
                    "contains": area
                }
            })
        
        query = {
            "database_id": database_id,
            "filter": {
                "and": filters
            } if len(filters) > 1 else filters[0],
            "sorts": [
                {
                    "property": "Date",
                    "direction": "ascending"
                }
            ]
        }
        
        return query
    
    def build_all_records_query(self, database_id: str, next_cursor: str = None) -> Dict:
        """
        Costruisce query globale senza filtri per recuperare tutto il database.
        
        Args:
            database_id: ID database target
            next_cursor: Cursore per la paginazione Notion
        
        Returns:
            Dict: Query strutturata per API Notion
        """
        logger.debug(f"Costruisco query globale per database: {database_id[:8]}...")
        
        query = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Date",
                    "direction": "descending"
                }
            ],
            "page_size": self.default_page_size
        }
        
        if next_cursor:
            query["start_cursor"] = next_cursor
            
        return query

    def validate_query_structure(self, query: Dict) -> bool:
        """
        Valida struttura query prima dell'invio.
        
        Args:
            query: Query da validare
        
        Returns:
            bool: True se query valida
        """
        required_fields = ['database_id']
        
        for field in required_fields:
            if field not in query:
                logger.error(f"Query invalida: campo '{field}' mancante")
                return False
        
        logger.debug("Query validata con successo")
        return True