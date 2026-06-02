"""
NotionService - Facade unificata per moduli Notion

Questo modulo espone:
- API pubblica unificata (backward compatible)
- Orchestrazione moduli specializzati
- Error handling centralizzato
- Interface semplificata per il resto del sistema

ARCHITETTURA MODULARE:
- NotionClient: Connessione e autenticazione
- NotionQueryBuilder: Costruzione query
- NotionDataParser: Parsing e mapping dati
- NotionCrudOperations: Operazioni database
- NotionDiagnostics: Monitoring e debug
"""

import logging
from typing import List, Dict, Optional

from .notion_client import NotionClient, NotionClientError
from .query_builder import NotionQueryBuilder
from .data_parser import NotionDataParser
from .crud_operations import NotionCrudOperations
from .diagnostics import NotionDiagnostics


logger = logging.getLogger(__name__)


class NotionService:
    """
    Facade unificata per tutti i servizi Notion.
    
    BACKWARD COMPATIBILITY: Mantiene stessa API del monolite precedente.
    
    RESPONSABILITÀ:
    - Orchestrazione moduli specializzati
    - API pubblica semplificata
    - Error handling centralizzato
    - Delegation pattern per operazioni specifiche
    """
    
    def __init__(self, token: str = None, database_id: str = None):
        """
        Inizializza NotionService con architettura modulare.
        
        Args:
            token: Token Notion (da .env se None)
            database_id: ID database formazioni (da .env se None)
        """
        try:
            # Inizializzazione moduli in ordine di dipendenza
            self.client = NotionClient(token, database_id)
            self.query_builder = NotionQueryBuilder()
            self.data_parser = NotionDataParser()
            self.crud_operations = NotionCrudOperations(self.client)
            self.diagnostics = NotionDiagnostics(self.client)
            
            logger.debug("NotionService modulare inizializzato | Componenti: Client, QueryBuilder, DataParser, CRUD, Diagnostics")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione NotionService | Error: {e}")
            raise NotionServiceError(f"Inizializzazione fallita: {e}")
    
    # ===============================
    # API PUBBLICA - BACKWARD COMPATIBLE
    # ===============================
    
    async def get_formazioni_by_status(self, status: str) -> List[Dict]:
        """
        Recupera formazioni filtrate per status specifico.
        
        METODO PRINCIPALE - Stesso API del monolite precedente.
        
        Args:
            status: Status formazione ("Programmata", "Calendarizzata", "Conclusa")
            
        Returns:
            List[Dict]: Lista formazioni filtrate e normalizzate
            
        Raises:
            NotionServiceError: Errori API o parsing dati
        """
        try:
            # 1. Costruisci query con QueryBuilder
            query = self.query_builder.build_status_filter_query(
                status=status,
                database_id=self.client.get_database_id()
            )
            
            # 2. Esegui query con Client
            response = self.client.get_client().databases.query(**query)
            
            # 3. Parsa risultati con DataParser
            formazioni = self.data_parser.parse_formazioni_list(response)
            
            logger.info(f"Formazioni recuperate | Status: '{status}' | Count: {len(formazioni)}")
            return formazioni
            
        except Exception as e:
            logger.error(f"Errore query formazioni | Status: '{status}' | Error: {e}")
            raise NotionServiceError(f"Errore recupero formazioni: {e}")
    
    async def get_dashboard_data(self) -> Dict[str, List[Dict]]:
        """
        Recupera tutti i dati per la dashboard in un'unica operazione ottimizzata.
        
        GESTISCE:
        - Singola chiamata API globale (più veloce di 3 chiamate separate)
        - Paginazione automatica (supera il limite dei 100 record di Notion)
        - Suddivisione dati in Python per stato
        
        Returns:
            Dict[str, List[Dict]]: Dizionario con chiavi 'Programmata', 'Calendarizzata', 'Conclusa'
        """
        try:
            all_raw_results = []
            next_cursor = None
            has_more = True
            
            # Ciclo di paginazione per recuperare TUTTI i record (anche > 100)
            while has_more:
                query = self.query_builder.build_all_records_query(
                    database_id=self.client.get_database_id(),
                    next_cursor=next_cursor
                )
                
                response = self.client.get_client().databases.query(**query)
                all_raw_results.extend(response.get('results', []))
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
                
                if has_more:
                    logger.debug(f"Paginazione Notion attiva... recuperati finora {len(all_raw_results)} record")
            
            # Parsing completo della lista unica
            # Creiamo un oggetto finto di risposta per riutilizzare parse_formazioni_list
            fake_response = {'results': all_raw_results}
            formazioni_totali = self.data_parser.parse_formazioni_list(fake_response)
            
            # Suddivisione in Python
            dashboard_data = {
                'Programmata': [],
                'Calendarizzata': [],
                'Conclusa': []
            }
            
            for f in formazioni_totali:
                stato = f.get('Stato')
                if stato in dashboard_data:
                    dashboard_data[stato].append(f)
                else:
                    logger.warning(f"Formazione '{f['Nome']}' ha uno stato sconosciuto: '{stato}'")
            
            logger.info(f"Dashboard data pronta | Totale: {len(formazioni_totali)} | "
                       f"P: {len(dashboard_data['Programmata'])} | "
                       f"C: {len(dashboard_data['Calendarizzata'])} | "
                       f"F: {len(dashboard_data['Conclusa'])}")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Errore critico nel recupero dashboard data: {e}")
            raise NotionServiceError(f"Errore ottimizzazione query: {e}")

    async def update_formazione(self, notion_id: str, updates: Dict) -> bool:
        """
        Aggiorna formazione con campi multipli in una singola operazione atomica.
        
        METODO UNIFICATO per tutti gli aggiornamenti.
        Supporta: Stato, Codice, Link Teams, e altri campi.
        
        Args:
            notion_id: ID della formazione da aggiornare
            updates: Dict con campi da aggiornare (es: {'Stato': 'Calendarizzata', 'Codice': 'IT-01'})
            
        Returns:
            bool: True se aggiornamento riuscito
            
        Raises:
            NotionServiceError: Errori API o validazione
        """
        try:
            success = await self.crud_operations.update_multiple_fields(notion_id, updates)
            
            if success:
                logger.info(f"Formazione {notion_id} aggiornata con successo")
            else:
                logger.error(f"Fallito aggiornamento formazione {notion_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Errore aggiornamento formazione | ID: ...{notion_id[-8:]} | Error: {e}")
            raise NotionServiceError(f"Errore aggiornamento: {e}")
    
    async def update_formazione_status(self, notion_id: str, new_status: str) -> bool:
        """
        Aggiorna status di una formazione specifica.
        
        DEPRECATO: Usa update_formazione({'Stato': new_status}) invece.
        Mantenuto per backward compatibility.
        """
        logger.warning("DEPRECATED: update_formazione_status | Usa update_formazione invece")
        return await self.update_formazione(notion_id, {'Stato': new_status})
    
    async def update_codice_e_link(self, notion_id: str, codice: str, link_teams: str) -> bool:
        """
        Aggiorna codice formazione e link Teams.
        
        DEPRECATO: Usa update_formazione({'Codice': codice, 'Link Teams': link_teams}) invece.
        Mantenuto per backward compatibility.
        """
        logger.warning("DEPRECATED: update_codice_e_link | Usa update_formazione invece")
        return await self.update_formazione(notion_id, {
            'Codice': codice,
            'Link Teams': link_teams
        })
    
    async def get_formazione_by_id(self, notion_id: str) -> Optional[Dict]:
        """
        Recupera formazione specifica per ID Notion.
        
        Delega a CrudOperations.
        """
        return await self.crud_operations.get_formazione_by_id(notion_id, self.data_parser)
    
    async def test_connection(self) -> Dict:
        """
        Testa connessione API Notion e configurazione database.
        
        Delega a Diagnostics.
        """
        return await self.diagnostics.test_connection()
    
    def get_service_stats(self) -> Dict:
        """
        Statistiche interne servizio per monitoring.
        
        Delega a Diagnostics.
        """
        return self.diagnostics.get_service_stats()
    
    # ===============================
    # API ESTESE - NUOVE FUNZIONALITÀ
    # ===============================
    
    async def get_formazioni_by_area(self, area: str) -> List[Dict]:
        """
        Recupera formazioni filtrate per area aziendale.
        
        NUOVA FUNZIONALITÀ abilitata dall'architettura modulare.
        """
        try:
            query = self.query_builder.build_area_filter_query(
                area=area,
                database_id=self.client.get_database_id()
            )
            
            response = self.client.get_client().databases.query(**query)
            formazioni = self.data_parser.parse_formazioni_list(response)
            
            logger.info(f"Formazioni recuperate | Area: '{area}' | Count: {len(formazioni)}")
            return formazioni
            
        except Exception as e:
            logger.error(f"Errore query formazioni | Area: '{area}' | Error: {e}")
            raise NotionServiceError(f"Errore recupero per area: {e}")
    
    async def get_formazioni_by_status_and_area(self, status: str, area: str) -> List[Dict]:
        """
        Recupera formazioni con filtri combinati.
        
        NUOVA FUNZIONALITÀ per query complesse.
        """
        try:
            query = self.query_builder.build_combined_filter_query(
                status=status,
                area=area,
                database_id=self.client.get_database_id()
            )
            
            response = self.client.get_client().databases.query(**query)
            formazioni = self.data_parser.parse_formazioni_list(response)
            
            logger.info(f"Formazioni recuperate | Filtri combinati | Count: {len(formazioni)}")
            return formazioni
            
        except Exception as e:
            logger.error(f"Errore query filtri combinati | Error: {e}")
            raise NotionServiceError(f"Errore recupero combinato: {e}")
    
    async def validate_database_structure(self) -> Dict:
        """
        Valida struttura database per compatibilità.
        
        NUOVA FUNZIONALITÀ per setup e manutenzione.
        """
        return await self.diagnostics.validate_database_structure()
    
    async def batch_update_status(self, formazioni_ids: List[str], new_status: str) -> Dict:
        """
        Aggiorna status per batch di formazioni.
        
        NUOVA FUNZIONALITÀ per operazioni bulk.
        """
        return await self.crud_operations.batch_update_status(formazioni_ids, new_status)


class NotionServiceError(Exception):
    """Eccezione specifica per errori NotionService."""
    pass


# Export pubblici per backward compatibility
__all__ = [
    'NotionService',
    'NotionServiceError'
]
