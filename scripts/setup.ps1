param([switch]$Upgrade)
$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction Stop
& $python.Source -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if (-not (Test-Path .venv)) { & $python.Source -m venv .venv }
$venvPython = (Resolve-Path .venv\Scripts\python.exe).Path
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
& $venvPython -m pip install -e .
if ($Upgrade) { & $venvPython -m pip install --upgrade -e . }
& $venvPython -m md_transformer --help
Write-Host "Ready: .venv\Scripts\python.exe -m md_transformer <pdf-root>"

