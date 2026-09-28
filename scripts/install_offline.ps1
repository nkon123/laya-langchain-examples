# Offline install of laya + LangChain/LangGraph from a local wheel folder.
# Usage: .\scripts\install_offline.ps1 [-Wheels ..\wheels-py311] [-ModelDir ..\laya]
param(
    [string]$Wheels = (Join-Path $PSScriptRoot "..\..\wheels-py311"),
    [string]$ModelDir = (Join-Path $PSScriptRoot "..\..\laya")
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not (Test-Path $Wheels)) { throw "Wheel folder not found: $Wheels" }
if (-not (Test-Path (Join-Path $ModelDir "multilingual\model.safetensors"))) {
    throw "Model folder not found or incomplete: $ModelDir"
}

py -3.11 -m venv .venv
if (-not $?) { throw "Python 3.11 not found. Install it from python.org first." }
$py = Join-Path $root ".venv\Scripts\python.exe"

& $py -m pip install --no-index --find-links $Wheels "laya[langchain]" langgraph
if (-not $?) { throw "pip install failed" }

$env:LAYA_MODEL_DIR = (Resolve-Path $ModelDir).Path
$env:PYTHONIOENCODING = "utf-8"
& $py examples\01_basic_predict.py

Write-Host ""
Write-Host "OK. Before running examples in a new shell:"
Write-Host "  `$env:LAYA_MODEL_DIR = '$($env:LAYA_MODEL_DIR)'"
