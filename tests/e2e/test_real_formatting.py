#!/usr/bin/env python3
"""
Test di formattazione messaggi con dati reali da Notion
======================================================
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Aggiungi la directory root del progetto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.notion import NotionService
from app.services.bot.telegram_formatters import TelegramFormatter

# Global quiet mode
QUIET = False

def q_print(msg, end='\n'):
    if not QUIET:
        print(msg, end=end)

async def get_sample_formazioni():
    q_print("🔍 Recupero formazioni reali da Notion...", end=' ')
    try:
        notion = NotionService()
        sample_formazioni = {}
        statuses = ['Programmata', 'Calendarizzata', 'Conclusa']
        for status in statuses:
            formazioni = await notion.get_formazioni_by_status(status)
            if formazioni:
                sample_formazioni[status] = formazioni[0]
        q_print(f"✅ OK ({len(sample_formazioni)} tipi trovati)")
        return sample_formazioni
    except Exception as e:
        q_print(f"❌ FAIL: {e}")
        return None

async def test_formatting(sample_formazioni):
    q_print("🎨 Validazione template YAML...", end=' ')
    import yaml
    templates_path = project_root / "config" / "message_templates.yaml"
    
    try:
        with open(templates_path, 'r', encoding='utf-8') as f:
            templates = yaml.safe_load(f)
        formatter = TelegramFormatter(templates=templates)
        
        # Test veloce di formattazione su una formazione
        if 'Programmata' in sample_formazioni:
            f = sample_formazioni['Programmata']
            formatter.format_training_message(f, 'main_group')
            
        if 'Conclusa' in sample_formazioni:
            f = sample_formazioni['Conclusa']
            formatter.format_feedback_message(f, "https://test.com", 'main_group')
            
        q_print("✅ OK")
        return True
    except Exception as e:
        q_print(f"❌ FAIL: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    
    global QUIET
    QUIET = args.quiet
    
    if not QUIET:
        print("🎨 FORMAZING - Test Formattazione Dati Reali")
        print("=" * 60)
    
    samples = await get_sample_formazioni()
    if not samples:
        return False
        
    success = await test_formatting(samples)
    
    if not QUIET:
        print(f"RISULTATO: {'✅ OK' if success else '❌ FAIL'}")
        
    return success

if __name__ == "__main__":
    try:
        logging.getLogger().setLevel(logging.ERROR)
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"💥 Errore imprevisto: {e}")
        sys.exit(1)
