"""
Telegram Formatters - Gestione template e formattazione messaggi

Questo modulo si occupa di:
- Formattazione messaggi usando template YAML
- Parsing e conversione date da diversi formati
- Gestione template per main_group vs area_group
- Fallback per errori di formattazione
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class TelegramFormatter:
    """
    Gestisce formattazione messaggi usando template YAML.
    
    RESPONSABILITÀ:
    - Formattazione messaggi training notification
    - Formattazione messaggi feedback request
    - Parsing date multi-formato (ISO, custom)
    - Gestione template personalizzati per tipo gruppo
    """
    
    def __init__(self, templates: Dict):
        """
        Inizializza formatter con template YAML.
        
        Args:
            templates (Dict): Template strutturati da file YAML
        """
        self.templates = templates
        logger.debug("TelegramFormatter inizializzato")
    
    def format_training_message(self, training_data: Dict, group_key: str) -> str:
        """
        Formatta messaggio notifica formazione usando template appropriato.
        
        LOGICA TEMPLATE:
        - main_group: template generico per gruppo principale
        - area_group: template specifico per gruppi area (più personale)
        
        Args:
            training_data (Dict): Dati formazione da Notion
            group_key (str): Gruppo destinatario ('main_group' o area specifica)
            
        Returns:
            str: Messaggio HTML formattato pronto per Telegram
        """
        # Estrazione dati con fallback 'N/A'
        nome = training_data.get('Nome', 'N/A')
        area_raw = training_data.get('Area', 'N/A')
        
        # Formatta Area: lista → stringa (es. ['IT', 'R&D'] → 'IT, R&D')
        if isinstance(area_raw, list):
            area = ', '.join(area_raw) if area_raw else 'N/A'
        else:
            area = area_raw if area_raw else 'N/A'
        
        data_ora = training_data.get('Data/Ora', 'N/A')
        codice = training_data.get('Codice', 'N/A')
        link_teams = training_data.get('Link Teams', 'N/A')

        # Parsing e formattazione data (supporta ISO e formato custom)
        data_formattata = self._format_date_time(data_ora)
        
        # Preparazione dati per template
        template_data = {
            'nome': nome,
            'area': area, 
            'data_ora': data_formattata,
            'codice': codice,
            'link_teams': link_teams
        }
        
        # Selezione template appropriato
        training_templates = self.templates.get('training_notification', {}).get('telegram', {})
        
        if group_key == 'main_group':
            template = training_templates.get('main_group', 'Template main_group non trovato')
        else:
            template = training_templates.get('area_group', 'Template area_group non trovato')
        
        # Formattazione con gestione errori
        try:
            formatted_message = template.format(**template_data)
            logger.debug(f"Messaggio training formattato per {group_key}: {len(formatted_message)} caratteri")
            return formatted_message
        except (KeyError, ValueError) as e:
            logger.error(f"Errore formattazione template training per {group_key}: {e}")
            return f"Errore nella formattazione del messaggio per la formazione: {nome}"
    
    def format_feedback_message(self, training_data: Dict, feedback_link: str, group_key: str) -> str:
        """
        Formatta messaggio richiesta feedback usando template YAML.
        
        CARATTERISTICHE:
        - Template unico per tutti i gruppi (feedback_request)
        - Include link diretto al form di feedback
        - Ottimizzato per engagement con CTA chiare
        
        Args:
            training_data (Dict): Dati formazione (Nome, Area, Codice)
            feedback_link (str): URL form di feedback 
            group_key (str): Gruppo destinatario (per logging)
            
        Returns:
            str: Messaggio HTML formattato per richiesta feedback
        """
        # Estrazione dati essenziali
        nome = training_data.get('Nome', 'N/A')
        area_raw = training_data.get('Area', 'N/A')
        
        # Formatta Area: lista -> stringa (es. ['IT', 'R&D'] -> 'IT, R&D')
        if isinstance(area_raw, list):
            area = ', '.join(area_raw) if area_raw else 'N/A'
        else:
            area = area_raw if area_raw else 'N/A'
        
        codice = training_data.get('Codice', 'N/A')
        
        # Preparazione dati template
        template_data = {
            'nome': nome,
            'area': area,
            'codice': codice,
            'feedback_link': feedback_link
        }
        
        # Recupero template feedback (unico per tutti i gruppi)
        feedback_template = (self.templates.get('feedback_request', {})
                           .get('telegram', {})
                           .get('message', 'Template feedback non trovato'))
        
        # Formattazione con gestione errori
        try:
            formatted_message = feedback_template.format(**template_data)
            logger.debug(f"Messaggio feedback formattato per {group_key}: {len(formatted_message)} caratteri")
            return formatted_message
        except (KeyError, ValueError) as e:
            logger.error(f"Errore formattazione template feedback: {e}")
            return f"Errore nella formattazione del messaggio feedback per la formazione: {nome}"
    
    def _format_date_time(self, data_ora) -> str:
        """
        Formatta data/ora da diversi formati in formato italiano dd/mm/yyyy HH:MM.
        
        FORMATI SUPPORTATI:
        - ISO format: "2024-09-22T14:30:00Z" → "22/09/2024 14:30"
        - Custom format: "22/09/2024 14:30" → "22/09/2024 14:30"
        - Altri: fallback a stringa originale
        
        Args:
            data_ora: Data/ora in formato vario
            
        Returns:
            str: Data formattata o stringa originale se parsing fallisce
        """
        try:
            if isinstance(data_ora, str) and data_ora != 'N/A':
                if 'T' in data_ora:  # Formato ISO da Notion API
                    dt = datetime.fromisoformat(data_ora.replace('Z', '+00:00'))
                    return dt.strftime('%d/%m/%Y %H:%M')
                else:  # Formato custom dd/mm/yyyy HH:MM (già formattato)
                    dt = datetime.strptime(data_ora, '%d/%m/%Y %H:%M')
                    return dt.strftime('%d/%m/%Y %H:%M')
            else:
                return str(data_ora)
        except Exception as e:
            logger.warning(f"Errore parsing data '{data_ora}': {e}")
            return str(data_ora)