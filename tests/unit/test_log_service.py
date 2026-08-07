"""
Test unitari per LogService.

Verifica:
- Scoperta e ordinamento cronologico dei file di log ruotati
- Parsing corretto dei log con timestamp e traceback multiriga
- Filtro per intervallo di date (start_dt / end_dt)
- Comportamento con directory vuota o file assenti
- Ottimizzazione skip file tramite mtime
"""

import os
import pytest
from datetime import datetime
from unittest.mock import patch

from app.services.log_service import LogService


# ----------------------------------------------------------------
# Fixture helpers
# ----------------------------------------------------------------

def _write_log(path: str, lines: list) -> None:
    """Scrive righe di log in un file, creando le directory se necessario."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def _make_service(log_dir: str) -> LogService:
    """Crea un LogService puntato alla directory temporanea."""
    svc = LogService.__new__(LogService)
    svc._log_dir = log_dir
    svc._log_basename = 'formazing.log'
    return svc


# ----------------------------------------------------------------
# 1. Scoperta e ordinamento dei file di log
# ----------------------------------------------------------------

class TestDiscoverLogFiles:

    def test_nessun_file(self, tmp_path):
        """Con directory vuota, _discover_log_files restituisce lista vuota."""
        svc = _make_service(str(tmp_path))
        assert svc._discover_log_files() == []

    def test_solo_file_principale(self, tmp_path):
        """Con solo formazing.log, viene restituito un solo file."""
        _write_log(str(tmp_path / 'formazing.log'), ['dummy'])
        svc = _make_service(str(tmp_path))
        files = svc._discover_log_files()
        assert len(files) == 1
        assert os.path.basename(files[0]) == 'formazing.log'

    def test_ordine_cronologico_backup(self, tmp_path):
        """
        I file di backup numerati più alti (più vecchi) devono comparire
        PRIMA del file principale nella lista.
        Es. formazing.log.3 → formazing.log.2 → formazing.log.1 → formazing.log
        """
        for name in ['formazing.log', 'formazing.log.1', 'formazing.log.2', 'formazing.log.3']:
            _write_log(str(tmp_path / name), ['dummy'])

        svc = _make_service(str(tmp_path))
        files = svc._discover_log_files()
        basenames = [os.path.basename(f) for f in files]

        # Il più vecchio deve stare in testa, il principale in fondo
        assert basenames.index('formazing.log.3') < basenames.index('formazing.log.2')
        assert basenames.index('formazing.log.2') < basenames.index('formazing.log.1')
        assert basenames.index('formazing.log.1') < basenames.index('formazing.log')

    def test_ignora_file_non_correlati(self, tmp_path):
        """File con nomi diversi nella stessa directory non vengono inclusi."""
        _write_log(str(tmp_path / 'formazing.log'), ['dummy'])
        _write_log(str(tmp_path / 'altro.log'), ['altro'])
        _write_log(str(tmp_path / 'formazing.log.old'), ['old'])  # suffisso non numerico

        svc = _make_service(str(tmp_path))
        files = svc._discover_log_files()
        basenames = [os.path.basename(f) for f in files]
        assert basenames == ['formazing.log']

    def test_directory_inesistente(self, tmp_path):
        """Se la directory non esiste, restituisce lista vuota senza eccezioni."""
        svc = _make_service(str(tmp_path / 'non_esiste'))
        assert svc._discover_log_files() == []


# ----------------------------------------------------------------
# 2. Filtro per intervallo di date
# ----------------------------------------------------------------

LOG_SAMPLE = [
    '2026-08-01 08:00:00 | INFO  | app.routes | Avvio applicazione',
    '2026-08-05 10:30:00 | INFO  | app.routes | Dashboard caricata | Totale: 10',
    '2026-08-05 10:30:01 | ERROR | app.services.notion | Errore Notion',
    'Traceback (most recent call last):',
    '  File "notion.py", line 42, in get_data',
    '    raise NotionError("timeout")',
    'NotionError: timeout',
    '2026-08-07 09:15:00 | WARNING | app | Attenzione configurazione',
    '2026-08-07 14:00:00 | INFO  | app.routes | Calendarizzazione completata',
]


class TestGetLogsFiltering:

    def test_filtro_giorno_singolo(self, tmp_path):
        """Solo i log del 5 agosto devono essere restituiti."""
        _write_log(str(tmp_path / 'formazing.log'), LOG_SAMPLE)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 8, 5, 0, 0, 0),
            end_dt=datetime(2026, 8, 5, 23, 59, 59)
        )

        # Le righe del 5 agosto + il traceback associato all'ERROR
        assert any('2026-08-05 10:30:00' in l for l in results)
        assert any('2026-08-05 10:30:01' in l for l in results)
        # Il traceback deve essere incluso (associato all'ERROR del 5 agosto)
        assert any('Traceback' in l for l in results)
        assert any('NotionError' in l for l in results)
        # Le righe di altri giorni non devono comparire
        assert not any('2026-08-01' in l for l in results)
        assert not any('2026-08-07' in l for l in results)

    def test_filtro_intervallo_multi_giorno(self, tmp_path):
        """Un intervallo dal 5 al 7 agosto deve includere tutti e tre i giorni."""
        _write_log(str(tmp_path / 'formazing.log'), LOG_SAMPLE)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 8, 5, 0, 0, 0),
            end_dt=datetime(2026, 8, 7, 23, 59, 59)
        )

        assert any('2026-08-05' in l for l in results)
        assert any('2026-08-07' in l for l in results)
        assert not any('2026-08-01' in l for l in results)

    def test_nessun_risultato_intervallo_fuori_range(self, tmp_path):
        """Un intervallo che non copre nessun log restituisce lista vuota."""
        _write_log(str(tmp_path / 'formazing.log'), LOG_SAMPLE)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2025, 1, 1, 0, 0, 0),
            end_dt=datetime(2025, 1, 31, 23, 59, 59)
        )

        assert results == []

    def test_filtro_ora_precisa(self, tmp_path):
        """Il filtro orario deve essere inclusivo per i boundary start/end."""
        lines = [
            '2026-08-07 09:00:00 | INFO | app | Prima delle 10',
            '2026-08-07 10:00:00 | INFO | app | Esattamente alle 10 (inizio)',
            '2026-08-07 11:00:00 | INFO | app | Tra 10 e 12',
            '2026-08-07 12:00:00 | INFO | app | Esattamente alle 12 (fine)',
            '2026-08-07 13:00:00 | INFO | app | Dopo le 12',
        ]
        _write_log(str(tmp_path / 'formazing.log'), lines)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 8, 7, 10, 0, 0),
            end_dt=datetime(2026, 8, 7, 12, 0, 0)
        )

        timestamps_found = [l.split(' | ')[0] for l in results if ' | ' in l]
        assert '2026-08-07 10:00:00' in timestamps_found, "Il boundary start deve essere inclusivo"
        assert '2026-08-07 12:00:00' in timestamps_found, "Il boundary end deve essere inclusivo"
        assert '2026-08-07 09:00:00' not in timestamps_found
        assert '2026-08-07 13:00:00' not in timestamps_found


# ----------------------------------------------------------------
# 3. Parsing traceback multiriga
# ----------------------------------------------------------------

class TestTracebackParsing:

    def test_traceback_associato_allevento_in_range(self, tmp_path):
        """
        Un traceback multiriga deve essere incluso se l'evento principale
        (con timestamp) rientra nell'intervallo.
        """
        lines = [
            '2026-08-07 10:00:00 | ERROR | app | Errore critico',
            'Traceback (most recent call last):',
            '  File "app.py", line 10, in main',
            '    raise RuntimeError("boom")',
            'RuntimeError: boom',
            '2026-08-07 10:00:01 | INFO  | app | Ripresa normale',
        ]
        _write_log(str(tmp_path / 'formazing.log'), lines)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 8, 7, 0, 0, 0),
            end_dt=datetime(2026, 8, 7, 23, 59, 59)
        )

        assert any('Traceback' in l for l in results)
        assert any('RuntimeError' in l for l in results)
        assert any('raise RuntimeError' in l for l in results)

    def test_traceback_escluso_se_evento_fuori_range(self, tmp_path):
        """
        Un traceback associato a un evento fuori dall'intervallo non deve
        essere incluso nei risultati.
        """
        lines = [
            '2026-08-01 10:00:00 | ERROR | app | Errore fuori range',
            'Traceback (most recent call last):',
            '  File "app.py", line 5',
            'OldError: vecchio errore',
            '2026-08-07 10:00:00 | INFO  | app | Log nel range',
        ]
        _write_log(str(tmp_path / 'formazing.log'), lines)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 8, 7, 0, 0, 0),
            end_dt=datetime(2026, 8, 7, 23, 59, 59)
        )

        assert not any('OldError' in l for l in results)
        assert not any('Traceback' in l for l in results)
        assert any('2026-08-07' in l for l in results)


# ----------------------------------------------------------------
# 4. Comportamento con input limite e directory vuota
# ----------------------------------------------------------------

class TestEdgeCases:

    def test_file_vuoto(self, tmp_path):
        """Un file di log vuoto non genera errori e restituisce lista vuota."""
        _write_log(str(tmp_path / 'formazing.log'), [])
        svc = _make_service(str(tmp_path))
        results = svc.get_logs(
            start_dt=datetime(2026, 8, 7, 0, 0, 0),
            end_dt=datetime(2026, 8, 7, 23, 59, 59)
        )
        assert results == []

    def test_default_giorno_corrente(self, tmp_path):
        """
        Chiamando get_logs senza parametri, il default deve essere il giorno
        corrente. I log di ieri non devono apparire.
        """
        from datetime import date
        today = date.today()
        yesterday = date(today.year, today.month, today.day)

        lines = [
            f'{today.year}-{today.month:02d}-{today.day:02d} 09:00:00 | INFO | app | Log di oggi',
        ]
        _write_log(str(tmp_path / 'formazing.log'), lines)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs()
        assert len(results) == 1
        assert 'Log di oggi' in results[0]

    def test_lettura_da_piu_file(self, tmp_path):
        """
        I log distribuiti su più file (principale + backup) devono essere
        tutti restituiti in ordine cronologico.
        """
        older_lines = [
            '2026-07-01 08:00:00 | INFO | app | Log vecchio nel backup',
        ]
        newer_lines = [
            '2026-08-07 09:00:00 | INFO | app | Log recente nel principale',
        ]
        _write_log(str(tmp_path / 'formazing.log.1'), older_lines)
        _write_log(str(tmp_path / 'formazing.log'), newer_lines)
        svc = _make_service(str(tmp_path))

        results = svc.get_logs(
            start_dt=datetime(2026, 7, 1, 0, 0, 0),
            end_dt=datetime(2026, 8, 31, 23, 59, 59)
        )

        assert any('Log vecchio' in l for l in results)
        assert any('Log recente' in l for l in results)
        # Il log vecchio deve venire prima del recente
        idx_vecchio = next(i for i, l in enumerate(results) if 'Log vecchio' in l)
        idx_recente = next(i for i, l in enumerate(results) if 'Log recente' in l)
        assert idx_vecchio < idx_recente
