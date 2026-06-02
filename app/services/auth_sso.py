"""
Auth SSO Service - Gestione autenticazione Microsoft e permessi RBAC.
"""

import msal
import logging
import threading
import asyncio
from flask import session, redirect, url_for
from functools import wraps
from config import Config

logger = logging.getLogger(__name__)

# ======================
# 1. Servizio di autenticazione (MSAL)
# ======================

class AuthService:
    """
    Gestisce l'interazione con Microsoft (MSAL).
    Implementato come Singleton per riutilizzare l'istanza MSAL.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Inizializza MSAL solo una volta
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.msal_app = msal.ConfidentialClientApplication(
            Config.MICROSOFT_CLIENT_ID,
            authority=Config.MSAL_AUTHORITY,
            client_credential=Config.MICROSOFT_CLIENT_SECRET
        )
        logger.debug("MSAL ConfidentialClientApplication inizializzata")

    def build_auth_url(self):
        """Genera l'URL per il login Microsoft."""
        return self.msal_app.get_authorization_request_url(
            Config.MSAL_SCOPES,
            redirect_uri=Config.MSAL_REDIRECT_URI
        )

    def get_token_from_code(self, auth_code):
        """Scambia il codice di autorizzazione per un token e i dati utente."""
        return self.msal_app.acquire_token_by_authorization_code(
            auth_code,
            scopes=Config.MSAL_SCOPES,
            redirect_uri=Config.MSAL_REDIRECT_URI
        )

    def build_logout_url(self, redirect_to):
        """Genera l'URL per il logout da Microsoft."""
        return (
            f"{Config.MSAL_AUTHORITY}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={redirect_to}"
        )

    @classmethod
    def get_instance(cls):
        """Factory method per ottenere l'istanza singleton."""
        return cls()


# ======================
# 2. Decoratori di protezione (RBAC)
# ======================

def login_required(f):
    """Protegge le rotte richiedendo il login e il dominio corretto."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            logger.info("Accesso negato: utente non loggato. Redirect a login.")
            return redirect(url_for('main.home'))
        
        # Controllo dominio (Whitelist)
        email = user.get('preferred_username', '').lower()
        domain = email.split('@')[-1] if '@' in email else ''
        
        if domain not in Config.ALLOWED_DOMAINS:
            logger.warning(f"Accesso negato: dominio '{domain}' non autorizzato per {email}")
            session.clear()
            return "Dominio non autorizzato. Usa l'account JEMORE.", 403
            
        # Gestione asincrona: se la funzione originale è async, dobbiamo attenderla
        if asyncio.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Protegge le rotte critiche richiedendo privilegi di admin."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Prima assicurati che sia loggato
        user = session.get('user')
        if not user:
            return redirect(url_for('main.home'))
            
        # Controllo se è admin
        if not session.get('is_admin'):
            email = user.get('preferred_username', '')
            logger.warning(f"Accesso negato a risorsa admin per: {email}")
            return "Accesso Negato: Non hai i permessi per eseguire questa operazione.", 403
            
        # Gestione asincrona
        if asyncio.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function
