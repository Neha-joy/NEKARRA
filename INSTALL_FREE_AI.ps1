# Run from PowerShell in the folder containing app.py. NVIDIA GPU strongly recommended.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Checking system GPU...'
Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | Format-Table
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows from https://git-scm.com/downloads/win and reopen VS Code.' }
if (-not (Test-Path '.venv')) { py -3.11 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 and ensure py -3.11 works.' } }
$PY = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $PY -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $PY -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Website dependency installation failed.' }
if (-not (Test-Path 'fashn-vton-1.5\pyproject.toml')) {
 git clone https://github.com/fashn-AI/fashn-vton-1.5.git fashn-vton-1.5
 if ($LASTEXITCODE -ne 0) { throw 'Git clone failed.' }
}
Push-Location fashn-vton-1.5
try {
  & $PY -m pip install -e .
  if ($LASTEXITCODE -ne 0) { throw 'Model dependency installation failed; check GPU/CUDA and Python version.' }
  & $PY scripts/download_weights.py --weights-dir ./weights
  if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
} finally { Pop-Location }
Write-Host 'Installation finished. Start with: .\.venv\Scripts\python.exe app.py' -ForegroundColor Green
