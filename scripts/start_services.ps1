# start_services.ps1 — Launch all Agentic DevStudio backend services
# Usage: .\scripts\start_services.ps1 [-TargetRepo "C:\path\to\your\repo"]

param(
    [string]$TargetRepo = ""
)

$Root = Split-Path $PSScriptRoot -Parent

# Load .env if present
$EnvFile = Join-Path $Root ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+?)\s*=\s*(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
        }
    }
} else {
    Write-Error ".env not found at $EnvFile — copy .env.example and fill in your values."
    exit 1
}

# Resolve TARGET_REPO_PATH: flag > .env > error
if ($TargetRepo) {
    $env:TARGET_REPO_PATH = $TargetRepo
}
if (-not $env:TARGET_REPO_PATH) {
    Write-Error "TARGET_REPO_PATH is not set. Pass it via -TargetRepo or set it in .env."
    exit 1
}

Write-Host "Starting Agentic DevStudio services..." -ForegroundColor Cyan
Write-Host "  Target repo : $env:TARGET_REPO_PATH"
Write-Host "  pod-memory  : http://localhost:8000"
Write-Host "  pod-mcp     : http://localhost:8001"
Write-Host "  studio-api  : http://localhost:8080"
Write-Host ""

# pod-memory — ChromaDB semantic layer
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$Root'; Write-Host '[pod-memory] starting on :8000' -ForegroundColor Green; uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000"

Start-Sleep -Seconds 2

# pod-mcp — MCP filesystem/shell/git tools
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$Root'; `$env:TARGET_REPO_PATH='$env:TARGET_REPO_PATH'; Write-Host '[pod-mcp] starting on :8001' -ForegroundColor Yellow; uv run uvicorn pod_mcp.server:app --app-dir packages/pod-mcp --port 8001"

Start-Sleep -Seconds 2

# studio-api — pod-brain FastAPI + AG-UI SSE
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$Root'; Write-Host '[studio-api] starting on :8080' -ForegroundColor Magenta; uv run uvicorn main:app --app-dir apps/studio-api --port 8080 --reload"

Write-Host "All services launched in separate windows." -ForegroundColor Cyan
Write-Host "Wait ~10s for models to load, then send your first task."
