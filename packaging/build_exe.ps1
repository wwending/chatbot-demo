param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not $SkipInstall) {
    python -m pip install -r requirements-build.txt
}

python -m app.db.init_db
python -m app.rag.ingest
python -m PyInstaller chatbot-demo.spec --clean --noconfirm

Write-Host ""
Write-Host "Built dist\chatbot-demo.exe"
Write-Host "Run it to open the native desktop client."
