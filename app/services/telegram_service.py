"""
Telegram Service - Servizio principale per comunicazioni Telegram

STRUTTURA SEMPLIFICATA:
======================
- Core messaging e configurazione
- Integrazione con moduli bot specializzati
- Gestione lifecycle bot (start/stop)
- Solo funzionalità essenziali

MODULI ESTERNI:
- bot.telegram_formatters: Formattazione messaggi
- bot.telegram_commands: Comandi bot interattivi
"""

import os
import json
import logging
import yaml
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import telegram
from telegram.ext import Application

from config import proteus

try:
    from .bot import TelegramFormatter, TelegramCommands
except ImportError:
    from bot import TelegramFormatter, TelegramCommands

# Logger per TelegramService (configurazione centralizzata già attiva)
logger = logging.getLogger(__name__)


# ===============================
# CLASSE PRINCIPALE SERVIZIO TELEGRAM  
# ===============================

class TelegramService:
    """
    Servizio principale per gestire comunicazioni Telegram del sistema Formazing.
    
    RESPONSABILITÀ CORE:
    - Invio notifiche formazioni ai gruppi target
    - Configurazione e lifecycle bot Telegram
    - Integrazione con moduli specializzati (formatters, commands)
    
    MODULI DELEGATI:
    - TelegramFormatter: formattazione messaggi con template YAML
    - TelegramCommands: gestione comandi bot interattivi
    """
    
    def __init__(
        self, 
        token: str, 
        notion_service,  # NotionService dependency (obbligatorio per comandi bot)
        groups_config_path: str = None, 
        templates_config_path: str = None
    ):
        """
        Inizializza servizio con configurazioni esterne e dipendenze.
        
        Args:
            token (str): Token bot Telegram da BotFather
            notion_service: Istanza NotionService per comandi bot interattivi
            groups_config_path (str): Path telegram_groups.json
            templates_config_path (str): Path message_templates.yaml
        """
        self.token = token or proteus.get('TELEGRAM.BOT_TOKEN')
        self.notion_service = notion_service
        
        # Carica configurazioni da Proteus (già caricate in config.py)
        # Il namespace 'telegram.groups' contiene i dati del file JSON
        self.groups = proteus.get('telegram.groups', {})
        # Rimuoviamo commenti se presenti nel dizionario caricato
        if '_comment' in self.groups:
            del self.groups['_comment']
            
        # Il namespace 'telegram.templates' contiene i dati del file YAML
        self.templates = proteus.get('telegram.templates', {})
        if not self.templates:
            logger.warning("Template Telegram non trovati in Proteus, uso fallback")
            self.templates = self._get_fallback_templates()
        
        # Componenti helper
        self.formatter = TelegramFormatter(self.templates)
        self.commands = TelegramCommands(self)
        self.commands.notion_service = notion_service
        
        logger.debug(f"TelegramService inizializzato via Proteus | Gruppi: {len(self.groups)}")
    
    # ===============================
    # LOGICA TARGETING E FORMATTAZIONE MESSAGGI
    # ===============================
    
    def _get_target_groups(self, training_data: Dict) -> List[str]:
        """
        Determina i gruppi Telegram target per una formazione specifica.
        
        CORE LOGIC:
        - Analizza Area e Periodo della formazione per determinare destinatari
        - Include sempre main_group (tranne per formazioni OUT)
        - Aggiunge gruppi area specifici in base al targeting
        
        REGOLE TARGETING:
        1. Periodo 'OUT': nessun invio (formazioni annullate/rimandate)
        2. Area 'All': main_group + tutti i gruppi area 
        3. Area specifica: main_group + gruppo dell'area specifica
        4. Area non riconosciuta: solo main_group
        
        AREE STANDARD SUPPORTATE:
        ['IT', 'R&D', 'HR', 'Legale', 'Commerciale', 'Marketing']
        
        Args:
            training_data (Dict): Dati formazione con chiavi 'Area' e 'Periodo'
            
        Returns:
            List[str]: Lista gruppi target (vuota per formazioni OUT)
        """
        target_groups = []
        
        # Area arriva già normalizzata come lista dal DataParser
        areas = training_data.get('Area', [])
        if not isinstance(areas, list):
            # Fallback per backward compatibility (se arriva ancora come stringa)
            areas = [a.strip() for a in str(areas).split(',') if a.strip()]
        
        periodo = training_data.get('Periodo', '').strip()
        
        # Formazioni OUT non ricevono comunicazioni
        if periodo == 'OUT':
            logger.info(f"Formazione OUT (esterna) - nessun targeting | Area: {areas}")
            return []
        
        # Il gruppo principale riceve sempre le comunicazioni (tranne OUT)
        if 'main_group' in self.groups:
            target_groups.append('main_group')
        
        # Logica targeting gruppi area
        if 'All' in areas or 'all' in [a.lower() for a in areas]:
            # Formazione per tutti: aggiungi tutti i gruppi area configurati
            for area_name in ['IT', 'R&D', 'HR', 'Legale', 'Commerciale', 'Marketing']:
                if area_name in self.groups:
                    target_groups.append(area_name)
            logger.info(f"Targeting 'All' | Gruppi: {len(target_groups)} (main + {len(target_groups)-1} aree)")
        else:
            # Formazione per aree specifiche: aggiungi ogni area presente
            configured_areas = [area for area in areas if area in self.groups]
            not_configured = [area for area in areas if area not in self.groups]
            
            for area in configured_areas:
                target_groups.append(area)
            
            if not_configured:
                logger.warning(f"Aree non configurate in telegram_groups.json: {', '.join(not_configured)}")
            
            if configured_areas:
                logger.info(f"🎯 Targeting aree specifiche | Gruppi: {len(target_groups)} "
                           f"(main + {', '.join(configured_areas)})")
        
        return target_groups
    

    # ===============================
    # GESTIONE MESSAGGI E NOTIFICHE
    # ===============================
    
    async def send_message_to_group(self, group_key: str, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Invia un messaggio a un gruppo Telegram specifico, con supporto per i topic.
        
        FUNZIONE CORE:
        - Legge la configurazione del gruppo, che ora è un oggetto con `chat_id` e `topic_id` opzionale.
        - Invia il messaggio al topic specificato, se presente.
        - Mantiene la compatibilità con la vecchia configurazione (stringa semplice).
        
        Args:
            group_key (str): Chiave del gruppo in telegram_groups.json ('IT', 'main_group', etc.)
            message (str): Messaggio da inviare (supporta HTML)
            parse_mode (str): Modalità parsing ('HTML', 'Markdown', None). Default: 'HTML'
            
        Returns:
            bool: True se messaggio inviato con successo, False in caso di errore
        """
        if group_key not in self.groups:
            logger.error(f"Gruppo '{group_key}' non configurato in telegram_groups.json")
            return False

        group_config = self.groups[group_key]
        
        if isinstance(group_config, dict):
            chat_id = group_config.get('chat_id')
            topic_id = group_config.get('topic_id')
        else:
            # Fallback per retrocompatibilità se la config non è un oggetto
            chat_id = group_config
            topic_id = None

        if not chat_id:
            logger.error(f"chat_id mancante per gruppo '{group_key}'")
            return False

        try:
            # Crea un client bot temporaneo per questa operazione
            async with telegram.Bot(token=self.token) as bot:
                kwargs = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                }
                if topic_id:
                    kwargs['message_thread_id'] = topic_id
                
                await bot.send_message(**kwargs)
            
            topic_info = f", topic: {topic_id}" if topic_id else ""
            logger.info(f"Messaggio inviato | Gruppo: {group_key} | Chat: {chat_id}{topic_info}")
            
            return True
            
        except telegram.error.TelegramError as e:
            logger.error(f"TelegramError invio messaggio | Gruppo: {group_key} | Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore imprevisto invio messaggio | Gruppo: {group_key} | Error: {e}", exc_info=True)
            return False
    
    
    async def send_training_notification(self, training_data: Dict, custom_messages: Dict[str, str] = None) -> Dict[str, bool]:
        """
        Invia notifica di nuova formazione ai gruppi appropriati usando template YAML.
        
        UTILIZZO PRINCIPALE:
        - Chiamato dal training_service quando una formazione viene calendarizzata
        - Determina automaticamente gruppi target (main + area specifica)
        - Usa template personalizzati per main_group vs area_group
        
        LOGICA TARGETING:
        - Formazioni 'All': invio a main_group + tutti i gruppi area 
        - Formazioni specifiche: invio a main_group + gruppo area specifica
        - Formazioni 'OUT': nessun invio (formazioni erogate all'esterno)
        
        Args:
            training_data (Dict): Dati formazione da Notion con chiavi:
                - Nome: titolo formazione
                - Area: area target ('IT', 'HR', 'All', etc.)
                - Data/Ora: data/ora formazione
                - Codice: codice identificativo 
                - Link Teams: link meeting
                - Periodo: periodo formazione ('Programmata', 'OUT', etc.)
                
        Returns:
            Dict[str, bool]: Risultati invio per ogni gruppo target
                             {'main_group': True, 'IT': False, ...}                             
        """
        results = {}
        
        # Determina gruppi target in base ad area e periodo della formazione
        target_groups = self._get_target_groups(training_data)
        
        # Se nessun gruppo target (es. formazioni OUT), ritorna risultato vuoto
        if not target_groups:
            logger.info(f"Nessun gruppo target per notifica | Formazione: {training_data.get('Nome', 'N/A')}")
            return results
        
        # Invia messaggio a ogni gruppo target
        for group_key in target_groups:
            # Usa il messaggio personalizzato se fornito, altrimenti usa il formatter (template)
            if custom_messages and group_key in custom_messages:
                message = custom_messages[group_key]
                logger.debug(f"Uso messaggio personalizzato per gruppo: {group_key}")
            else:
                message = self.formatter.format_training_message(training_data, group_key)
            
            # Se il messaggio è vuoto (l'utente ha cancellato tutto), saltiamo l'invio
            if not message or not message.strip():
                logger.info(f"Messaggio vuoto per {group_key}, invio saltato.")
                results[group_key] = True # Consideriamolo un successo (intenzione dell'utente)
                continue
            
            success = await self.send_message_to_group(group_key, message)
            results[group_key] = success
        
        successful = sum(1 for s in results.values() if s)
        logger.info(f"Notifica formazione completata | Successo: {successful}/{len(results)} | "
                   f"Gruppi: {', '.join(results.keys())}")
        return results
    
    async def send_feedback_notification(self, training_data: Dict, feedback_link: str, custom_messages: Dict[str, str] = None) -> Dict[str, bool]:
        """
        Invia richiesta feedback post-formazione ai gruppi area (NO main_group).
        
        SCOPO:
        - Sollecita feedback da partecipanti dopo formazione completata
        - Invia solo a gruppi area specifici (non spam al gruppo principale)
        - Include link diretto al form di feedback
        
        DIFFERENZA DA TRAINING_NOTIFICATION:
        - Non include mai il main_group (evita spam feedback)
        - Usa template feedback_request dal file YAML
        - Target solo gruppi area specifici della formazione
        
        QUANDO USARE:
        - Dopo completamento formazione (status 'Completata' in Notion)
        - Quando è disponibile link form feedback
        - Per sollecitare valutazioni qualità formazione
        
        Args:
            training_data (Dict): Dati formazione con Nome, Area, Codice
            feedback_link (str): URL diretto al form di feedback online
            
        Returns:
            Dict[str, bool]: Risultati invio per gruppi area (escluso main_group)
            
        ESEMPIO:
            results = await service.send_feedback_notification(
                training_data={'Nome': 'Python Basics', 'Area': 'IT', 'Codice': 'PY001'},
                feedback_link='https://forms.office.com/feedback123'
            )
            # Risultato: {'IT': True} (solo gruppo IT, no main_group)
        """
        results = {}
        
        # Ottieni tutti i gruppi target della formazione
        all_target_groups = self._get_target_groups(training_data)
        
        # Rimuovi main_group dai target (feedback solo a gruppi area)
        target_groups = [group for group in all_target_groups if group != 'main_group' and group != 'In_prova']
        
        if not target_groups:
            logger.info(f"Nessun gruppo area per feedback | Formazione: {training_data.get('Nome', 'N/A')}")
            return results
        
        # Invia richiesta feedback a ogni gruppo area
        logger.info(f"Invio richiesta feedback | Target: {len(target_groups)} gruppi area | "
                   f"Formazione: {training_data.get('Nome', 'N/A')}")
        
        for group_key in target_groups:
            # Usa il messaggio personalizzato se fornito
            if custom_messages and group_key in custom_messages:
                message = custom_messages[group_key]
                logger.debug(f"Uso messaggio feedback personalizzato per gruppo: {group_key}")
            else:
                message = self.formatter.format_feedback_message(training_data, feedback_link, group_key)
            
            success = await self.send_message_to_group(group_key, message)
            results[group_key] = success
        
        successful = sum(1 for s in results.values() if s)
        logger.info(f"Richiesta feedback completata | Successo: {successful}/{len(results)} | "
                   f"Gruppi: {', '.join(results.keys())}")
        return results
    
    # ===============================
    # GESTIONE LIFECYCLE BOT TELEGRAM (per run_bot.py)
    # ===============================
    
    def run_bot_sync(self):
        """
        Esegue il bot in modalità sincrona per script standalone o testing.
        
        UTILIZZO:
        - Script standalone per testing bot comandi
        - Debugging interattivo senza applicazione Flask
        - Demo o prototipazione funzionalità bot
        
        FUNZIONALITÀ:
        - Gestione automatica event loop asyncio
        - Gestione CTRL+C per shutdown pulito
        - Mantiene bot attivo fino a interruzione utente
        
        PROCESSO:
        1. Crea event loop asyncio
        2. Avvia bot con start_bot()
        3. Mantiene esecuzione con Event().wait()
        4. Gestisce KeyboardInterrupt per shutdown graceful
        5. Chiama stop_bot() nel finally
        
        ESEMPIO USO:
            service = TelegramService(token="...")
            service.run_bot_sync()  # Bot resta attivo fino a CTRL+C
        """
        async def main():
            # Crea l'Application instance qui, solo per il processo del bot
            application = Application.builder().token(self.token).build()
            
            # Registra i comandi sull'istanza dell'applicazione
            self.commands.register_handlers(application)
            logger.info("Comandi bot configurati per il processo di polling.")

            try:
                logger.info("Avvio del bot Telegram in modalit polling...")
                await application.initialize()
                await application.start()
                await application.updater.start_polling()
                logger.info("Bot Telegram avviato con successo e in ascolto comandi.")
                
                # Mantieni il processo in vita
                await asyncio.Event().wait()

            except (KeyboardInterrupt, SystemExit):
                logger.info("Interruzione ricevuta, avvio spegnimento pulito del bot...")
            
            finally:
                if application.updater and application.updater.is_running:
                    await application.updater.stop()
                if application.running:
                    await application.stop()
                await application.shutdown()
                logger.info("Bot Telegram fermato con successo.")
        
        try:
            asyncio.run(main())
        except Exception as e:
            logger.critical(f"Errore critico nel loop principale del bot: {e}", exc_info=True)



# ===============================
# UTILITY FUNCTIONS E FACTORY METHODS
# ===============================

def create_telegram_service_from_config(config_dict: Dict) -> TelegramService:
    """
    Factory method per creare TelegramService da configurazione dict.
    
    UTILIZZO:
    - Inizializzazione servizio in app Flask da variabili ambiente
    - Testing con configurazioni mock
    - Setup centralizzato con validazione parametri
    
    VANTAGGI:
    - Validazione token obbligatorio con errore chiaro
    - Gestione parametri opzionali con defaults
    - Separazione configurazione da istanziazione
    
    Args:
        config_dict (Dict): Configurazione con chiavi:
            - TELEGRAM_BOT_TOKEN (obbligatorio): Token bot da BotFather
            - TELEGRAM_GROUPS_CONFIG (opzionale): Path telegram_groups.json
            - TELEGRAM_TEMPLATES_CONFIG (opzionale): Path message_templates.yaml
            
    Returns:
        TelegramService: Istanza configurata e pronta all'uso
    """
    token = config_dict.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN mancante nella configurazione")
    
    groups_config_path = config_dict.get('TELEGRAM_GROUPS_CONFIG')
    templates_config_path = config_dict.get('TELEGRAM_TEMPLATES_CONFIG')
    
    return TelegramService(
        token=token, 
        groups_config_path=groups_config_path,
        templates_config_path=templates_config_path
    )


async def test_telegram_connection(service: TelegramService) -> bool:
    """
    Testa connettività e validità del token bot Telegram.
    
    UTILIZZO:
    - Validazione setup durante inizializzazione app
    - Health check per monitoraggio sistema
    - Debugging problemi connettività bot
    
    VERIFICA:
    - Validità token tramite API getMe
    - Connettività di rete verso Telegram
    - Configurazione corretta bot
    
    Args:
        service (TelegramService): Istanza servizio da testare
        
    Returns:
        bool: True se connessione e token validi, False altrimenti
        
    SIDE EFFECTS:
    - Logga informazioni bot (username, nome) se successo
    - Logga errori dettagliati se fallimento
    
    ESEMPIO:
        if not await test_telegram_connection(service):
            logger.error("Bot non configurato correttamente")
            return
    """
    try:
        bot_info = await service.bot.get_me()
        logger.info(f"Bot Telegram connesso: @{bot_info.username} ({bot_info.first_name})")
        return True
    except Exception as e:
        logger.error(f"Errore nella connessione al bot Telegram: {e}")
        return False


def validate_groups_config(groups_config: Dict[str, Dict]) -> List[str]:
    """
    Valida completezza e correttezza della nuova configurazione gruppi Telegram.
    
    VALIDAZIONI:
    1. Presenza di 'main_group'.
    2. Presenza delle aree standard.
    3. Ogni gruppo deve essere un dizionario con una chiave 'chat_id'.
    4. Il valore di 'chat_id' deve essere una stringa che inizia con '-'.
    5. 'topic_id' (se presente) deve essere un numero intero.
    """
    errors = []
    
    if 'main_group' not in groups_config:
        errors.append("Gruppo principale 'main_group' mancante")
    
    standard_areas = ['IT', 'R&D', 'HR', 'Legale', 'Commerciale', 'Marketing']
    for area in standard_areas:
        if area not in groups_config:
            errors.append(f"Gruppo per area '{area}' mancante")
    
    for group_name, config in groups_config.items():
        if not isinstance(config, dict):
            errors.append(f"La configurazione per il gruppo '{group_name}' non è un oggetto JSON.")
            continue

        chat_id = config.get('chat_id')
        if not chat_id:
            errors.append(f"'chat_id' mancante per il gruppo '{group_name}'")
        elif not isinstance(chat_id, str) or not chat_id.startswith('-'):
            errors.append(f"'chat_id' per il gruppo '{group_name}' non è valido: {chat_id}")

        topic_id = config.get('topic_id')
        if topic_id and not isinstance(topic_id, int):
            errors.append(f"'topic_id' per il gruppo '{group_name}' deve essere un numero intero.")
            
    return errors


# ===============================
# ESEMPIO DI UTILIZZO E TESTING
# ===============================

if __name__ == "__main__":
    """
    Script standalone per testing e demo funzionalità TelegramService.
    
    FUNZIONALITÀ DEMO:
    - Caricamento configurazione da variabili ambiente
    - Test connessione bot Telegram
    - Validazione configurazione gruppi
    - Esempio invio messaggio (commentato per sicurezza)
    - Avvio bot interattivo (commentato per sicurezza)
    
    SETUP RICHIESTO:
    1. File .env con TELEGRAM_BOT_TOKEN
    2. File config/telegram_groups.json configurato
    3. File config/message_templates.yaml configurato
    
    ESECUZIONE:
        python app/services/telegram_service.py
    """
    from config import proteus
    
    async def main():
        """Funzione principale demo."""
        # Ottieni istanza NotionService (necessaria per il bot)
        from app.services.notion import NotionService
        notion_service = NotionService()
        
        try:
            # Creazione servizio pescando tutto da Proteus
            service = TelegramService(
                token=proteus.get('TELEGRAM.BOT_TOKEN'),
                notion_service=notion_service
            )
            logger.info(f"TelegramService creato con {len(service.groups)} gruppi")
            
        except ValueError as e:
            logger.error(f"Errore configurazione: {e}")
            return
        
        # Test connessione al bot
        if not await test_telegram_connection(service):
            logger.error("Impossibile connettersi al bot Telegram")
            return
        
        # Validazione configurazione gruppi
        errors = validate_groups_config(service.groups)
        if errors:
            logger.warning("Errori nella configurazione gruppi:")
            for error in errors:
                logger.warning(f"- {error}")
        else:
            logger.info("Configurazione gruppi valida")
        
        # Esempio di invio messaggio di test (DECOMMENTARE PER TESTARE)
        # ATTENZIONE: Invia messaggio reale ai gruppi configurati!
        """
        test_message = "🤖 <b>Test Bot Formazing</b>\n\n✅ <i>Il bot funziona correttamente!</i>"
        success = await service.send_message_to_group('main_group', test_message)
        logger.info(f"Invio messaggio test: {' Successo' if success else ' Fallito'}")
        """
        
        # Avvio bot per comandi interattivi (DECOMMENTARE PER TESTARE)
        # ATTENZIONE: Bot resta attivo e risponde a comandi!
        """
        logger.info("Avvio bot per comandi interattivi...")
        logger.info("Prova i comandi: /oggi, /domani, /settimana, /help")
        logger.info("Premi CTRL+C per fermare il bot")
        await service.start_bot()
        """
        
        logger.info("Demo completata con successo")
    
    # Esecuzione demo
    asyncio.run(main())