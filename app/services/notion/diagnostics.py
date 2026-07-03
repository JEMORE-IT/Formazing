"""
NotionDiagnostics - Diagnostica e monitoring Notion

Questo modulo gestisce:
- Test connessione e health checks
- Performance monitoring e metriche
- Error reporting e debugging
- Validazione configurazione sistema
"""

import logging
from typing import Dict
from notion_client.errors import APIResponseError


logger = logging.getLogger(__name__)


class NotionDiagnostics:
    """
    Diagnostica e monitoring per servizi Notion.
    
    RESPONSABILITÀ:
    - Health checks connessione e database
    - Performance metrics e statistiche
    - Validazione configurazione completa
    - Error reporting strutturato
    """
    
    def __init__(self, notion_client):
        """
        Inizializza diagnostics.
        
        Args:
            notion_client: Client Notion per test
        """
        self.client = notion_client.get_client()
        self.database_id = notion_client.get_database_id()
        self.config_info = notion_client.get_config_info()
        logger.debug("NotionDiagnostics inizializzato")
    
    async def test_connection(self) -> Dict:
        """
        Test completo connessione API Notion e accesso database.
        
        HEALTH CHECK COMPLETO per:
        - Connessione API base
        - Autenticazione token
        - Accesso database formazioni
        - Validazione permissions
        
        Returns:
            Dict: Risultati dettagliati test connessione
        """
        logger.info("Avvio test connessione Notion API...")
        
        result = {
            'connection_ok': False,
            'database_accessible': False,
            'user_info': None,
            'database_info': None,
            'permissions': {},
            'error': None,
            'response_time_ms': None
        }
        
        try:
            import time
            start_time = time.time()
            
            # Test 1: Connessione base API
            user_info = self.client.users.me()
            result['connection_ok'] = True
            result['user_info'] = {
                'name': user_info.get('name', 'Unknown'),
                'type': user_info.get('type', 'Unknown'),
                'id': user_info.get('id', 'Unknown')[:8] + '...'  # ID parziale
            }
            
            # Test 2: Accesso database formazioni
            database_info = self.client.databases.retrieve(database_id=self.database_id)
            result['database_accessible'] = True
            result['database_info'] = {
                'title': self._extract_database_title(database_info),
                'id': self.database_id[:8] + '...',  # ID parziale per sicurezza
                'properties_count': len(database_info.get('properties', {})),
                'created_time': database_info.get('created_time', 'Unknown'),
                'last_edited_time': database_info.get('last_edited_time', 'Unknown')
            }
            
            # Test 3: Permissions check
            result['permissions'] = self._check_database_permissions(database_info)
            
            # Timing
            end_time = time.time()
            result['response_time_ms'] = int((end_time - start_time) * 1000)
            
            logger.info("Test connessione completato con successo")
            
        except APIResponseError as e:
            result['error'] = f"Errore API Notion: {e}"
            logger.error(result['error'])
        except Exception as e:
            result['error'] = f"Errore generico: {e}"
            logger.error(result['error'])
        
        return result
    
    def get_service_stats(self) -> Dict:
        """
        Statistiche complete servizio per monitoring.
        
        METRICHE per:
        - Configurazione servizio
        - Performance indicators
        - Resource usage
        - Cache statistics
        
        Returns:
            Dict: Metriche complete servizio
        """
        return {
            'service_name': 'NotionService',
            'version': '2.0.0-modular',
            'notion_client_version': 'notion-client==2.2.1',
            'configuration': self.config_info,
            'modules': {
                'client': 'NotionClient',
                'query_builder': 'NotionQueryBuilder', 
                'data_parser': 'NotionDataParser',
                'crud_operations': 'NotionCrudOperations',
                'diagnostics': 'NotionDiagnostics'
            },
            'capabilities': {
                'query_formazioni': True,
                'update_status': True,
                'update_codice_link': True,
                'batch_operations': True,
                'diagnostics': True
            }
        }
    
    async def validate_database_structure(self) -> Dict:
        """
        Valida struttura database per compatibilità.
        
        VERIFICA:
        - Presenza campi obbligatori
        - Tipi campo corretti
        - Configurazione properties
        
        Returns:
            Dict: Risultati validazione struttura
        """
        logger.info("Validazione struttura database...")
        
        result = {
            'valid': False,
            'required_fields': {},
            'missing_fields': [],
            'incorrect_types': [],
            'warnings': []
        }
        
        # Campi obbligatori e tipi attesi
        expected_fields = {
            'Nome': 'title',
            'Area': 'multi_select',
            'Date': 'date',
            'Stato': 'status',
            'Codice': 'rich_text',
            'Link Teams': 'url',
            'Periodo': 'select',
            'Partecipanti': 'people',
            'Numero Partecipanti': 'number',
            'Durata': 'number'
        }
        
        try:
            database_info = self.client.databases.retrieve(database_id=self.database_id)
            properties = database_info.get('properties', {})
            
            # Verifica campi obbligatori
            for field_name, expected_type in expected_fields.items():
                if field_name in properties:
                    actual_type = properties[field_name].get('type')
                    result['required_fields'][field_name] = {
                        'present': True,
                        'type': actual_type,
                        'correct_type': actual_type == expected_type
                    }
                    
                    if actual_type != expected_type:
                        result['incorrect_types'].append({
                            'field': field_name,
                            'expected': expected_type,
                            'actual': actual_type
                        })
                else:
                    result['missing_fields'].append(field_name)
                    result['required_fields'][field_name] = {
                        'present': False,
                        'type': None,
                        'correct_type': False
                    }
            
            # Determina validità generale
            result['valid'] = len(result['missing_fields']) == 0 and len(result['incorrect_types']) == 0
            

            if result['valid']:
                logger.info("Struttura database valida")
            else:
                logger.warning(f"Struttura database con problemi: {len(result['missing_fields'])} campi mancanti, {len(result['incorrect_types'])} tipi incorretti")
            
        except Exception as e:
            result['error'] = f"Errore validazione: {e}"
            logger.error(result['error'])
        
        return result
    
    def _extract_database_title(self, database_info: Dict) -> str:
        """Estrae titolo database da response Notion."""
        title_array = database_info.get('title', [])
        if title_array and len(title_array) > 0:
            return title_array[0].get('plain_text', 'Unknown')
        return 'Unknown'
    
    def _check_database_permissions(self, database_info: Dict) -> Dict:
        """Verifica permissions database."""
        # Placeholder - Notion non espone permissions direttamente
        return {
            'can_read': True,  # Se arriviamo qui, possiamo leggere
            'can_write': 'unknown',  # Richiederebbe test write
            'can_update': 'unknown'
        }