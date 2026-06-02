"""
Script di test veloce per Microsoft Service.

Verifica che:
1. La configurazione sia valida
2. I moduli si importino correttamente
3. Il servizio si inizializzi senza errori
"""

import sys
import os
import pytest

# Aggiungi root al path (tests/unit -> tests -> root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import Config
from app.services.microsoft import MicrosoftService


def test_config():
    """Testa la configurazione."""
    validation = Config.validate_config()
    
    # Assert invece di print e return bool
    assert validation['telegram'], "Configurazione Telegram mancante"
    assert validation['notion'], "Configurazione Notion mancante"
    
    if not validation['microsoft_graph']:
        pytest.skip("Microsoft Graph non configurato completamente in .env")


def test_service_initialization():
    """Testa l'inizializzazione del servizio."""
    try:
        service = MicrosoftService()
        info = service.get_service_info()
        
        assert info['user_email'], "Email utente mancante"
        assert info['tenant_id'], "Tenant ID mancante"
        
    except Exception as e:
        pytest.fail(f"Inizializzazione MicrosoftService fallita: {e}")


def test_template_loading():
    """Testa il caricamento dei template."""
    try:
        service = MicrosoftService()
        
        # Test formatting con dati sample (USA NOMI CAMPI NOTION ORIGINALI)
        sample_data = {
            'Nome': 'Test Formazione',
            'Codice': 'TEST-2024-01',
            'Data/Ora': '2024-10-15T10:00:00Z',
            'Area': ['IT']
        }
        
        subject = service.email_formatter.format_subject(sample_data)
        assert "Test Formazione" in subject
        
        body = service.email_formatter.format_calendar_body(sample_data)
        assert len(body) > 0
        
    except Exception as e:
        pytest.fail(f"Test template Microsoft fallito: {e}")
