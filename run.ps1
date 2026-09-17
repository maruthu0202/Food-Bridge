# ============================================================
#  FoodBridge -- Auto Setup and Run Script (PowerShell)
#  Run this file to set up and launch the application
# ============================================================

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   FOODBRIDGE -- Auto Setup and Launch      " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$ProjectDir = $PSScriptRoot
$PythonExe  = "$ProjectDir\venv\Scripts\python.exe"

# Step 1: Check Python is installed
Write-Host "[STEP 1] Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "         Found: $pythonVersion" -ForegroundColor Green

# Step 2: Create virtual environment if not exists
if (-Not (Test-Path "$ProjectDir\venv")) {
    Write-Host ""
    Write-Host "[STEP 2] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv "$ProjectDir\venv"
    Write-Host "         Virtual environment created." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[STEP 2] Virtual environment already exists. Skipping." -ForegroundColor Green
}

# Step 3: Install dependencies
Write-Host ""
Write-Host "[STEP 3] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
Push-Location $ProjectDir
Start-Process -FilePath $PythonExe -ArgumentList "-m pip install -r `"$ProjectDir\requirements.txt`" --quiet" -Wait -NoNewWindow
Pop-Location
Write-Host "         All dependencies installed." -ForegroundColor Green

# Step 4: Seed demo data if DB does not exist
$dbPath = "$ProjectDir\food_donation_dev.db"
if (-Not (Test-Path $dbPath)) {
    Write-Host ""
    Write-Host "[STEP 4] Database not found. Seeding demo data..." -ForegroundColor Yellow
    Push-Location $ProjectDir
    Start-Process -FilePath $PythonExe -ArgumentList "`"$ProjectDir\seed.py`"" -Wait -NoNewWindow
    Pop-Location
    Write-Host "         Demo data seeded successfully." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[STEP 4] Database already exists. Skipping seed." -ForegroundColor Green
}

# Step 5: Run tests
Write-Host ""
Write-Host "[STEP 5] Running test suite..." -ForegroundColor Yellow
Push-Location $ProjectDir
$testResult = Start-Process -FilePath $PythonExe -ArgumentList "-m pytest `"$ProjectDir\tests`" -v --tb=short -q" -Wait -NoNewWindow -PassThru
Pop-Location
if ($testResult.ExitCode -ne 0) {
    Write-Host "         WARNING: Some tests failed. App will still start." -ForegroundColor DarkYellow
} else {
    Write-Host "         All tests passed successfully!" -ForegroundColor Green
}

# Step 6: Launch Flask dev server
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Starting FoodBridge Application...       " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  App URL : http://127.0.0.1:5000" -ForegroundColor White
Write-Host ""
Write-Host "  Demo Accounts:" -ForegroundColor White
Write-Host "    Admin : admin@foodbridge.org  / Admin@123" -ForegroundColor Gray
Write-Host "    Donor : donor@citybakery.com  / Donor@123" -ForegroundColor Gray
Write-Host "    NGO   : ngo@hopeshelter.org   / Ngo@123" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor DarkGray
Write-Host ""

$env:FLASK_ENV    = "development"
$env:SECRET_KEY   = "dev-secret-key-foodbridge-12345"

Push-Location $ProjectDir
Start-Process -FilePath $PythonExe -ArgumentList "`"$ProjectDir\app.py`"" -Wait -NoNewWindow
Pop-Location
