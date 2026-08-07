"""
LogService - Lettura e filtraggio dei log applicativi per intervallo di date.

Responsabilità:
- Scoperta automatica dei file di log ruotati (formazing.log, formazing.log.1, ...)
- Parsing delle righe di log con timestamp e gestione dei traceback multiriga
- Filtro efficiente per intervallo di date senza limiti arbitrari di righe
"""

import os
import re
import logging
from datetime import datetime, date
from typing import List, Optional

logger = logging.getLogger(__name__)

# Pattern per riconoscere l'inizio di una nuova riga di log con timestamp.
# Formato atteso: "2026-08-07 14:22:33 | LEVEL | module | message"
_LOG_LINE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')


class LogService:
    """
    Servizio per leggere e filtrare i file di log dell'applicazione Formazing.

    Gestisce la scoperta e lettura dei file di log ruotati (es. formazing.log,
    formazing.log.1, formazing.log.2, ...) e filtra le righe in base a un
    intervallo di date specificato dall'utente.

    Design decisions:
    - I file vengono scansionati dal più vecchio al più recente per garantire
      l'ordine cronologico corretto dell'output.
    - I file il cui mtime è antecedente a start_dt vengono saltati per efficienza.
    - I traceback multiriga (righe senza timestamp) vengono "appesi" all'evento
      precedente per mantenere il contesto degli errori completo e leggibile.
    - Non viene imposto alcun limite al numero di righe restituite: l'utente
      riceve TUTTI i log che rientrano nell'intervallo richiesto.
    """

    def __init__(self, log_dir: str = 'logs', log_basename: str = 'formazing.log'):
        """
        Inizializza il LogService.

        Args:
            log_dir: Directory contenente i file di log (relativa alla root del progetto).
            log_basename: Nome base del file di log principale.
        """
        # Calcola il path assoluto della directory dei log a partire da questo file
        self._log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            log_dir
        )
        self._log_basename = log_basename

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_logs(
        self,
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None
    ) -> List[str]:
        """
        Restituisce tutte le righe di log (inclusi traceback) nell'intervallo
        temporale specificato.

        Se start_dt è None, usa l'inizio del giorno corrente.
        Se end_dt è None, usa la fine del giorno corrente (23:59:59).

        Args:
            start_dt: Datetime di inizio intervallo (inclusivo).
            end_dt:   Datetime di fine intervallo (inclusivo).

        Returns:
            Lista di stringhe, una per ogni riga di log (incluse righe di traceback
            associate a eventi che rientrano nell'intervallo). Ordinate dalla più
            vecchia alla più recente.
        """
        # Valori di default: giorno corrente
        if start_dt is None:
            today = date.today()
            start_dt = datetime(today.year, today.month, today.day, 0, 0, 0)
        if end_dt is None:
            today = date.today()
            end_dt = datetime(today.year, today.month, today.day, 23, 59, 59)

        log_files = self._discover_log_files()
        if not log_files:
            logger.warning(f"Nessun file di log trovato in: {self._log_dir}")
            return []

        results: List[str] = []
        for filepath in log_files:
            results.extend(self._read_file_in_range(filepath, start_dt, end_dt))

        logger.debug(
            f"LogService: trovate {len(results)} righe nell'intervallo "
            f"{start_dt.isoformat()} - {end_dt.isoformat()}"
        )
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_log_files(self) -> List[str]:
        """
        Scopre tutti i file di log nella directory, ordinati dal più vecchio
        al più recente (i backup numerati più alti sono i più vecchi).

        Returns:
            Lista di path assoluti ai file di log, ordinata cronologicamente
            (il più vecchio prima).
        """
        if not os.path.isdir(self._log_dir):
            logger.error(f"Directory dei log non trovata: {self._log_dir}")
            return []

        files = []
        for filename in os.listdir(self._log_dir):
            # Accetta: formazing.log, formazing.log.1, formazing.log.2, ...
            if filename == self._log_basename or (
                filename.startswith(self._log_basename + '.') and
                filename[len(self._log_basename) + 1:].isdigit()
            ):
                files.append(os.path.join(self._log_dir, filename))

        # Ordina: i file numerati più grandi (es. .5) sono i più vecchi;
        # il file senza suffisso numerico è il più recente.
        def sort_key(path: str) -> int:
            """Assegna un numero d'ordine: più alto = più vecchio = prima nella lista."""
            basename = os.path.basename(path)
            suffix = basename[len(self._log_basename):]
            if suffix == '':
                return 0  # file principale = più recente, messo alla fine
            try:
                return -int(suffix.lstrip('.'))  # es. .3 → -3 (più alto = più vecchio)
            except ValueError:
                return 1

        # Ordina ascendente: i più vecchi (numeri negativi grandi) vengono prima
        files.sort(key=sort_key)
        logger.debug(f"LogService: file di log individuati: {[os.path.basename(f) for f in files]}")
        return files

    def _read_file_in_range(
        self,
        filepath: str,
        start_dt: datetime,
        end_dt: datetime
    ) -> List[str]:
        """
        Legge un singolo file di log e restituisce le righe che rientrano
        nell'intervallo specificato, incluse le righe di traceback associate.

        Ottimizzazione: se la data di ultima modifica del file (mtime) è
        antecedente a start_dt, il file viene saltato completamente poiché
        non può contenere log più recenti di quella data.

        Args:
            filepath: Path assoluto al file da leggere.
            start_dt: Datetime di inizio (inclusivo).
            end_dt:   Datetime di fine (inclusivo).

        Returns:
            Lista di righe di log nell'intervallo, in ordine cronologico.
        """
        # Ottimizzazione: skip del file se modificato prima dell'intervallo richiesto
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_mtime < start_dt:
                logger.debug(
                    f"LogService: skip '{os.path.basename(filepath)}' "
                    f"(mtime {file_mtime.date()} < start {start_dt.date()})"
                )
                return []
        except OSError as e:
            logger.warning(f"LogService: impossibile leggere mtime di '{filepath}': {e}")

        results: List[str] = []
        # Buffer che accumula le righe dell'evento corrente (riga principale + traceback)
        current_event_lines: List[str] = []
        current_event_in_range: bool = False

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for raw_line in f:
                    line = raw_line.rstrip('\r\n')
                    match = _LOG_LINE_RE.match(line)

                    if match:
                        # Nuova riga di log con timestamp: scarica l'evento precedente
                        if current_event_in_range and current_event_lines:
                            results.extend(current_event_lines)

                        # Parsa il timestamp della nuova riga
                        ts_str = match.group(1)
                        try:
                            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            current_event_lines = [line]
                            current_event_in_range = False
                            continue

                        # Controlla se la riga rientra nell'intervallo richiesto
                        current_event_in_range = (start_dt <= ts <= end_dt)
                        current_event_lines = [line]

                        # Se il timestamp supera end_dt, i successivi saranno ancora più
                        # recenti: possiamo interrompere la lettura del file.
                        if ts > end_dt:
                            current_event_in_range = False
                            break
                    else:
                        # Riga senza timestamp: è continuazione (traceback, stacktrace)
                        # dell'evento corrente. La aggiungiamo al buffer senza modificare
                        # current_event_in_range.
                        current_event_lines.append(line)

                # Scarica l'ultimo evento rimasto nel buffer
                if current_event_in_range and current_event_lines:
                    results.extend(current_event_lines)

        except OSError as e:
            logger.error(f"LogService: errore lettura file '{filepath}': {e}")

        return results
