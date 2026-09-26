# ==============================================================================
# NovaFlow - Lancement Complet (Backend FastAPI + Frontend Next.js + Bot Discord)
# ==============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             🚀 LANCEMENT GLOBAL DE NOVAFLOW               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ROOT_DIR) { $ROOT_DIR = Get-Location }

# 1. Nettoyage préventif des anciens processus uvicorn/next orphelins sur les ports
Write-Host "`n[Nettoyage] Vérification des ports 8000 et 3000..." -ForegroundColor DarkGray
Get-Process -Name node, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Démarrage de l'API Backend FastAPI (Port 8000)
Write-Host "`n[1/3] ⚙️  Démarrage de l'API Backend FastAPI (http://localhost:8000)..." -ForegroundColor Green
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$VENV_PYTHON = Join-Path $BACKEND_DIR "venv\Scripts\python.exe"

if (-not (Test-Path $VENV_PYTHON)) {
    $VENV_PYTHON = "python"
}

# Lancer le backend dans sa propre fenêtre pour voir les logs d'API
$backendProcess = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-Command", "cd '$BACKEND_DIR'; & '$VENV_PYTHON' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" `
    -PassThru

# 3. Démarrage du Frontend Next.js (Port 3000)
Write-Host "[2/3] 🖥️  Démarrage du Frontend Next.js (http://localhost:3000)..." -ForegroundColor Green
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"

# Lancer Next.js dans sa propre fenêtre pour voir la compilation et les logs Turbopack
$frontendProcess = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-Command", "cd '$FRONTEND_DIR'; npm run dev" `
    -PassThru

# 4. Attente active que le serveur web réponde sur le port 3000
Write-Host "`n⏳ Attente de l'initialisation du serveur Web..." -ForegroundColor Yellow
$maxWait = 25
$waited = 0
$serverReady = $false

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 2
    $waited += 2
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $serverReady = $true
            break
        }
    } catch {
        Write-Host "   ...compilation en cours ($waited s)" -ForegroundColor DarkGray
    }
}

if ($serverReady) {
    Write-Host "   ✅ Dashboard Web en ligne : http://localhost:3000" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Next.js prend un peu de temps à compiler, mais il est lancé dans sa fenêtre." -ForegroundColor Yellow
}

# 5. Démarrage du Bot Discord (au premier plan dans ce terminal)
Write-Host "`n[3/3] 🤖 Démarrage du Bot Discord NovaFlow..." -ForegroundColor Magenta
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   • Web Dashboard : http://localhost:3000" -ForegroundColor White
Write-Host "   • API Backend   : http://localhost:8000" -ForegroundColor White
Write-Host "   • Bot Discord   : En cours d'exécution ci-dessous" -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Cyan

try {
    Push-Location $BACKEND_DIR
    & $VENV_PYTHON -m app.main_bot
}
finally {
    Pop-Location
    Write-Host "`n🛑 Arrêt des services..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
