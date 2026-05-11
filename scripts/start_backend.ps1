# start_backend.ps1 — Launch Agentic DevStudio backend services only (no frontend)
# Usage: .\scripts\start_backend.ps1

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

Write-Host "Starting Agentic DevStudio services..." -ForegroundColor Cyan
Write-Host "  pod-memory  : http://localhost:8000"
Write-Host "  pod-mcp     : http://localhost:8001"
Write-Host "  studio-api  : http://localhost:8080"
Write-Host ""

# Encode a command string to base64 so it can be passed to pwsh -EncodedCommand
# without semicolons or quotes causing argument-parsing issues.
function Encode-Command([string]$Cmd) {
    [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($Cmd))
}

$Enc1 = Encode-Command "Set-Location '$Root'; Write-Host '[pod-memory] starting on :8000' -ForegroundColor Green; uv run uvicorn pod_memory.server:app --app-dir packages/pod-memory --port 8000"
$Enc2 = Encode-Command "Set-Location '$Root'; Write-Host '[pod-mcp] starting on :8001' -ForegroundColor Yellow; uv run uvicorn pod_mcp.server:app --app-dir packages/pod-mcp --port 8001"
$Enc3 = Encode-Command "Set-Location '$Root'; Write-Host '[studio-api] starting on :8080' -ForegroundColor Magenta; uv run uvicorn main:app --app-dir apps/studio-api --port 8080 --reload"

if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
    # Windows Terminal: open all three services as named, coloured tabs in one window.
    # Start-Process joins the array with spaces; bare ";" elements become wt subcommand separators.
    Start-Process wt -ArgumentList @(
        "new-tab", "--title", "pod-memory", "--tabColor", "#16C60C",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc1,
        ";",
        "new-tab", "--title", "pod-mcp", "--tabColor", "#F9F1A5",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc2,
        ";",
        "new-tab", "--title", "studio-api", "--tabColor", "#B4009E",
        "pwsh", "-NoExit", "-EncodedCommand", $Enc3
    )
    Write-Host "Services launched in Windows Terminal tabs." -ForegroundColor Cyan
} else {
    # Fallback: separate windows (wt.exe not found)
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc1
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc2
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $Enc3
    Write-Host "Services launched in separate windows (Windows Terminal not found)." -ForegroundColor Yellow
}

Write-Host "Wait ~10s for models to load, then send your first task."
