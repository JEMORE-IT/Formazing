"""
Email Formatter - Template engine per corpo eventi calendario.

Carica template YAML e rende il corpo degli eventi con interpolazione variabili.
Pattern simile a: bot/telegram_formatters.py
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailFormatterError(Exception):
    """Eccezione per errori nel formatting delle email."""
    pass


class EmailFormatter:
    """
    Formatter per corpo eventi calendario e email.
    
    Pattern: Template engine con YAML + interpolazione variabili.
    Simile a: TelegramFormatter
    """
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Inizializza il formatter caricando i template.
        
        Args:
            template_path: Path al file YAML template (default: config/calendar_templates.yaml)
        """
        if template_path is None:
            # Default path relativo alla root del progetto
            base_path = Path(__file__).parent.parent.parent.parent
            template_path = base_path / "config" / "calendar_templates.yaml"
        
        self.template_path = Path(template_path)
        self.templates = self._load_templates()
        logger.debug(f"EmailFormatter inizializzato | Template: {self.template_path}")
    
    def _load_templates(self) -> Dict:
        """
        Carica i template dal file YAML.
        
        Returns:
            Dict con i template caricati
            
        Raises:
            EmailFormatterError: Se il caricamento fallisce
        """
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
            
            logger.debug(f"Templates caricati | Keys: {list(templates.keys())}")
            return templates
            
        except FileNotFoundError:
            logger.error(f"Template file non trovato | Path: {self.template_path}")
            raise EmailFormatterError(f"Template file not found: {self.template_path}")
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error | Error: {e}")
            raise EmailFormatterError(f"Invalid YAML in template file: {e}")
        except Exception as e:
            logger.error(f"Errore caricamento templates | Error: {e}")
            raise EmailFormatterError(f"Failed to load templates: {e}")
    
    def _format_date(self, date_value) -> str:
        """
        Formatta una data in formato leggibile italiano.
        
        Args:
            date_value: Stringa ISO o oggetto datetime
            
        Returns:
            Data formattata (es. "Lunedì 15 Gennaio 2024 - 14:30")
        """
        try:
            # Se è già una stringa, prova a parsarla
            if isinstance(date_value, str):
                # Gestisce formato ISO con timezone
                date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return str(date_value)
            
            # Mappa giorni e mesi in italiano
            giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
            mesi = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
            
            giorno_settimana = giorni[date_obj.weekday()]
            mese = mesi[date_obj.month - 1]
            
            return f"{giorno_settimana} {date_obj.day} {mese} {date_obj.year} - {date_obj.strftime('%H:%M')}"
            
        except Exception as e:
            logger.warning(f"Date formatting error | Error: {e} | Using original value")
            return str(date_value)
    
    def format_calendar_body(self, formazione_data: Dict) -> str:
        """
        Genera il corpo HTML dell'evento calendario usando il template.
        
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
            Corpo HTML formattato per l'evento
            
        Raises:
            EmailFormatterError: Se il template è mancante o i dati sono invalidi
        """
        try:
            if 'calendar_event' not in self.templates:
                raise EmailFormatterError("Missing 'calendar_event' template")
            
            template = self.templates['calendar_event']['body']
            
            # Formatta la data in italiano
            data_formattata = self._format_date(formazione_data.get('Data/Ora', ''))
            
            # Se Area è una lista, unisci con virgola
            area_value = formazione_data.get('Area', 'N/A')
            if isinstance(area_value, list):
                area_str = ', '.join(area_value)
            else:
                area_str = str(area_value)
            
            # Interpolazione variabili (senza teams_link, viene aggiunto automaticamente)
            body = template.format(
                Nome=formazione_data.get('Nome', 'N/A'),
                Codice=formazione_data.get('Codice', 'N/A'),
                Data=data_formattata,
                Area=area_str
            )
            
            # Converti newline in <br> per HTML
            body_html = body.replace('\n', '<br>')
            
            logger.debug(f"Calendar body formattato | Formazione: {formazione_data.get('Nome', 'unknown')}")
            return body_html
            
        except KeyError as e:
            logger.error(f"Template variable mancante | Error: {e}")
            raise EmailFormatterError(f"Missing variable in template: {e}")
        except Exception as e:
            logger.error(f"Body formatting error: {e}")
            raise EmailFormatterError(f"Failed to format body: {e}")
    
    def format_subject(self, formazione_data: Dict) -> str:
        """
        Genera il subject dell'evento calendario.
        
        Args:
            formazione_data: Dati formazione (usa campo 'Nome' di Notion)
            
        Returns:
            Subject formattato
        """
        try:
            if 'calendar_event' not in self.templates:
                # Fallback se manca il template
                return formazione_data.get('Nome', 'Formazione')
            
            template = self.templates['calendar_event']['subject']
            subject = template.format(Nome=formazione_data.get('Nome', 'N/A'))
            
            # Rimuovi whitespace extra
            return subject.strip()
            
        except Exception as e:
            logger.warning(f"Subject formatting error: {e}, using Nome field")
            return formazione_data.get('Nome', 'Formazione')
