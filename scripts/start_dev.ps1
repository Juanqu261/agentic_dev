# start_dev.ps1 — Launch all Agentic DevStudio services in development mode
# Backend services + frontend (Next.js dev server) in Windows Terminal tabs.
# Usage: .\scripts\start_dev.ps1

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

Write-Host "Starting Agentic DevStudio (dev mode)..." -ForegroundColor Cyan
Write-Host "  pod-memory  : http://localhost:8000"
Write-Host "  pod-mcp     : http://localhost:8001"
Write-Host "  studio-api  : http://localhost:8080"
Write-Host "  studio-ui   : http://localhost:3000"
Write-Host ""

function Encode-Command([string]$Cmd) {
    [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($Cmd))
}

$FrontendDir = Join-Path $Root "apps\studio-ui"

$Enc1 = Encode-Command "Set-Location '$Root'; Write-Host '[pod-memory] starting on :8000' -ForegroundColor Green; uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000"
$Enc2 = Encode-Command "Set-Location '$Root'; Write-Host '[pod-mcp] starting on :8001' -ForegroundColor Yellow; uv run uvicorn pod_mcp.server:app --app-dir packages/pod-mcp --port 8001"
$Enc3 = Encode-Command "Set-Location '$Root'; Write-Host '[studio-api] starting on :8080' -ForegroundColor Magenta; uv run uvicorn main:app --app-dir apps/studio-api --port 8080 --reload"
$Enc4 = Encode-Command "Set-Location '$FrontendDir'; Write-Host '[studio-ui] starting on :3000' -ForegroundColor Cyan; npm run dev"

if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
    Start-Process wt -ArgumentList @(
        "new-tab", "--title", "pod-memory", "--tabColor", "#16C60C",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc1,
        ";",
        "new-tab", "--title", "pod-mcp", "--tabColor", "#F9F1A5",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc2,
        ";",
        "new-tab", "--title", "studio-api", "--tabColor", "#B4009E",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc3,
        ";",
        "new-tab", "--title", "studio-ui", "--tabColor", "#0078D4",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc4
    )
    Write-Host "Services launched in Windows Terminal tabs." -ForegroundColor Cyan
} else {
    # Fallback: separate windows
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc1
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc2
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc3
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc4
    Write-Host "Services launched in separate windows (Windows Terminal not found)." -ForegroundColor Yellow
}

Write-Host "Wait ~10s for backend models to load, then open http://localhost:3000"
