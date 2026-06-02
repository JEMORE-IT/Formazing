"""
Microsoft Graph Client - Autenticazione e configurazione.

Gestisce l'autenticazione OAuth2 con Microsoft Graph API usando MSAL.
"""

import logging
from msal import ConfidentialClientApplication
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GraphClientError(Exception):
    """Eccezione base per errori del client Microsoft Graph."""
    pass


class GraphClient:
    """Client Microsoft Graph con autenticazione OAuth2."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_email: str):
        """
        Inizializza il client Microsoft Graph.
        
        Args:
            tenant_id: Azure AD Tenant ID
            client_id: Application (client) ID
            client_secret: Client secret value
            user_email: Email dell'utente organizzatore (lucadileo@jemore.it)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
        self._msal_client = None
        self._access_token = None
        self._token_expiry = None  # Traccia scadenza token
        
        logger.debug(f"GraphClient inizializzato | User: {user_email}")
    
    def _get_access_token(self) -> str:
        """
        Acquisisce access token via OAuth2 con gestione automatica scadenza.
        
        Il token viene automaticamente rinnovato se:
        - Non esiste ancora
        - È scaduto
        - Sta per scadere (entro 5 minuti)
        
        Returns:
            str: Access token valido
        """
        # Controlla se token valido e non scaduto
        if self._access_token and self._token_expiry:
            # Buffer di 5 minuti prima della scadenza per sicurezza
            if datetime.now() < self._token_expiry - timedelta(minutes=5):
                logger.debug("Using cached access token (still valid)")
                return self._access_token
            else:
                logger.info("Token expired or expiring soon, refreshing...")
                self._access_token = None  # Invalida token scaduto
            
        try:
            if not self._msal_client:
                self._msal_client = ConfidentialClientApplication(
                    client_id=self.client_id,
                    client_credential=self.client_secret,
                    authority=self.authority
                )
            
            result = self._msal_client.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                self._access_token = result["access_token"]
                
                # Calcola scadenza token (default 3600 secondi = 1 ora)
                expires_in = result.get("expires_in", 3600)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"Access token acquisito | Expiry: {self._token_expiry.strftime('%H:%M:%S')}")
                return self._access_token
            else:
                error_msg = result.get("error_description", "Unknown error")
                raise GraphClientError(f"Token acquisition failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Authentication error | Error: {e}")
            raise GraphClientError(f"Authentication failed: {str(e)}")
    
    def make_request(self, method: str, endpoint: str, json_data: dict = None) -> dict:
        """
        Effettua una richiesta HTTP a Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: Endpoint relativo (es. '/me/events')
            json_data: Optional payload JSON
            
        Returns:
            Risposta JSON decodificata
        """
        url = f"{self.graph_endpoint}{endpoint}"
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            
            if response.status_code == 204:
                return {}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
            except:
                error_detail = e.response.text
            
            logger.error(f"Graph API error | Status: {e.response.status_code} | Detail: {error_detail}")
            raise GraphClientError(f"API request failed: {error_detail}")
            
        except Exception as e:
            logger.error(f"Request error | Error: {e}")
            raise GraphClientError(f"Request failed: {str(e)}")
