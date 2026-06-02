#!/bin/bash

echo ""
echo "🧪 FORMAZING QUICK TEST RUNNER"
echo "==============================="

show_help() {
    echo ""
    echo "💡 Uso: ./quick_test.sh [COMANDO]"
    echo ""
    echo "🎯 COMANDI DISPONIBILI:"
    echo "   unit     - Test unitari (veloci)"
    echo "   config   - Verifica connessioni reali"
    echo "   workflow - Simulazione completa safe"
    echo "   all      - Suite completa step-by-step (consigliato)"
    echo ""
}

check_prerequisites() {
    echo "🔧 Setup ambiente..."
    
    if [ ! -f ".env" ]; then
        echo "❌ File .env non trovato!"
        echo "💡 Crea il file .env con i token necessari"
        exit 1
    fi

    if [ ! -f "tests/config/test_telegram_groups.json" ]; then
        echo "❌ File tests/config/test_telegram_groups.json non trovato!"
        exit 1
    fi
}

if [ -z "$1" ]; then
    show_help
    exit 0
fi

check_prerequisites

# Usa python3 come default se disponibile, altrimenti python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

case "$1" in
    "unit")
        echo "⚡ Esecuzione test unitari..."
        $PYTHON_CMD -m pytest tests/unit/ -v --tb=short
        ;;
        
    "config")
        echo "🔍 Verifica connessioni..."
        $PYTHON_CMD tests/e2e/test_real_config.py
        ;;
        
    "workflow")
        echo "🔄 Test workflow completo (safe)..."
        $PYTHON_CMD tests/e2e/test_workflow.py --limit 3
        ;;
        
    "all")
        echo "🚀 SUITE COMPLETA PRE-COMMIT"
        echo ""
        
        echo "🟦 STEP 1/4 - Test Unitari"
        echo "---------------------------"
        echo "🎯 Target: Logica interna (Notion, Telegram, Microsoft)"
        read -p "👉 Premere INVIO per avviare i test unitari..."
        $PYTHON_CMD -m pytest tests/unit/ --tb=short
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ TEST UNITARI FALLITI - Suite interrotta"
            exit 1
        fi
        echo "✅ Step 1 completato!"
        echo ""

        echo "🟨 STEP 2/4 - Verifica Connessioni"
        echo "------------------------------------"
        echo "🎯 Target: Notion API + Telegram Bot Token"
        read -p "👉 Premere INVIO per verificare le connessioni..."
        $PYTHON_CMD tests/e2e/test_real_config.py
        if [ $? -ne 0 ]; then
            echo ""
            echo "⚠️ Problemi di connessione rilevati."
            read -p "❓ Vuoi continuare comunque? (s/N): " choice
            if [[ ! "$choice" =~ ^[Ss]$ ]]; then
                echo "⏭️ Suite interrotta."
                exit 1
            fi
        fi
        echo "✅ Step 2 completato!"
        echo ""

        echo "🟩 STEP 3/4 - Test Formattazione"
        echo "--------------------------------"
        echo "🎯 Target: Validazione template YAML con dati reali"
        read -p "👉 Premere INVIO per testare la formattazione..."
        $PYTHON_CMD tests/e2e/test_real_formatting.py
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ ERRORE FORMATTAZIONE - Suite interrotta"
            exit 1
        fi
        echo "✅ Step 3 completato!"
        echo ""

        echo "🟪 STEP 4/4 - Workflow Simulazione"
        echo "----------------------------------"
        echo "🎯 Target: Simulazione processo completo (Safe)"
        read -p "👉 Premere INVIO per avviare la simulazione finale..."
        $PYTHON_CMD tests/e2e/test_workflow.py --limit 3
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ WORKFLOW FALLITO - Controlla i log"
            exit 1
        fi
        
        echo ""
        echo "🎉 =========================================="
        echo "🎉 SUITE COMPLETATA CON SUCCESSO!"
        echo "🎉 =========================================="
        ;;
        
    *)
        echo "❌ Comando non riconosciuto: $1"
        show_help
        exit 1
        ;;
esac

echo ""
echo "✅ Operazione completata"
