# ==============================================================================
# NovaFlow - Lancement Complet (Backend FastAPI + Frontend Next.js + Bot Discord)
# ==============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             🚀 LANCEMENT GLOBAL DE NOVAFLOW               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Vérification du fichier backend/.env
$ENV_FILE = Join-Path $ROOT_DIR "backend\.env"
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "⚠️  Fichier backend/.env introuvable. Copie de .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $ROOT_DIR "backend\.env.example") $ENV_FILE
}

# 2. Démarrage de l'API Backend FastAPI (Port 8000)
Write-Host "`n[1/3] ⚙️  Démarrage de l'API Backend FastAPI (http://localhost:8000)..." -ForegroundColor Green
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$VENV_PYTHON = Join-Path $BACKEND_DIR "venv\Scripts\python.exe"

if (-not (Test-Path $VENV_PYTHON)) {
    $VENV_PYTHON = "python"
}

$backendProcess = Start-Process -FilePath $VENV_PYTHON `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $BACKEND_DIR `
    -PassThru

# 3. Démarrage du Frontend Next.js (Port 3000)
Write-Host "[2/3] 🖥️  Démarrage de l'interface Web Next.js (http://localhost:3000)..." -ForegroundColor Green
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"
$frontendProcess = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $FRONTEND_DIR `
    -PassThru

# 4. Attente brève que les services réseau montent
Start-Sleep -Seconds 3

# 5. Démarrage du Bot Discord (au premier plan dans ce terminal)
Write-Host "[3/3] 🤖 Démarrage du Bot Discord NovaFlow..." -ForegroundColor Magenta
Write-Host "`n✅ Tous les services sont lancés :" -ForegroundColor Cyan
Write-Host "   • Web Dashboard : http://localhost:3000" -ForegroundColor White
Write-Host "   • API Backend   : http://localhost:8000" -ForegroundColor White
Write-Host "   • Bot Discord   : En cours d'exécution ci-dessous" -ForegroundColor White
Write-Host "   (Appuie sur Ctrl+C pour arrêter le bot et fermer les processus)`n" -ForegroundColor DarkGray

try {
    Push-Location $BACKEND_DIR
    & $VENV_PYTHON -m app.main_bot
}
finally {
    Pop-Location
    Write-Host "`n🛑 Arrêt des services d'arrière-plan en cours..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "👋 NovaFlow arrêté proprement." -ForegroundColor Green
}
