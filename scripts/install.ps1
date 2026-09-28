# Install laya + LangChain/LangGraph into .venv (Python 3.14) and run the first example.
# Usage: .\scripts\install.ps1 [-ModelDir C:\laya\laya]
param(
    [string]$ModelDir = $env:LAYA_MODEL_DIR
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not $ModelDir) { $ModelDir = Join-Path $root "models\laya" }
if (-not (Test-Path (Join-Path $ModelDir "multilingual\model.safetensors"))) {
    throw "Model folder not found or incomplete: $ModelDir (pass -ModelDir or set LAYA_MODEL_DIR)"
}

py -3.14 -m venv .venv
if (-not $?) { throw "Python 3.14 not found. Install it from python.org first." }
$py = Join-Path $root ".venv\Scripts\python.exe"

& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if (-not $?) { throw "pip install failed" }

$env:LAYA_MODEL_DIR = (Resolve-Path $ModelDir).Path
$env:PYTHONIOENCODING = "utf-8"
& $py examples\01_basic_predict.py

Write-Host ""
Write-Host "OK. To keep the model path for new shells:"
Write-Host "  setx LAYA_MODEL_DIR `"$($env:LAYA_MODEL_DIR)`""
