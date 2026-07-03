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
    
    async def get_meeting_attendance(self, join_url: str) -> dict:
        """
        Recupera i dettagli di presenza di una chiamata Teams tramite joinUrl.
        
        Fa tre chiamate in sequenza a Microsoft Graph API:
        1. Cerca il meeting online per recuperare l'ID:
           GET /users/{userId}/onlineMeetings?$filter=joinWebUrl eq '{joinUrl}'
        2. Recupera la lista dei report di presenza per quel meeting:
           GET /users/{userId}/onlineMeetings/{meetingId}/attendanceReports
        3. Ottiene il dettaglio del report di presenza con i record degli utenti:
           GET /users/{userId}/onlineMeetings/{meetingId}/attendanceReports/{reportId}?$expand=attendanceRecords
           
        Args:
            join_url: URL della riunione Teams
            
        Returns:
            Dict: Dizionario contenente:
                - 'participants': List[Dict] (Lista partecipanti con 'name' ed 'email')
                - 'duration': float (Durata in ore decimali, arrotondata a 2 decimali)
                - 'total_participants': int (Numero totale di partecipanti dal report)
        """
        if not join_url:
            logger.warning("join_url vuoto in get_meeting_attendance")
            return {
                'participants': [],
                'duration': 0.0,
                'total_participants': 0
            }
            
        import urllib.parse
        try:
            user_id = self.graph_client.get_user_guid()
            
            # 1. Trova l'onlineMeetingId usando il joinUrl
            filter_query = f"joinWebUrl eq '{join_url}'"
            encoded_filter = urllib.parse.quote(filter_query)
            endpoint = f"/users/{user_id}/onlineMeetings?$filter={encoded_filter}"
            
            logger.debug(f"Ricerca meeting online tramite Graph API | Endpoint: {endpoint}")
            meetings_response = self.graph_client.make_request(
                method="GET",
                endpoint=endpoint
            )
            
            meetings = meetings_response.get('value', [])
            if not meetings:
                logger.warning(f"Nessun meeting online trovato per join_url: {join_url}")
                return {
                    'participants': [],
                    'duration': 0.0,
                    'total_participants': 0
                }
                
            meeting_id = meetings[0].get('id')
            if not meeting_id:
                logger.warning("ID meeting nullo nella risposta Graph API")
                return {
                    'participants': [],
                    'duration': 0.0,
                    'total_participants': 0
                }
                
            # 2. Ottieni i report di presenza
            reports_endpoint = f"/users/{user_id}/onlineMeetings/{meeting_id}/attendanceReports"
            logger.debug(f"Recupero attendance reports | Endpoint: {reports_endpoint}")
            reports_response = self.graph_client.make_request(
                method="GET",
                endpoint=reports_endpoint
            )
            
            reports = reports_response.get('value', [])
            if not reports:
                logger.warning(f"Nessun report di presenza trovato per meeting_id: {meeting_id}")
                return {
                    'participants': [],
                    'duration': 0.0,
                    'total_participants': 0
                }
                
            # Trova il report principale con il maggior numero di partecipanti
            # (evita di selezionare report vuoti generati da riaperture accidentali del link)
            best_report = max(reports, key=lambda r: r.get('totalParticipantCount', 0))
            report_id = best_report.get('id')
            if not report_id:
                logger.warning("ID report di presenza nullo")
                return {
                    'participants': [],
                    'duration': 0.0,
                    'total_participants': 0
                }
                
            # 3. Ottieni i dettagli del report espandendo attendanceRecords
            report_detail_endpoint = f"/users/{user_id}/onlineMeetings/{meeting_id}/attendanceReports/{report_id}?$expand=attendanceRecords"
            logger.debug(f"Download dettaglio report presenze | Endpoint: {report_detail_endpoint}")
            report_detail = self.graph_client.make_request(
                method="GET",
                endpoint=report_detail_endpoint
            )
            
            # Calcolo durata
            meeting_start = report_detail.get('meetingStartDateTime')
            meeting_end = report_detail.get('meetingEndDateTime')
            total_participants = report_detail.get('totalParticipantCount', 0)
            
            duration_hours = 0.0
            if meeting_start and meeting_end:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(meeting_start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(meeting_end.replace('Z', '+00:00'))
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    raw_hours = duration_seconds / 3600.0
                    duration_hours = round(raw_hours * 2) / 2
                    if duration_seconds > 0 and duration_hours == 0.0:
                        duration_hours = 0.5
                except Exception as ex:
                    logger.error(f"Errore parsing orari meeting per durata: {ex}")
            
            records = report_detail.get('attendanceRecords', [])
            logger.info(f"Recuperati {len(records)} record di presenza per meeting {meeting_id} | Durata: {duration_hours}h")
            
            participants = []
            for r in records:
                identity = r.get('identity', {})
                user = identity.get('user', {})
                display_name = user.get('displayName') or r.get('emailAddress') or 'Utente Sconosciuto'
                email = r.get('emailAddress') or user.get('id', '')
                
                participants.append({
                    'name': display_name,
                    'email': email
                })
                
            if not total_participants:
                total_participants = len(participants)
                
            return {
                'participants': participants,
                'duration': duration_hours,
                'total_participants': total_participants
            }
            
        except (GraphClientError, Exception) as e:
            err_str = str(e)
            logger.error(f"Errore recupero presenze Teams per meeting | Error: {e}")
            
            # Messaggi di errore parlanti per utenti non tecnici
            if "3004" in err_str or "Specified meeting is not found" in err_str:
                user_msg = (
                    "Riunione non trovata su Microsoft Teams. "
                    "Verifica che il link Teams presente in Notion sia corretto, che l'evento non sia stato eliminato "
                    "dal calendario e che la chiamata sia stata effettivamente avviata ed utilizzata."
                )
            elif "3003" in err_str or "User does not have access to lookup meeting" in err_str:
                user_msg = (
                    "Accesso negato alla riunione. "
                    "Assicurati che la riunione Teams sia stata organizzata dall'utente configurato nel file .env "
                    "e che l'applicazione abbia le autorizzazioni per accedere ai suoi meeting."
                )
            elif "Insufficient privileges" in err_str:
                user_msg = (
                    "Privilegi insufficienti su Microsoft Graph. "
                    "Verifica che l'applicazione abbia il permesso applicativo 'User.Read.All' "
                    "con consenso dell'amministratore concesso nel portale Azure."
                )
            elif "No application access policy found" in err_str:
                user_msg = (
                    "Policy di accesso mancante in Microsoft Teams. "
                    "L'amministratore IT deve assegnare l'Application Access Policy (tramite PowerShell) all'utente organizzatore."
                )
            else:
                user_msg = f"Errore Microsoft Graph: {err_str}"
                
            raise MicrosoftServiceError(user_msg)

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
