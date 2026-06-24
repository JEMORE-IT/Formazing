"""
Configurazione centralizzata Formazing App via Proteus.

Inizializza il ConfigurationManager di Proteus caricando le variabili d'ambiente
in formato nested (es. FLASK__PORT -> flask.port).
"""

import os
import logging
import logging.config
from proteus import ConfigurationManager

# Inizializza il manager di Proteus (Singleton)
# Lo chiamiamo 'proteus' per chiarezza negli import
proteus = ConfigurationManager.instance()

# Calcola i path base
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(BASE_DIR, '.env')
config_dir = os.path.join(BASE_DIR, 'config')

# 1. Carica variabili d'ambiente da file .env
if os.path.exists(env_path):
    proteus.load(env_path)

# Carica anche le variabili d'ambiente di sistema (es. in produzione/Docker)
# Questo permette alle variabili in os.environ di sovrascrivere o integrare quelle del file .env
proteus.load_environ(prefixes=['FLASK_', 'NOTION_', 'TELEGRAM_', 'MICROSOFT_', 'AUTH_', 'LOG_', 'APP_', 'MSAL_'])

# 2. Carica configurazioni JSON/YAML in namespace dedicati
# Grazie alla nuova feature 'namespace', i file piatti vengono isolati correttamente
configs_to_load = [
    ('telegram_groups.json', 'telegram.groups'),
    ('message_templates.yaml', 'telegram.templates'),
    ('faqs.yaml', 'app.guide'),
    ('microsoft_emails.json', 'microsoft.emails'),
    ('calendar_templates.yaml', 'microsoft.templates')
]

for filename, namespace in configs_to_load:
    path = os.path.join(config_dir, filename)
    if os.path.exists(path):
        proteus.load(path, namespace=namespace)
        logging.info(f"Configurazione caricata: {filename} -> namespace: {namespace}")

def setup_logging():
    """Configura logging centralizzato usando i valori caricati in Proteus."""
    log_file = proteus.get('LOG.FILE', 'logs/formazing.log')
    log_level = proteus.get('LOG.LEVEL', 'INFO').upper()
    log_max_bytes = proteus.get('LOG.MAX_BYTES', 10 * 1024 * 1024, cast=int)
    log_backup_count = proteus.get('LOG.BACKUP_COUNT', 5, cast=int)
    log_name_width = proteus.get('LOG.NAME_WIDTH', 50, cast=int)
    
    log_format = f'%(asctime)s | %(levelname)-5s | %(name)-{log_name_width}s | %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {'format': log_format, 'datefmt': log_date_format},
            'console': {'format': log_format, 'datefmt': '%H:%M:%S'}
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'console',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'standard',
                'filename': log_file,
                'maxBytes': log_max_bytes,
                'backupCount': log_backup_count,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            '': {'handlers': ['console', 'file'], 'level': log_level, 'propagate': False},
            'app': {'handlers': ['console', 'file'], 'level': log_level, 'propagate': False},
            'telegram': {'handlers': ['console', 'file'], 'level': 'CRITICAL', 'propagate': False},
            'httpx': {'handlers': ['console', 'file'], 'level': 'WARNING', 'propagate': False}
        }
    }
    
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info(f"[START] Formazing - Proteus Config Engine attivo (file: {log_file})")
    logger.info("=" * 80)

def validate_config() -> dict:
    """Valida la presenza delle chiavi critiche nel manager Proteus."""
    results = {
        'telegram': bool(proteus.get('TELEGRAM.BOT_TOKEN')),
        'notion': bool(proteus.get('NOTION.TOKEN') and proteus.get('NOTION.DATABASE_ID')),
        'microsoft': bool(
            proteus.get('MICROSOFT.CLIENT_ID') and 
            proteus.get('MICROSOFT.CLIENT_SECRET') and 
            proteus.get('MICROSOFT.TENANT_ID')
        ),
        'auth': bool(proteus.get('AUTH.ALLOWED_DOMAINS'))
    }
    results['overall_ok'] = all(results.values())
    return results

