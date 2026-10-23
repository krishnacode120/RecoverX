$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the project .venv and install .[desktop,dev] first.' }
& $python -m PyInstaller --noconfirm --clean apps/desktop/packaging/RecoverX.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed; no installer created.' }
$compilerPath = $env:RECOVERX_ISCC
if (-not $compilerPath) { $compilerPath = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source }
if (-not $compilerPath) {
  $candidate = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
  if (Test-Path -LiteralPath $candidate) { $compilerPath = $candidate }
}
if (-not $compilerPath) { Write-Warning 'Portable app built in dist\RecoverX. Inno Setup 6 unavailable; installer not built.'; exit 2 }
& $compilerPath apps/desktop/packaging/recoverx.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Get-FileHash -Algorithm SHA256 dist/installer/RecoverX-Setup-0.2.0.exe
