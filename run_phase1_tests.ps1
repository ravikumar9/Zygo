# PHASE 1 PLAYWRIGHT VERIFICATION EXECUTION SCRIPT (POWERSHELL)
# 
# This script handles the complete Phase 1 automation verification
# Usage:
#   .\run_phase1_tests.ps1              # Run all tests (headless)
#   .\run_phase1_tests.ps1 -Mode headed # Run with browser visible
#   .\run_phase1_tests.ps1 -Mode debug  # Run with debugger
#   .\run_phase1_tests.ps1 -Mode owner  # Owner registration tests only
#   .\run_phase1_tests.ps1 -Mode admin  # Admin approval tests only
#
# If you get "script execution disabled" error, run:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

param(
    [string]$Mode = "headless"
)

# Colors for output
$Green = [ConsoleColor]::Green
$Red = [ConsoleColor]::Red
$Yellow = [ConsoleColor]::Yellow
$Cyan = [ConsoleColor]::Cyan

Write-Host ""
Write-Host "=========================================" -ForegroundColor $Cyan
Write-Host "🚀 PHASE 1 PLAYWRIGHT VERIFICATION" -ForegroundColor $Cyan
Write-Host "=========================================" -ForegroundColor $Cyan
Write-Host "Mode: $Mode" -ForegroundColor $Yellow
Write-Host ""

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing Node dependencies..." -ForegroundColor $Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ npm install failed" -ForegroundColor $Red
        exit 1
    }
    Write-Host ""
}

# Find and activate Python venv
$venvPaths = @(".\.venv-1", ".\venv", ".\.venv")
$venvFound = $false

foreach ($venvPath in $venvPaths) {
    if (Test-Path "$venvPath\Scripts\activate.ps1") {
        Write-Host "🐍 Activating Python virtual environment: $venvPath" -ForegroundColor $Yellow
        & "$venvPath\Scripts\activate.ps1"
        $venvFound = $true
        break
    }
}

if (-not $venvFound) {
    Write-Host "❌ Python virtual environment not found" -ForegroundColor $Red
    Write-Host "   Please create with: python -m venv .venv-1" -ForegroundColor $Yellow
    exit 1
}

Write-Host "✅ Environment ready" -ForegroundColor $Green
Write-Host ""

# Run tests based on mode
switch ($Mode.ToLower()) {
    "headless" {
        Write-Host "🎬 Running tests in HEADLESS mode..." -ForegroundColor $Cyan
        npm test
    }
    "headed" {
        Write-Host "👀 Running tests in HEADED mode (browser visible)..." -ForegroundColor $Cyan
        npm run test:headed
    }
    "debug" {
        Write-Host "🐛 Running tests in DEBUG mode..." -ForegroundColor $Cyan
        npm run test:debug
    }
    "owner" {
        Write-Host "👤 Running OWNER REGISTRATION tests only..." -ForegroundColor $Cyan
        npm run test:owner
    }
    "admin" {
        Write-Host "👨‍💼 Running ADMIN APPROVAL tests only..." -ForegroundColor $Cyan
        npm run test:admin
    }
    "visibility" {
        Write-Host "👁️ Running USER VISIBILITY tests only..." -ForegroundColor $Cyan
        npm run test:visibility
    }
    "negative" {
        Write-Host "❌ Running NEGATIVE TEST CASES only..." -ForegroundColor $Cyan
        npm run test:negative
    }
    default {
        Write-Host "❌ Unknown mode: $Mode" -ForegroundColor $Red
        Write-Host "Usage: .\run_phase1_tests.ps1 -Mode [headless|headed|debug|owner|admin|visibility|negative]" -ForegroundColor $Yellow
        exit 1
    }
}

$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=========================================" -ForegroundColor $Cyan

if ($testExitCode -eq 0) {
    Write-Host "✅ TESTS PASSED" -ForegroundColor $Green
} else {
    Write-Host "❌ TESTS FAILED" -ForegroundColor $Red
}

Write-Host "=========================================" -ForegroundColor $Cyan
Write-Host ""

Write-Host "📊 View detailed report:" -ForegroundColor $Yellow
Write-Host "   npm run test:report" -ForegroundColor $Cyan
Write-Host ""

Write-Host "📄 Test results:" -ForegroundColor $Yellow
Write-Host "   - HTML: playwright-report\index.html" -ForegroundColor $Cyan
Write-Host "   - JSON: test-results.json" -ForegroundColor $Cyan
Write-Host "   - XML: test-results.xml" -ForegroundColor $Cyan
Write-Host ""

exit $testExitCode
