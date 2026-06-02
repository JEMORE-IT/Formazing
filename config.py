"""
Configurazione centralizzata Formazing App

Gestisce caricamento variabili ambiente e configurazioni globali
per tutti i servizi (Telegram, Notion, Microsoft Graph, Flask).
"""

import os
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


# Carica automaticamente variabili da .env
load_dotenv()


class Config:
    """Configurazione base application."""
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # ===== FLASK CONFIG =====
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    # ===== AUTH & RBAC CONFIG (Microsoft SSO) =====
    ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', 'jemore.it').split(',')
    ADMIN_USERS = os.getenv('ADMIN_USERS', '').split(',')
    MSAL_REDIRECT_URI = os.getenv('MSAL_REDIRECT_URI', f'http://localhost:{FLASK_PORT}/auth/callback')
    # Authority URL per JEMORE (Single Tenant o Common)
    MSAL_AUTHORITY = f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID', 'common')}"
    MSAL_SCOPES = ["User.Read"]
    
    # ===== TELEGRAM CONFIG =====
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_GROUPS_CONFIG = 'config/telegram_groups.json'
    TELEGRAM_TEMPLATES_CONFIG = 'config/message_templates.yaml'
    
    # ===== NOTION CONFIG =====
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # ===== MICROSOFT GRAPH CONFIG =====
    MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID')
    MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET') 
    MICROSOFT_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID')
    MICROSOFT_USER_EMAIL = os.getenv('MICROSOFT_USER_EMAIL')  # Organizzatore eventi (es. lucadileo@jemore.it)
    
    # ===== LOGGING CONFIG =====
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.getenv('LOG_FILE', 'logs/formazing.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10 MB default
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))  # 5 file di backup
    # Width (in characters) reserved for the logger/module name column.
    # Increase via environment variable LOG_NAME_WIDTH if names are long.
    LOG_NAME_WIDTH = int(os.getenv('LOG_NAME_WIDTH', 50))
    LOG_FORMAT = f'%(asctime)s | %(levelname)-5s | %(name)-{LOG_NAME_WIDTH}s | %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    @classmethod
    def setup_logging(cls):
        """
        Configura logging centralizzato per tutta l'applicazione.
        
        CARATTERISTICHE:
        - RotatingFileHandler per evitare log file troppo grandi
        - Output sia su console che su file
        - Formato consistente con timestamp, livello, modulo, messaggio
        - Livello configurabile via variabile ambiente LOG_LEVEL
        - Gestione automatica rotazione log (max 10MB per file, 5 backup)
        
        UTILIZZO:
        - Chiamare UNA SOLA VOLTA all'avvio dell'applicazione (app factory o main)
        - Tutti i moduli usano poi logging.getLogger(__name__) senza configurazioni aggiuntive
        """
        # Crea directory logs se non esiste
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Configurazione logging con dictConfig
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': cls.LOG_FORMAT,
                    'datefmt': cls.LOG_DATE_FORMAT
                },
                'console': {
                    'format': cls.LOG_FORMAT,
                    'datefmt': '%H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': cls.LOG_LEVEL,
                    'formatter': 'console',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': cls.LOG_LEVEL,
                    'formatter': 'standard',
                    'filename': cls.LOG_FILE,
                    'maxBytes': cls.LOG_MAX_BYTES,
                    'backupCount': cls.LOG_BACKUP_COUNT,
                    'encoding': 'utf-8'
                }
            },
            'loggers': {
                # Root logger - cattura tutto
                '': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                # Logger specifici per moduli chiave (livello dettagliato)
                'app': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                # NOTION SERVICE - Database operations
                'app.services.notion': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.notion.client': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.notion.crud': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.notion.query': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                # MICROSOFT SERVICE - Graph API, Calendar, Email
                'app.services.microsoft': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.microsoft.graph': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.microsoft.calendar': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                # TELEGRAM SERVICE - Bot e messaging
                'app.services.telegram': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                'app.services.telegram.bot': {
                    'handlers': ['console', 'file'],
                    'level': cls.LOG_LEVEL,
                    'propagate': False
                },
                # Riduci verbosità librerie esterne per evitare spam di errori di rete
                'telegram': {
                    'handlers': ['console', 'file'],
                    'level': 'CRITICAL',
                    'propagate': False
                },
                'httpx': {
                    'handlers': ['console', 'file'],
                    'level': 'WARNING',
                    'propagate': False
                },
                'httpcore': {
                    'handlers': ['console', 'file'],
                    'level': 'WARNING',
                    'propagate': False
                }
            }
        }
        
        logging.config.dictConfig(logging_config)
        
        # Log messaggio di conferma configurazione
        logger = logging.getLogger(__name__)
        logger.info("=" * 80)
        logger.info("[START] Formazing Application - Logging configurato")
        logger.info(f"[LOGS] Log file: {cls.LOG_FILE} (max {cls.LOG_MAX_BYTES // (1024*1024)}MB, {cls.LOG_BACKUP_COUNT} backup)")
        logger.info(f"Log level: {cls.LOG_LEVEL}")
        logger.info("Servizi: Notion | Microsoft | Telegram | Routes")
        logger.info("=" * 80)
    
    @classmethod
    def validate_config(cls) -> dict:
        """
        Valida configurazione critica per startup.
        
        Returns:
            dict: Risultati validazione per ogni servizio
        """
        validation = {
            'telegram': bool(cls.TELEGRAM_BOT_TOKEN),
            'notion': bool(cls.NOTION_TOKEN and cls.NOTION_DATABASE_ID),
            'microsoft_graph': bool(
                cls.MICROSOFT_CLIENT_ID and 
                cls.MICROSOFT_CLIENT_SECRET and 
                cls.MICROSOFT_TENANT_ID and
                cls.MICROSOFT_USER_EMAIL
            ),
            'flask_auth': bool(cls.BASIC_AUTH_PASSWORD),
            'overall_ok': False
        }
        
        # Almeno Telegram e Notion devono essere configurati
        # Microsoft Graph è opzionale ma consigliato
        validation['overall_ok'] = validation['telegram'] and validation['notion']
        
        return validation