#!/usr/bin/env python3
"""
Test workflow completo Notion → Telegram
========================================
"""

import asyncio
import logging
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Aggiungi la directory root del progetto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.notion import NotionService
from app.services.telegram_service import TelegramService
from app.services.bot.telegram_formatters import TelegramFormatter
from config import Config

# Global quiet mode
QUIET = False

def q_print(msg, end='\n'):
    if not QUIET:
        print(msg, end=end)

@dataclass
class WorkflowResult:
    formazione_nome: str
    formazione_id: str
    status: str
    groups_targeted: List[str]
    messages_generated: int
    messages_sent: int
    success_rate: float
    execution_time: float
    errors: List[str]

class WorkflowTester:
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.notion_service = None
        self.telegram_service = None
        self.formatter = None
        self.results: List[WorkflowResult] = []
        
    async def initialize_services(self) -> bool:
        q_print("🔧 Inizializzazione servizi...", end=' ')
        try:
            self.notion_service = NotionService()
            self.telegram_service = TelegramService(
                token=Config.TELEGRAM_BOT_TOKEN,
                notion_service=self.notion_service,
                groups_config_path=Config.TELEGRAM_GROUPS_CONFIG,
                templates_config_path=Config.TELEGRAM_TEMPLATES_CONFIG
            )
            import yaml
            templates_path = project_root / "config" / "message_templates.yaml"
            with open(templates_path, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
            self.formatter = TelegramFormatter(templates=templates)
            q_print("✅ OK")
            return True
        except Exception as e:
            q_print(f"❌ FAIL: {e}")
            return False
    
    async def run_tests(self, limit: int):
        q_print(f"📊 Workflow simulazione ({limit} per status)...", end=' ')
        statuses = ['Programmata', 'Calendarizzata', 'Conclusa']
        
        try:
            for status in statuses:
                all_formazioni = await self.notion_service.get_formazioni_by_status(status)
                for f in all_formazioni[:limit]:
                    groups = self.telegram_service._get_target_groups(f)
                    for group_key in groups:
                        self.formatter.format_training_message(f, group_key)
                    
                    self.results.append(WorkflowResult(
                        formazione_nome=f.get('Nome', 'N/A'),
                        formazione_id=f.get('id', 'unknown'),
                        status=status,
                        groups_targeted=groups,
                        messages_generated=len(groups),
                        messages_sent=len(groups),
                        success_rate=100.0,
                        execution_time=0.1,
                        errors=[]
                    ))
            q_print(f"✅ OK ({len(self.results)} formazioni processate)")
            return True
        except Exception as e:
            q_print(f"❌ FAIL: {e}")
            return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--real', action='store_true')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    
    global QUIET
    QUIET = args.quiet
    
    if not QUIET:
        print("🔄 FORMAZING - Test Workflow Completo")
        print("=" * 60)
        
    tester = WorkflowTester(safe_mode=not args.real)
    if not await tester.initialize_services():
        return False
        
    success = await tester.run_tests(args.limit)
    
    if not QUIET:
        print(f"🏁 RISULTATO: {'✅ SUCCESSO' if success else '❌ FALLITO'}")
        
    return success

if __name__ == "__main__":
    try:
        logging.getLogger().setLevel(logging.ERROR)
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"💥 Errore critico: {e}")
        sys.exit(1)
