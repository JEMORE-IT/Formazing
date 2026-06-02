"""
NotionCrudOperations - Operazioni CRUD su database Not                "properties": {
                    "Stato": {
                        "status": {
                            "name": new_status
                        }
                    }
                }Questo modulo gestisce:
- Update status, codici, link formazioni
- Create nuove formazioni (futuro)
- Delete operations (futuro)
- Operazioni batch e transazioni
"""

import logging
from typing import Dict, Optional, List
from notion_client.errors import APIResponseError


logger = logging.getLogger(__name__)


class NotionCrudOperations:
    """
    Operazioni CRUD specializzate per database formazioni.
    
    RESPONSABILITÀ:
    - Update status formazioni (workflow transitions)
    - Update codici e link Teams (calendarizzazione)
    - Recupero formazioni singole per ID
    - Gestione errori operazioni critiche
    """
    
    def __init__(self, notion_client):
        """
        Inizializza CRUD operations.
        
        Args:
            notion_client: Client Notion autenticato
        """
        self.client = notion_client.get_client()
        logger.debug("NotionCrudOperations inizializzato")
    
    async def update_formazione_status(self, notion_id: str, new_status: str) -> bool:
        """
        Aggiorna status di una formazione specifica.
        
        WORKFLOW TRANSITIONS:
        - Programmata -> Calendarizzata (dopo invio notifiche)
        - Calendarizzata -> Conclusa (dopo feedback inviato)
        
        Args:
            notion_id: ID interno Notion della formazione
            new_status: Nuovo status ("Programmata", "Calendarizzata", "Conclusa")
        
        Returns:
            bool: True se aggiornamento successful
        """
        if not notion_id:
            logger.error("notion_id nullo in update_formazione_status")
            return False
            
        try:
            response = self.client.pages.update(
                page_id=notion_id,
                properties={
                    "Stato": {
                        "status": {
                            "name": new_status
                        }
                    }
                }
            )
            
            logger.info(f"Status aggiornato | ID: ...{notion_id[-8:]} | New status: {new_status}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore API aggiornamento status | ID: ...{notion_id[-8:]} | Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento status | ID: ...{notion_id[-8:]} | Error: {e}")
            return False
    
    async def update_codice_e_link(self, notion_id: str, codice: str, link_teams: str) -> bool:
        """
        Aggiorna codice formazione e link Teams.
        
        CALENDARIZZAZIONE WORKFLOW:
        - Genera codice univoco (es: IT-Sicurezza_Web-2024-SPRING-01)
        - Salva link Teams generato da Microsoft Graph
        
        Args:
            notion_id: ID interno Notion della formazione
            codice: Codice formazione generato
            link_teams: URL meeting Teams
        
        Returns:
            bool: True se aggiornamento successful
        """
        try:
            properties = {
                "Codice": {
                    "rich_text": [
                        {
                            "text": {
                                "content": codice
                            }
                        }
                    ]
                }
            }
            
            # Aggiungi link Teams solo se presente
            if link_teams and link_teams.strip():
                properties["Link Teams"] = {
                    "url": link_teams
                }
            
            response = self.client.pages.update(
                page_id=notion_id,
                properties=properties
            )
            
            logger.info(f"Codice e link aggiornati | ID: ...{notion_id[-8:]} | Codice: {codice}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore aggiornamento codice/link {notion_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento codice/link {notion_id}: {e}")
            return False
    
    async def get_formazione_by_id(self, notion_id: str, data_parser) -> Optional[Dict]:
        """
        Recupera formazione specifica per ID Notion.
        
        UTILITY per:
        - Operazioni puntuali
        - Validazione dati post-update
        - Refresh stato singola formazione
        
        Args:
            notion_id: ID interno Notion della formazione
            data_parser: Parser per conversione dati
        
        Returns:
            Dict: Formazione normalizzata o None se non trovata
        """
        logger.debug(f"Recupero formazione | ID: ...{notion_id[-8:]}")
        
        try:
            response = self.client.pages.retrieve(page_id=notion_id)
            formazione = data_parser.parse_single_formazione(response)
            
            if formazione:
                logger.debug(f"Formazione recuperata: {formazione['Nome']}")
            else:
                logger.warning(f"Formazione non parsabile: {notion_id}")
            
            return formazione
            
        except APIResponseError as e:
            logger.error(f"Errore recupero formazione {notion_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Errore generico recupero formazione {notion_id}: {e}")
            return None
    
    async def update_multiple_fields(self, notion_id: str, updates: Dict) -> bool:
        """
        Aggiorna multipli campi in una singola operazione.
        
        OPERAZIONE ATOMICA per aggiornamenti complessi.
        
        Args:
            notion_id: ID interno Notion della formazione
            updates: Dizionario con campi da aggiornare
        
        Returns:
            bool: True se aggiornamento successful
        """
        try:
            properties = {}
            
            # Costruisci properties Notion format da updates
            for field, value in updates.items():
                if field == 'Stato':
                    properties["Stato"] = {"status": {"name": value}}
                elif field == 'Codice':
                    properties["Codice"] = {"rich_text": [{"text": {"content": value}}]}
                elif field == 'Link':
                    properties["Link"] = {"url": value}
                elif field == 'Link Teams':
                    properties["Link Teams"] = {"url": value}
                # Aggiungi altri campi se necessario
            
            response = self.client.pages.update(
                page_id=notion_id,
                properties=properties
            )
            
            logger.info(f"Multipli campi aggiornati | ID: ...{notion_id[-8:]} | Campi: {list(updates.keys())}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore aggiornamento multiplo {notion_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento multiplo {notion_id}: {e}")
            return False
    
    async def batch_update_status(self, formazioni_ids: List[str], new_status: str) -> Dict:
        """
        Aggiorna status per batch di formazioni.
        
        UTILE PER: Operazioni bulk (es: chiusura fine anno)
        
        Args:
            formazioni_ids: Lista ID formazioni da aggiornare
            new_status: Nuovo status per tutte
        
        Returns:
            Dict: Risultati batch (success_count, failed_ids)
        """
        logger.info(f"Batch update status | Formazioni: {len(formazioni_ids)} | Target status: {new_status}")
        
        results = {
            'success_count': 0,
            'failed_ids': [],
            'total': len(formazioni_ids)
        }
        
        for notion_id in formazioni_ids:
            success = await self.update_formazione_status(notion_id, new_status)
            if success:
                results['success_count'] += 1
            else:
                results['failed_ids'].append(notion_id)
        
        logger.info(f"Batch update completato | Successo: {results['success_count']}/{results['total']}")
        return results