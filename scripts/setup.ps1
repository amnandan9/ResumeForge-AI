# ══════════════════════════════════════════════════════════
# ResumeForge AI — Setup Script (PowerShell)
# ══════════════════════════════════════════════════════════

param(
    [string]$OllamaModel = "mistral:7b"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ResumeForge AI — Setup Script          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Verify Docker ───────────────────────────────
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "  ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# ── Step 2: Build and start services ────────────────────
Write-Host "[2/5] Building and starting services..." -ForegroundColor Yellow
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose up -d --build

Write-Host "  Waiting for services to be healthy..."
Start-Sleep -Seconds 15

# Check API health
$maxRetries = 20
$retryCount = 0
do {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "  ✓ ResumeForge API is healthy" -ForegroundColor Green
            break
        }
    } catch {
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Write-Host "  ✗ API failed to start after $maxRetries attempts" -ForegroundColor Red
            docker compose logs resumeforge-api
            exit 1
        }
        Write-Host "  Waiting for API... (attempt $retryCount/$maxRetries)"
        Start-Sleep -Seconds 5
    }
} while ($true)

# ── Step 3: Pull Ollama Model ──────────────────────────
Write-Host "[3/5] Pulling Ollama model: $OllamaModel ..." -ForegroundColor Yellow
Write-Host "  This may take 5-15 minutes on first run..."
docker exec resumeforge-ollama ollama pull $OllamaModel
Write-Host "  ✓ Model $OllamaModel pulled successfully" -ForegroundColor Green

# ── Step 4: Verify Ollama ──────────────────────────────
Write-Host "[4/5] Verifying Ollama..." -ForegroundColor Yellow
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET
    Write-Host "  ✓ Ollama is running with models: $($ollamaResponse.models.name -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Ollama health check failed" -ForegroundColor Red
}

# ── Step 5: Connect existing n8n ────────────────────────
Write-Host "[5/5] Network setup for n8n..." -ForegroundColor Yellow
# Find existing n8n container
$n8nContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -match "n8n" } | Select-Object -First 1
if ($n8nContainer) {
    Write-Host "  Found existing n8n container: $n8nContainer"
    try {
        docker network connect resumeforge-network $n8nContainer 2>$null
        Write-Host "  ✓ Connected $n8nContainer to resumeforge-network" -ForegroundColor Green
    } catch {
        Write-Host "  (Already connected or skipped)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  No existing n8n container found. Start n8n and connect it manually:" -ForegroundColor DarkYellow
    Write-Host "    docker network connect resumeforge-network <your-n8n-container>" -ForegroundColor DarkYellow
}

# ── Done ────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ResumeForge AI is READY!             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  API:     http://localhost:8000" -ForegroundColor White
Write-Host "  Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Ollama:  http://localhost:11434" -ForegroundColor White
Write-Host ""
Write-Host "  Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open your n8n UI"
Write-Host "  2. Import the workflow from: n8n-workflow/resumeforge_workflow.json"
Write-Host "  3. Activate the workflow"
Write-Host "  4. Run: .\scripts\test_pipeline.ps1"
Write-Host ""
