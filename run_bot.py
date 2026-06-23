# run_bot.py
"""
🤖 Processo dedicato per Bot Telegram Formazing

Esegue il bot Telegram in modalità polling per gestire comandi interattivi
come /oggi, /domani, /settimana senza interferire con il processo Flask.
"""

import logging
from app.services.training_service import TrainingService
from config import setup_logging

# Configura logging centralizzato PRIMA di tutto
setup_logging()

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Avvio processo dedicato Bot Telegram Formazing")
    logger.info("Comandi disponibili: /oggi, /domani, /settimana, /help")
    logger.info("Premi CTRL+C per fermare il bot")
    logger.info("=" * 80)

    # Ottieni l'istanza del TrainingService (Singleton)
    # Crea e configura tutti i servizi necessari (NotionService, TelegramService)
    training_service = TrainingService.get_instance()
    logger.info("TrainingService Singleton inizializzato")
    
    # Usa il metodo run_bot_sync per gestire il bot in modalità polling
    # Gestisce avvio, ascolto comandi e spegnimento pulito
    try:
        logger.info("Avvio bot in modalità polling...")
        training_service.telegram_service.run_bot_sync()
    except KeyboardInterrupt:
        logger.info("Interruzione utente ricevuta (CTRL+C)")
    except Exception as e:
        logger.critical(f"❌ Errore critico nel processo bot: {e}", exc_info=True)
    finally:
        logger.info("=" * 80)
        logger.info("Processo bot terminato")
        logger.info("=" * 80)

