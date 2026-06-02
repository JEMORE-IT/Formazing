"""
Test unitari per TelegramFormatter - Formattazione messaggi

Questo modulo testa la logica pura di formattazione messaggi:
- Sostituzione placeholder nei template
- Parsing e formattazione date multi-formato  
- Gestione errori e fallback
- Template selection logic

Focus: SOLO logica di formattazione, NO invii reali
Pattern: Usa fixture da conftest.py per template e dati controllati
"""

import pytest
from datetime import datetime
from unittest.mock import patch
import yaml

from app.services.bot.telegram_formatters import TelegramFormatter


@pytest.mark.unit
class TestTelegramFormatter:
    """Test suite per TelegramFormatter - Focus su logica pura"""
    
    @pytest.fixture
    def real_templates(self):
        """
        Carica template reali dal file YAML di configurazione.
        
        Questo approccio garantisce che i test unitari utilizzino
        esattamente gli stessi template del sistema in produzione,
        aumentando l'accuratezza e riducendo la duplicazione di codice.
        
        Returns:
            dict: Template strutturati caricati da config/message_templates.yaml
        """
        with open('config/message_templates.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @pytest.fixture
    def formatter(self, real_templates):
        """
        TelegramFormatter configurato con template di produzione.
        
        Combina la classe TelegramFormatter con i template reali,
        creando un'istanza pronta per il testing che riflette
        il comportamento effettivo del sistema.
        
        Args:
            real_templates: Fixture con i template YAML caricati
            
        Returns:
            TelegramFormatter: Istanza pronta per il test
        """
        return TelegramFormatter(real_templates)

    # ================================
    # TEST format_training_message
    # ================================

    def test_format_training_message_main_group_complete_data(self, formatter, sample_training_data):
        """
        Test formattazione messaggio training per gruppo principale.
        
        Verifica che:
        - Tutti i campi dei dati vengano inseriti correttamente nel template
        - Il template main_group venga selezionato
        - Non rimangano placeholder non risolti nel messaggio finale
        - La struttura HTML sia corretta per Telegram
        
        Utilizza sample_training_data da conftest.py con dati dinamici realistici.
        """
        result = formatter.format_training_message(sample_training_data, 'main_group')
        
        # Verifiche presenza campi da sample_training_data (conftest.py)
        assert sample_training_data['Nome'] in result
        assert sample_training_data['Area'] in result
        assert sample_training_data['Data/Ora'] in result
        assert sample_training_data['Codice'] in result
        assert sample_training_data['Link Teams'] in result
        
        # Verifiche template structure reale (ora con 🎉 invece di 🚀)
        assert '🎉' in result 
        assert '<a href=' in result
        assert 'Formazione per i soci' in result
        
        # Verifica non ci siano placeholder non risolti
        assert '{' not in result
        assert '}' not in result
    
    def test_format_training_message_area_group_complete_data(self, formatter, sample_training_data):
        """
        Test formattazione messaggio training per gruppi area specifici.
        
        Verifica che:
        - Venga utilizzato il template area_group (diverso dal main_group)
        - Il messaggio sia personalizzato per l'area specifica
        - Mantenga la struttura HTML appropriata per Telegram
        
        Importante: Questo test dimostra la logica di template selection.
        """
        result = formatter.format_training_message(sample_training_data, 'area_group')
        
        # Verifiche presenza campi da fixture conftest.py
        assert sample_training_data['Nome'] in result
        assert sample_training_data['Data/Ora'] in result
        
        # Verifiche template specifico area_group (dal template reale usa 🚀)
        assert '🚀' in result
        assert 'Nuova formazione programmata!' in result
        assert 'Partecipa qui</a>' in result
    
    def test_format_training_message_missing_fields(self, formatter):
        """
        Test gestione robusta di dati incompleti con fallback automatici.
        
        Scenario: Dati formazione con campi mancanti (Data/Ora, Codice, Link Teams)
        
        Verifica che:
        - I campi presenti vengano inseriti correttamente
        - I campi mancanti vengano sostituiti con 'N/A'
        - Il template venga completato senza errori
        - Non rimangano placeholder irrisolti
        """
        minimal_training_data = {
            'Nome': 'Basic Course',
            'Area': 'HR'
        }
        
        result = formatter.format_training_message(minimal_training_data, 'main_group')
        
        # Campi presenti
        assert 'Basic Course' in result
        assert 'HR' in result
        
        # Campi mancanti → fallback N/A
        assert 'N/A' in result  # Deve apparire per campi mancanti
        
        # Template deve essere completato comunque
        assert result.startswith('🎉 <b>')
        assert '{' not in result  # No placeholder irrisolti
    
    def test_format_training_message_template_not_found(self, sample_training_data):
        """
        Test gestione graceful di template di formattazione mancanti.
        
        Scenario: TelegramFormatter inizializzato con dizionario vuoto
        Verifica che il sistema non crashi ma restituisca un messaggio
        di errore leggibile invece del template formattato.
        
        Importante per robustezza: Se configurazione è incompleta,
        l'utente deve vedere un errore chiaro, non un crash.
        """
        # Formatter con template vuoti
        empty_formatter = TelegramFormatter({})
        
        result = empty_formatter.format_training_message(sample_training_data, 'main_group')
        
        # Deve restituire messaggio di errore
        assert 'Template main_group non trovato' in result
        assert sample_training_data['Nome'] not in result  # Non deve fare formattazione
    
    def test_format_training_message_template_format_error(self, formatter):
        """
        Test gestione errori di formattazione per placeholder invalidi.
        
        Scenario: Template contiene placeholder che non esistono nei dati
        (es. {invalid_placeholder} quando dati contengono solo {nome})
        
        Verifica che:
        - Il sistema non crashi con KeyError
        - Restituisca messaggio di errore descrittivo
        - Includa il nome del corso nel messaggio per debug
        
        Questo protegge da errori di configurazione template.
        """
        # Template con placeholder invalido
        broken_templates = {
            'training_notification': {
                'telegram': {
                    'main_group': 'Test {invalid_placeholder} {nome}'
                }
            }
        }
        broken_formatter = TelegramFormatter(broken_templates)
        
        training_data = {'Nome': 'Test Course'}  # Manca invalid_placeholder
        
        result = broken_formatter.format_training_message(training_data, 'main_group')
        
        # Deve restituire messaggio di errore fallback
        assert 'Errore nella formattazione del messaggio' in result
        assert 'Test Course' in result  # Nome deve essere nel messaggio di errore
    
    # ================================
    # TEST format_feedback_message
    # ================================
    
    def test_format_feedback_message_complete_data(self, formatter, sample_training_data):
        """
        Test formattazione messaggio richiesta feedback con dati completi.
        
        Verifica che:
        - Tutti i campi training (Nome, Codice) appaiano nel messaggio
        - Il link feedback sia correttamente integrato come link cliccabile
        - Il template reale produca la struttura HTML attesa per Telegram
        - Non rimangano placeholder irrisolti nel messaggio finale
        
        Utilizza dati realistici da conftest.py per test accurati.
        """
        feedback_link = 'https://forms.office.com/r/test-feedback-123'
        
        result = formatter.format_feedback_message(sample_training_data, feedback_link, 'IT')
        
        # Verifiche presenza campi da fixture conftest.py
        assert sample_training_data['Nome'] in result
        assert sample_training_data['Codice'] in result
        assert feedback_link in result
        
        # Verifiche template structure reale
        assert '⭐' in result and 'opinione vale oro!' in result  # Template reale
        assert '<a href=' in result
        assert 'Clicca qui per inviare il feedback</a>' in result  # Testo reale
        
        # No placeholder irrisolti
        assert '{' not in result
        assert '}' not in result
    
    def test_format_feedback_message_missing_fields(self, formatter):
        """
        Test robustezza formattazione feedback con dati incompleti.
        
        Scenario: Dati training con solo Nome e Area (manca Codice)
        
        Verifica che:
        - I campi presenti vengano inseriti correttamente
        - I campi mancanti vengano sostituiti con fallback 'N/A'
        - Il template feedback venga completato senza errori
        - Il link feedback rimanga sempre funzionante
        """
        minimal_training_data = {
            'Nome': 'Basic Course',
            'Area': 'HR'
        }
        feedback_link = 'https://forms.office.com/r/test'
        
        result = formatter.format_feedback_message(minimal_training_data, feedback_link, 'HR')
        
        # Campi presenti
        assert 'Basic Course' in result
        assert feedback_link in result
        
        # Campi mancanti → N/A (Codice è nel template, ma Area NO)
        assert 'N/A' in result
        
        # Template completato
        assert '{' not in result
    
    def test_format_feedback_message_template_not_found(self, sample_training_data):
        """
        Test gestione errore per template feedback mancante.
        
        Scenario: TelegramFormatter senza template feedback configurati
        
        Verifica che il sistema restituisca un messaggio di errore
        chiaro invece di crashare, permettendo diagnosi rapida
        di problemi di configurazione template.
        
        Importante per deployment: Se YAML è incompleto, l'errore
        deve essere immediatamente identificabile.
        """
        empty_formatter = TelegramFormatter({})
        
        result = empty_formatter.format_feedback_message(
            sample_training_data, 
            'https://test.com', 
            'IT'
        )
        
        # Messaggio di errore
        assert 'Template feedback non trovato' in result
    
    # ================================
    # TEST _format_date_time
    # ================================
    
    def test_format_date_time_iso_format(self, formatter):
        """
        Test conversione formato data ISO → formato italiano leggibile.
        
        Scenario: Data in formato ISO 8601 (standard API Notion)
        Input: "2025-09-28T14:30:00Z" 
        Output atteso: "28/09/2025 14:30"
        
        Questo test verifica la capacità di parsing delle date che
        arrivano dall'API Notion in formato ISO standard.
        """
        iso_date = "2025-09-28T14:30:00Z"
        
        result = formatter._format_date_time(iso_date)
        
        # Deve convertire in formato italiano
        assert result == "28/09/2025 14:30"
    
    def test_format_date_time_iso_format_with_timezone(self, formatter):
        """
        Test parsing date ISO con timezone esplicito.
        
        Scenario: Data con timezone "+02:00" (Europa/Roma)
        Input: "2025-09-28T14:30:00+02:00"
        
        Verifica che:
        - Il parsing gestisca correttamente il timezone
        - La data risultante sia nel formato italiano atteso
        - L'ora venga preservata o convertita appropriatamente
        
        Questo test copre date che arrivano da API esterne
        con timezone espliciti diversi da UTC.
        """
        iso_date = "2025-09-28T14:30:00+02:00"
        
        result = formatter._format_date_time(iso_date)
        
        # Deve gestire timezone correttamente
        assert "28/09/2025" in result
        assert ":" in result  # Deve contenere ora
    
    def test_format_date_time_custom_format(self, formatter):
        """
        Test data già in formato custom dd/mm/yyyy HH:MM.
        
        Scenario: Data già nel formato output desiderato
        Input: "28/09/2025 14:30"
        
        Verifica che:
        - Il formatter riconosca date già formattate
        - Non modifichi date già nel formato corretto
        - Eviti elaborazioni inutili per performance
        
        Importante per evitare doppia conversione
        quando i dati arrivano già formattati.
        """
        custom_date = "28/09/2025 14:30"
        
        result = formatter._format_date_time(custom_date)
        
        # Deve rimanere uguale (già nel formato corretto)
        assert result == "28/09/2025 14:30"
    
    def test_format_date_time_invalid_format(self, formatter):
        """
        Test gestione robusta di date in formato non riconosciuto.
        
        Scenario: Stringa che non è una data valida
        Input: "not-a-date"
        
        Verifica che:
        - Il sistema non crashi per input invalidi
        - Venga restituita la stringa originale come fallback
        - Il comportamento sia predicibile per debugging
        
        Fondamentale per stabilità del sistema quando
        riceve dati corrotti o malformati.
        """
        invalid_date = "not-a-date"
        
        result = formatter._format_date_time(invalid_date)
        
        # Deve restituire stringa originale come fallback
        assert result == "not-a-date"
    
    def test_format_date_time_na_value(self, formatter):
        """
        Test gestione valore speciale N/A.
        
        Scenario: Campo data con valore "N/A" (non disponibile)
        Input: 'N/A'
        
        Verifica che:
        - I valori N/A vengano preservati senza modifiche
        - Non ci siano tentativi di parsing su valori null
        - L'output sia user-friendly per campi mancanti
        
        Comune in database opera dove alcuni campi data
        possono essere non disponibili o non applicabili.
        """
        result = formatter._format_date_time('N/A')
        
        assert result == 'N/A'
    
    def test_format_date_time_none_value(self, formatter):
        """
        Test gestione sicura di valori None.
        
        Scenario: Campo data con valore Python None
        Input: None
        
        Verifica che:
        - I valori None vengano convertiti in stringa
        - Non si verifichino AttributeError su None
        - Il comportamento sia consistente con altri fallback
        
        Protegge contro NoneType errors quando
        i dati dal database contengono valori null.
        """
        result = formatter._format_date_time(None)
        
        assert result == 'None'
    
    @patch('app.services.bot.telegram_formatters.logger')
    def test_format_date_time_logs_warning_on_error(self, mock_logger, formatter):
        """
        Test logging automatico di errori di parsing date con mock verification.
        
        Scenario: Data in formato impossibile "2025-99-99T99:99:99Z"
        
        Verifica che:
        - Venga chiamato logger.warning esattamente una volta
        - Il messaggio di log contenga dettagli dell'errore
        - Venga restituito fallback sicuro (stringa originale)
        - Il sistema non crashi per date malformate
        
        Utilizza @patch per mock del logger e verifica delle chiamate.
        """
        bad_date = "2025-99-99T99:99:99Z"  # Data impossibile
        
        result = formatter._format_date_time(bad_date)
        
        # Deve loggare warning e restituire fallback
        mock_logger.warning.assert_called_once()
        assert "Errore parsing data" in mock_logger.warning.call_args[0][0]
        assert result == bad_date  # Fallback alla stringa originale
    
    # ================================
    # TEST Template Selection Logic
    # ================================
    
    def test_template_selection_main_group(self, formatter, sample_training_data):
        """
        Test selezione template corretto per main_group.
        
        Scenario: Messaggio per gruppo principale (main_group)
        Input: sample_training_data + 'main_group'
        
        Verifica che:
        - Venga selezionato il template specifico per main_group
        - Il messaggio abbia il tone generale per tutti i soci
        """
        result = formatter.format_training_message(sample_training_data, 'main_group')
        
        # Deve usare template main_group (dal template reale usa 🎉)
        assert '🎉' in result
        assert 'Formazione per i soci' in result
    
    def test_template_selection_area_group(self, formatter, sample_training_data):
        """
        Test selezione template corretto per area_group.
        
        Scenario: Messaggio per gruppo area-specifica
        Input: sample_training_data + 'area_group'
        
        Verifica che:
        - Venga utilizzato il template specializzato per area
        - Il contenuto sia personalizzato per il target gruppo
        """  
        result = formatter.format_training_message(sample_training_data, 'area_group')
        
        # Deve usare template area_group (dal template reale usa 🚀)
        assert '🚀' in result
        assert 'Nuova formazione programmata!' in result
    
    def test_template_selection_unknown_group(self, formatter, sample_training_data):
        """
        Test selezione template per gruppo sconosciuto con fallback.
        
        Scenario: Richiesta per gruppo non configurato
        Input: sample_training_data + 'unknown_group'
        
        Verifica che:
        - Il sistema non crashi per gruppi non riconosciuti
        - Venga applicato automaticamente il fallback (area_group)
        - Il messaggio risultante sia funzionale e leggibile
        """
        result = formatter.format_training_message(sample_training_data, 'unknown_group')
        
        # Deve usare template area_group come fallback
        assert '🚀' in result
        assert 'Nuova formazione programmata!' in result
    
    # ================================
    # TEST Integration con fixture reali
    # ================================
    
    def test_integration_with_conftest_fixtures(self, sample_training_data):
        """
        Test integrazione con il sistema di fixture centralizzato.
        
        Verifica che:
        - sample_training_data da conftest.py sia strutturato correttamente
        - Contenga tutti i campi richiesti dal sistema
        - Abbia data dinamica basata su 'oggi' (sempre valida)
        - Dimostri il corretto riutilizzo delle fixture condivise
        """
        # Usa fixture reale da conftest.py
        assert 'Nome' in sample_training_data
        assert 'Area' in sample_training_data
        assert 'Data/Ora' in sample_training_data
        
        # Test che fixture contenga data dinamica (oggi)
        today = datetime.now()
        expected_date = today.strftime('%d/%m/%Y')
        assert expected_date in sample_training_data['Data/Ora']
    
    def test_integration_formatter_with_alternative_data(self, formatter, alternative_training_data):
        """
        Test con dati alternativi da conftest.py (area HR).
        
        Scenario: Formazione area HR con fixture alternative_training_data
        
        Verifica che:
        - I dati alternativi vengano processati correttamente
        - Il template area_group sia selezionato appropriatamente
        - Il contenuto includa dettagli specifici per l'area HR
        """
        result = formatter.format_training_message(alternative_training_data, 'area_group')
        
        # Deve contenere elementi del template reale con dati HR
        assert alternative_training_data['Nome'] in result
        assert alternative_training_data['Area'] in result  # HR
        assert '🚀' in result
        assert 'Partecipa qui</a>' in result  # Marker specifico del template area_group
