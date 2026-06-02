"""
NotionClient - Core client e gestione connessione

Questo modulo gestisce:
- Inizializzazione e autenticazione client Notion
- Validazione configurazione critica
- Gestione credenziali e sicurezza
- Error handling di base per connessione
"""

import logging
import os
from notion_client import Client


logger = logging.getLogger(__name__)


class NotionClient:
    """
    Client core per connessione e autenticazione API Notion.
    
    RESPONSABILITÀ:
    - Configurazione e validazione credenziali
    - Inizializzazione client Notion ufficiale  
    - Gestione connessione base
    - Cache configurazione per ottimizzazioni
    """
    
    def __init__(self, token: str = None, database_id: str = None):
        """
        Inizializza client Notion con autenticazione.
        
        Args:
            token: Token Notion (da .env se None)
            database_id: ID database formazioni (da .env se None)
        
        Raises:
            ValueError: Se credenziali mancanti
            Exception: Se inizializzazione client fallisce
        """
        # Configurazione credenziali
        self.token = token or os.getenv('NOTION_TOKEN')
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        
        # Validazione configurazione critica
        self._validate_credentials()
        
        # Inizializzazione client Notion
        try:
            self.client = Client(auth=self.token)
            logger.debug("NotionClient inizializzato | Database ID: ...%s", self.database_id[-8:] if len(self.database_id) > 8 else self.database_id)
        except Exception as e:
            logger.error(f"Errore inizializzazione NotionClient | Error: {e}")
            raise
        
        # Cache per ottimizzazioni
        self._cache_ttl = 300  # 5 minuti
        self._last_cache_time = None
        self._cached_data = {}
    
    def _validate_credentials(self):
        """Valida che tutte le credenziali necessarie siano configurate."""
        if not self.token or not self.token.strip():
            raise ValueError("NOTION_TOKEN non configurato")
        if not self.database_id or not self.database_id.strip():
            raise ValueError("NOTION_DATABASE_ID non configurato")
    
    def get_client(self) -> Client:
        """Ritorna client Notion autenticato."""
        return self.client
    
    def get_database_id(self) -> str:
        """Ritorna ID database formazioni."""
        return self.database_id
    
    def get_config_info(self) -> dict:
        """
        Informazioni configurazione per debugging.
        
        Returns:
            dict: Info configurazione (senza esporre credenziali)
        """
        return {
            'token_configured': bool(self.token),
            'database_id_configured': bool(self.database_id),
            'database_id_preview': self.database_id[:8] + '...' if self.database_id else None,
            'cache_ttl_seconds': self._cache_ttl
        }


class NotionClientError(Exception):
    """Eccezione specifica per errori NotionClient."""
    pass