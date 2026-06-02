#!/usr/bin/env python3
"""
Test di verifica configurazione reale per Notion e Telegram
==========================================================
"""

import asyncio
import logging
import os
import sys
import argparse
from pathlib import Path

# Aggiungi la directory root del progetto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.notion import NotionService
from app.services.telegram_service import TelegramService
from config import Config

# Global quiet mode
QUIET = False

def q_print(msg, end='\n'):
    if not QUIET:
        print(msg, end=end)

async def verify_notion_connection():
    q_print("🔍 Testing Notion Service...", end=' ')
    try:
        notion = NotionService()
        statuses = ['Programmata', 'Calendarizzata', 'Conclusa']
        for status in statuses:
            await notion.get_formazioni_by_status(status)
        q_print("✅ OK")
        return True
    except Exception as e:
        q_print(f"❌ FAIL: {e}")
        return False

async def verify_telegram_connection():
    q_print("🤖 Testing Telegram Service...", end=' ')
    try:
        notion_service = NotionService()
        telegram_token = Config.TELEGRAM_BOT_TOKEN
        if not telegram_token:
            q_print("❌ FAIL: Token mancante")
            return False
            
        telegram = TelegramService(
            token=telegram_token,
            notion_service=notion_service,
            groups_config_path=Config.TELEGRAM_GROUPS_CONFIG,
            templates_config_path=Config.TELEGRAM_TEMPLATES_CONFIG
        )
        
        import telegram as tg
        async with tg.Bot(token=telegram_token) as bot:
            await bot.get_me()
        q_print("✅ OK")
        return True
    except Exception as e:
        q_print(f"❌ FAIL: {e}")
        return False

def verify_environment_config():
    q_print("🔧 Verifica variabili d'ambiente...", end=' ')
    required_vars = ['NOTION_TOKEN', 'NOTION_DATABASE_ID', 'TELEGRAM_BOT_TOKEN']
    for var in required_vars:
        if not os.getenv(var):
            q_print(f"❌ FAIL: {var} mancante")
            return False
    q_print("✅ OK")
    return True

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    
    global QUIET
    QUIET = args.quiet
    
    if not QUIET:
        print("🚀 FORMAZING - Test Configurazione Reale")
        print("=" * 50)
    
    env_ok = verify_environment_config()
    notion_ok = await verify_notion_connection() if env_ok else False
    telegram_ok = await verify_telegram_connection() if env_ok else False
    
    success = env_ok and notion_ok and telegram_ok
    
    if not QUIET:
        print("\n" + "=" * 50)
        print(f"RISULTATO: {'✅ TUTTO FUNZIONA' if success else '❌ PROBLEMI RILEVATI'}")
    
    return success

if __name__ == "__main__":
    try:
        # Configura logging per non sporcare l'output
        logging.getLogger().setLevel(logging.ERROR)
        
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"💥 Errore imprevisto: {e}")
        sys.exit(1)
