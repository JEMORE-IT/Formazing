@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
echo.
echo 🧪 FORMAZING QUICK TEST RUNNER
echo ===============================

echo 🔧 Setup ambiente...
if not exist ".env" (
    echo ❌ File .env non trovato!
    goto :error
)

if "%1"=="unit" (
    echo ⚡ Esecuzione test unitari...
    python -m pytest tests/unit/ -v --tb=short
    goto :end
)

if "%1"=="config" (
    echo 🔍 Verifica connessioni...
    python tests/e2e/test_real_config.py
    goto :end
)

if "%1"=="all" (
    echo 🚀 SUITE COMPLETA PRE-COMMIT
    echo.
    
    echo 🟦 STEP 1/4 - Test Unitari
    set /p "ready=👉 Premere INVIO per avviare..."
    python -m pytest tests/unit/ --tb=short --quiet
    if !errorlevel! neq 0 goto :test_failed

    echo 🟨 STEP 2/4 - Verifica Connessioni  
    set /p "ready=👉 Premere INVIO per avviare..."
    python tests/e2e/test_real_config.py --quiet
    if !errorlevel! neq 0 (
        echo ⚠️ Problemi di connessione.
        set /p "choice=❓ Continua? (S/N): "
        if /i "!choice!" neq "S" goto :end
    )

    echo 🟩 STEP 3/4 - Test Formattazione
    set /p "ready=👉 Premere INVIO per avviare..."
    python tests/e2e/test_real_formatting.py --quiet
    if !errorlevel! neq 0 goto :test_failed

    echo 🟪 STEP 4/4 - Workflow Simulazione
    set /p "ready=👉 Premere INVIO per avviare..."
    python tests/e2e/test_workflow.py --limit 3 --quiet
    if !errorlevel! neq 0 goto :test_failed
    
    echo.
    echo 🎉 ==========================================
    echo 🎉 SUITE COMPLETATA CON SUCCESSO!
    echo 🎉 ==========================================
    goto :end
)

if "%1"=="" (
    echo 💡 Uso: quick_test.bat [all^|unit^|config^|workflow]
    goto :end
)

:test_failed
echo.
echo ❌ ERRORE: Uno degli step è fallito. Controlla l'output sopra.
goto :error

:error
echo.
echo ❌ Operazione fallita
exit /b 1

:end
echo.
echo ✅ Operazione completata
endlocal