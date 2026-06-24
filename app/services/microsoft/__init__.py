"""
Microsoft Service - Facade per integrazione Microsoft Graph e Teams.

Fornisce API unificata per la creazione di eventi calendario con Teams meeting.

Architettura modulare:
- graph_client: Autenticazione e client Graph API
- email_formatter: Template engine per corpo eventi
- calendar_operations: Creazione eventi calendario

Uso:
    from app.services.microsoft import MicrosoftService
    
    service = MicrosoftService()
    result = await service.create_training_event(formazione_data)
"""

import logging
from typing import Dict, Optional
from .graph_client import GraphClient, GraphClientError
from .email_formatter import EmailFormatter, EmailFormatterError
from .calendar_operations import CalendarOperations, CalendarOperationsError

logger = logging.getLogger(__name__)


class MicrosoftServiceError(Exception):
    """Eccezione base per errori del Microsoft Service."""
    pass


class MicrosoftService:
    """Facade per operazioni Microsoft Graph e Teams."""
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_email: Optional[str] = None,
        template_path: Optional[str] = None
    ):
        """
        Inizializza il Microsoft Service.
        
        Args:
            tenant_id: Azure AD Tenant ID (da .env se None)
            client_id: Application client ID (da .env se None)
            client_secret: Client secret (da .env se None)
            user_email: Email organizzatore (da .env se None)
            template_path: Path custom per template calendario
        """
        # Carica da config se non forniti
        if any(x is None for x in [tenant_id, client_id, client_secret, user_email]):
            from config import proteus
            tenant_id = tenant_id or proteus.get('MICROSOFT.TENANT_ID')
            client_id = client_id or proteus.get('MICROSOFT.CLIENT_ID')
            client_secret = client_secret or proteus.get('MICROSOFT.CLIENT_SECRET')
            user_email = user_email or proteus.get('MICROSOFT.USER_EMAIL')
        
        # Inizializza sottomoduli (senza TeamsMeeting)
        self.graph_client = GraphClient(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            user_email=user_email
        )
        
        self.email_formatter = EmailFormatter(template_path)
        
        self.calendar_operations = CalendarOperations(
            graph_client=self.graph_client,
            email_formatter=self.email_formatter
        )
        
        logger.debug("MicrosoftService inizializzato | Componenti: GraphClient, EmailFormatter, CalendarOperations")
    
    async def create_training_event(self, formazione_data: Dict, custom_body: str = None) -> Dict:
        """
        Crea un evento calendario con Teams meeting per una formazione.
        
        Metodo principale del facade - orchestrazione completa.
        USA DIRETTAMENTE I NOMI DEI CAMPI NOTION (no mapping).
        
        Args:
            formazione_data: Dati formazione da Notion
                {
                    'Nome': 'Sicurezza Informatica',
                    'Codice': 'IT-Security-2024-SPRING-01',
                    'Data/Ora': '15/10/2024 14:30',
                    'Area': ['IT', 'R&D']
                }
        
        Returns:
            Dict con risultato creazione:
            {
                'event_id': 'AAMkAGI...',
                'teams_link': 'https://teams.microsoft.com/l/meetup-join/...',
                'calendar_link': 'https://outlook.office365.com/...',
                'subject': 'Sicurezza Informatica',
                'start_date': '2024-01-15T14:30:00',
                'attendee_emails': ['it@jemore.it', 'rd@jemore.it'],
                'status': 'success'
            }
        
        Raises:
            MicrosoftServiceError: Se la creazione fallisce
        
        Examples:
            >>> service = MicrosoftService()
            >>> formazione = {
            ...     'Nome': 'Python Training',
            ...     'Codice': 'IT-PY-2024-01',
            ...     'Data/Ora': '15/10/2024 10:00',
            ...     'Area': ['IT']
            ... }
            >>> result = await service.create_training_event(formazione)
            >>> print(result['teams_link'])
            'https://teams.microsoft.com/l/meetup-join/...'
        """
        try:
            # Valida dati input
            self._validate_formazione_data(formazione_data)
            
            # Delega a calendar_operations
            result = self.calendar_operations.create_calendar_event(formazione_data, custom_body)
            
            # Aggiungi status
            result['status'] = 'success'
            
            logger.info(
                f"Evento Teams creato | Subject: {result.get('subject')} | "
                f"Event ID: ...{result.get('event_id', '')[-12:]}"
            )
            
            return result
            
        except (CalendarOperationsError, EmailFormatterError, GraphClientError) as e:
            logger.error(f"MicrosoftService error | Component error: {e}")
            raise MicrosoftServiceError(f"Failed to create training event: {str(e)}")
        except Exception as e:
            logger.error(f"Errore imprevisto creazione evento | Error: {e}")
            raise MicrosoftServiceError(f"Unexpected error: {str(e)}")
    
    def _validate_formazione_data(self, formazione_data: Dict) -> None:
        """
        Valida che formazione_data contenga tutti i campi richiesti.
        Usa i nomi dei campi Notion (con lettera maiuscola).
        
        Args:
            formazione_data: Dati formazione
            
        Raises:
            MicrosoftServiceError: Se mancano campi obbligatori
        """
        required_fields = ['Nome', 'Data/Ora', 'Area']
        missing_fields = [f for f in required_fields if f not in formazione_data]
        
        if missing_fields:
            raise MicrosoftServiceError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        logger.debug(f"Validazione dati formazione completata | Nome: {formazione_data.get('Nome')}")
    
    def get_service_info(self) -> Dict:
        """
        Ottiene informazioni sul servizio configurato.
        
        Returns:
            Dict con configurazione servizio (senza secrets)
        """
        return {
            'tenant_id': self.graph_client.tenant_id,
            'user_email': self.graph_client.user_email,
            'template_path': str(self.email_formatter.template_path),
            'areas_configured': len(self.calendar_operations.area_emails)
        }


# Export pubblico
__all__ = [
    'MicrosoftService',
    'MicrosoftServiceError',
    'GraphClient',
    'GraphClientError',
    'EmailFormatter',
    'EmailFormatterError',
    'CalendarOperations',
    'CalendarOperationsError'
]
