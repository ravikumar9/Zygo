@echo off
REM PHASE 1 PLAYWRIGHT VERIFICATION EXECUTION SCRIPT (WINDOWS)
REM 
REM This script handles the complete Phase 1 automation verification
REM Usage:
REM   run_phase1_tests.bat           - Run all tests (headless)
REM   run_phase1_tests.bat headed    - Run with browser visible
REM   run_phase1_tests.bat debug     - Run with debugger
REM   run_phase1_tests.bat owner     - Owner registration tests only
REM   run_phase1_tests.bat admin     - Admin approval tests only

setlocal enabledelayedexpansion

set "MODE=%1"
if "%MODE%"=="" set "MODE=headless"

echo.
echo =========================================
echo 🚀 PHASE 1 PLAYWRIGHT VERIFICATION
echo =========================================
echo Mode: %MODE%
echo.

REM Check if node_modules exists
if not exist "node_modules" (
  echo 📦 Installing Node dependencies...
  call npm install
  if errorlevel 1 (
    echo ❌ npm install failed
    exit /b 1
  )
  echo.
)

REM Check if Python venv is available
if not exist ".venv-1" (
  if not exist "venv" (
    echo ❌ Python virtual environment not found
    echo    Please create with: python -m venv .venv-1
    exit /b 1
  )
)

REM Activate Python venv
if exist ".venv-1\Scripts\activate.bat" (
  call .venv-1\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
) else (
  echo ❌ Could not find venv activation script
  exit /b 1
)

echo ✅ Environment ready
echo.

REM Run tests based on mode
if "%MODE%"=="headless" (
  echo 🎬 Running tests in HEADLESS mode...
  call npm test
) else if "%MODE%"=="headed" (
  echo 👀 Running tests in HEADED mode (browser visible)...
  call npm run test:headed
) else if "%MODE%"=="debug" (
  echo 🐛 Running tests in DEBUG mode...
  call npm run test:debug
) else if "%MODE%"=="owner" (
  echo 👤 Running OWNER REGISTRATION tests only...
  call npm run test:owner
) else if "%MODE%"=="admin" (
  echo 👨‍💼 Running ADMIN APPROVAL tests only...
  call npm run test:admin
) else if "%MODE%"=="visibility" (
  echo 👁️ Running USER VISIBILITY tests only...
  call npm run test:visibility
) else if "%MODE%"=="negative" (
  echo ❌ Running NEGATIVE TEST CASES only...
  call npm run test:negative
) else (
  echo ❌ Unknown mode: %MODE%
  echo Usage: run_phase1_tests.bat [headless^|headed^|debug^|owner^|admin^|visibility^|negative]
  exit /b 1
)

if errorlevel 1 (
  echo.
  echo ❌ Tests failed
  exit /b 1
)

echo.
echo =========================================
echo ✅ TESTS COMPLETE
echo =========================================
echo.
echo 📊 View detailed report:
echo    npm run test:report
echo.
echo 📄 Test results:
echo    - HTML: playwright-report\index.html
echo    - JSON: test-results.json
echo    - XML: test-results.xml
echo.

exit /b 0
