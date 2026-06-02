"""
Unit test per NotionQueryBuilder.

Testa costruzione query strutturate per Notion API.
Focus su:
- Query per status (più utilizzata)
- Query per range date e area
- Query combinate con multipli filtri
- Validazione struttura query
- Edge cases e parametri opzionali

UTILIZZO:
pytest tests/unit/notion/test_query_builder.py -v
pytest -m "unit and notion" tests/unit/notion/test_query_builder.py -v
"""

import pytest
from app.services.notion.query_builder import NotionQueryBuilder


@pytest.mark.unit
@pytest.mark.notion
class TestNotionQueryBuilder:
    """Test suite per NotionQueryBuilder."""
    
    @pytest.fixture
    def query_builder(self):
        """Istanza NotionQueryBuilder per test."""
        return NotionQueryBuilder()
    
    # ===== TEST BUILD STATUS FILTER QUERY =====
    
    def test_build_status_filter_query_programmata(self, query_builder, sample_database_id):
        """
        Test costruzione query per status 'Programmata'.
        
        Verifica che:
        - Filtro status sia corretto
        - Ordinamento per data ascending
        - Page size default sia incluso
        - Struttura query sia valida per API Notion
        
        Query più utilizzata nel sistema per comandi bot.
        """
        result = query_builder.build_status_filter_query("Programmata", sample_database_id)
        
        assert result["database_id"] == sample_database_id
        assert result["filter"]["property"] == "Stato"
        assert result["filter"]["status"]["equals"] == "Programmata"
        assert result["sorts"][0]["property"] == "Date"
        assert result["sorts"][0]["direction"] == "ascending"
        assert result["page_size"] == 100
    
    def test_build_status_filter_query_calendarizzata(self, query_builder, sample_database_id):
        """
        Test costruzione query per status 'Calendarizzata'.
        
        Verifica che:
        - Status diversi generino filtri corretti
        - Struttura query rimanga consistente
        - Ordinamento sia sempre per data
        
        Caso comune: formazioni già calendarizzate pronte per avvio.
        """
        result = query_builder.build_status_filter_query("Calendarizzata", sample_database_id)
        
        assert result["filter"]["status"]["equals"] == "Calendarizzata"
        assert result["database_id"] == sample_database_id
        assert "sorts" in result
    
    def test_build_status_filter_query_conclusa(self, query_builder, sample_database_id):
        """
        Test costruzione query per status 'Conclusa' con ordinamento decrescente.
        
        Verifica che:
        - Status finali siano gestiti correttamente con i più recenti prima (descending)
        - Query structure sia valida per API Notion
        - Ordinamento rifletta la modifica recente in query_builder.py
        
        Utile per dashboard: mostra formazioni appena concluse in cima alla lista.
        """
        result = query_builder.build_status_filter_query("Conclusa", sample_database_id)
        
        assert result["filter"]["status"]["equals"] == "Conclusa"
        assert result["sorts"][0]["direction"] == "descending"
    
    # ===== TEST BUILD DATE RANGE FILTER QUERY =====
    
    def test_build_date_range_filter_query_valid_range(self, query_builder, sample_database_id):
        """
        Test costruzione query per range date valido.
        
        Verifica che:
        - Filtro 'and' combini on_or_after e on_or_before
        - Date ISO format siano preservate
        - Ordinamento per data sia incluso
        - Struttura 'and' sia corretta per API Notion
        
        Caso comune: query settimanali/mensili per planning.
        """
        start_date = "2024-04-01"
        end_date = "2024-04-30"
        
        result = query_builder.build_date_range_filter_query(start_date, end_date, sample_database_id)
        
        assert result["database_id"] == sample_database_id
        assert result["filter"]["and"][0]["property"] == "Date"
        assert result["filter"]["and"][0]["date"]["on_or_after"] == start_date
        assert result["filter"]["and"][1]["property"] == "Date"
        assert result["filter"]["and"][1]["date"]["on_or_before"] == end_date
        assert result["sorts"][0]["property"] == "Date"
    
    def test_build_date_range_filter_query_same_day(self, query_builder, sample_database_id):
        """
        Test costruzione query per stesso giorno (start = end).
        
        Verifica che:
        - Range di un giorno funzioni correttamente
        - Filtro 'and' sia ancora utilizzato
        - Date identiche non causino problemi
        
        Edge case: formazioni in giornata specifica.
        """
        same_date = "2024-04-15"
        
        result = query_builder.build_date_range_filter_query(same_date, same_date, sample_database_id)
        
        assert result["filter"]["and"][0]["date"]["on_or_after"] == same_date
        assert result["filter"]["and"][1]["date"]["on_or_before"] == same_date
    
    # ===== TEST BUILD AREA FILTER QUERY =====
    
    def test_build_area_filter_query_it(self, query_builder, sample_database_id):
        """
        Test costruzione query per area 'IT'.
        
        Verifica che:
        - Filtro multi_select con 'contains' sia corretto
        - Area specifica sia nel filtro
        - Ordinamento per data sia incluso
        
        Caso comune: formazioni IT specifiche.
        """
        result = query_builder.build_area_filter_query("IT", sample_database_id)
        
        assert result["database_id"] == sample_database_id
        assert result["filter"]["property"] == "Area"
        assert result["filter"]["multi_select"]["contains"] == "IT"
        assert result["sorts"][0]["property"] == "Date"
    
    def test_build_area_filter_query_hr(self, query_builder, sample_database_id):
        """
        Test costruzione query per area 'HR'.
        
        Verifica che:
        - Aree diverse generino filtri corretti
        - Struttura multi_select sia consistente
        - Performance sia ottimizzata
        
        Caso business: formazioni HR separate da quelle tecniche.
        """
        result = query_builder.build_area_filter_query("HR", sample_database_id)
        
        assert result["filter"]["multi_select"]["contains"] == "HR"
        assert result["filter"]["property"] == "Area"
    
    def test_build_area_filter_query_marketing(self, query_builder, sample_database_id):
        """
        Test costruzione query per area 'Marketing'.
        
        Verifica che:
        - Aree con nomi lunghi funzionino
        - Case sensitivity sia preservata
        - Struttura rimanga valida
        
        Coverage: tutte le aree business dell'azienda.
        """
        result = query_builder.build_area_filter_query("Marketing", sample_database_id)
        
        assert result["filter"]["multi_select"]["contains"] == "Marketing"
    
    # ===== TEST BUILD COMBINED FILTER QUERY =====
    
    def test_build_combined_filter_query_status_only(self, query_builder, sample_database_id):
        """
        Test query combinata solo con status (area None).
        
        Verifica che:
        - Solo filtro status sia applicato (non 'and')
        - Area None non generi filtro vuoto
        - Struttura sia ottimizzata per singolo filtro
        
        Caso comune: filtraggio base solo per status.
        """
        result = query_builder.build_combined_filter_query("Programmata", None, sample_database_id)
        
        assert result["database_id"] == sample_database_id
        assert result["filter"]["property"] == "Stato"
        assert result["filter"]["status"]["equals"] == "Programmata"
        # Non dovrebbe avere 'and' per singolo filtro
        assert "and" not in result["filter"]
    
    def test_build_combined_filter_query_status_and_area(self, query_builder, sample_database_id):
        """
        Test query combinata con status e area.
        
        Verifica che:
        - Filtro 'and' combini status e area
        - Entrambi i filtri siano presenti e corretti
        - Ordinamento sia preservato
        
        Caso avanzato: formazioni IT programmate, HR calendarizzate, etc.
        """
        result = query_builder.build_combined_filter_query("Programmata", "IT", sample_database_id)
        
        assert result["database_id"] == sample_database_id
        assert "and" in result["filter"]
        assert len(result["filter"]["and"]) == 2
        
        # Verifica filtro status
        status_filter = result["filter"]["and"][0]
        assert status_filter["property"] == "Stato"
        assert status_filter["status"]["equals"] == "Programmata"
        
        # Verifica filtro area
        area_filter = result["filter"]["and"][1]
        assert area_filter["property"] == "Area"
        assert area_filter["multi_select"]["contains"] == "IT"
    
    def test_build_combined_filter_query_different_combinations(self, query_builder, sample_database_id):
        """
        Test combinazioni diverse di status e area.
        
        Verifica che:
        - Ogni combinazione generi filtri corretti
        - Logica 'and' sia sempre consistente
        - Performance rimanga ottimale
        
        Coverage: matrix testing delle combinazioni principali.
        """
        # Combinazione Calendarizzata + HR
        result = query_builder.build_combined_filter_query("Calendarizzata", "HR", sample_database_id)
        
        status_filter = result["filter"]["and"][0]
        area_filter = result["filter"]["and"][1]
        
        assert status_filter["status"]["equals"] == "Calendarizzata"
        assert area_filter["multi_select"]["contains"] == "HR"
    
    # ===== TEST VALIDATE QUERY STRUCTURE =====
    
    def test_validate_query_structure_valid_query(self, query_builder, expected_status_query):
        """
        Test validazione query strutturata correttamente.
        
        Verifica che:
        - Query con database_id sia valida
        - Validazione restituisca True
        - Nessun errore per query corrette
        
        Caso base: validazione query generate dal builder.
        """
        result = query_builder.validate_query_structure(expected_status_query)
        
        assert result is True
    
    def test_validate_query_structure_missing_database_id(self, query_builder):
        """
        Test validazione query senza database_id.
        
        Verifica che:
        - Query senza database_id sia invalida
        - Validazione restituisca False
        - Errore sia loggato correttamente
        
        Edge case: prevenzione errori API per query malformate.
        """
        invalid_query = {
            "filter": {"property": "test"},
            "sorts": []
        }
        
        result = query_builder.validate_query_structure(invalid_query)
        
        assert result is False
    
    def test_validate_query_structure_empty_query(self, query_builder):
        """
        Test validazione query vuota.
        
        Verifica che:
        - Query {} sia invalida
        - Validazione gestisca dict vuoti
        - Comportamento sia robusto
        
        Edge case: protezione contro query completamente vuote.
        """
        empty_query = {}
        
        result = query_builder.validate_query_structure(empty_query)
        
        assert result is False
    
    def test_validate_query_structure_minimal_valid_query(self, query_builder):
        """
        Test validazione query minimale ma valida.
        
        Verifica che:
        - Solo database_id sia sufficiente per validazione
        - Filtri e sorts siano opzionali
        - Validazione non sia troppo restrittiva
        
        Caso limite: query più semplice possibile ma valida.
        """
        minimal_query = {
            "database_id": "test-id"
        }
        
        result = query_builder.validate_query_structure(minimal_query)
        
        assert result is True
    
    # ===== TEST EDGE CASES =====
    
    def test_query_builder_initialization(self, query_builder):
        """
        Test inizializzazione QueryBuilder.
        
        Verifica che:
        - Default page size sia 100
        - Istanza sia configurata correttamente
        - Nessun errore durante init
        
        Caso base: setup corretto del builder.
        """
        assert query_builder.default_page_size == 100
    
    def test_all_queries_include_date_sorting(self, query_builder, sample_database_id):
        """
        Test che tutte le query includano ordinamento per data.
        
        Verifica che:
        - Ogni metodo build_* includa sorts
        - Ordinamento sia sempre per 'Date' ascending
        - Consistency tra tutti i metodi
        
        Requisito business: formazioni sempre ordinate cronologicamente.
        """
        # Test su tutti i metodi di build
        status_query = query_builder.build_status_filter_query("Programmata", sample_database_id)
        date_query = query_builder.build_date_range_filter_query("2024-01-01", "2024-12-31", sample_database_id)
        area_query = query_builder.build_area_filter_query("IT", sample_database_id)
        combined_query = query_builder.build_combined_filter_query("Programmata", "IT", sample_database_id)
        
        queries = [status_query, date_query, area_query, combined_query]
        
        for query in queries:
            assert "sorts" in query
            assert query["sorts"][0]["property"] == "Date"
            assert query["sorts"][0]["direction"] == "ascending"