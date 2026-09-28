# Install laya + LangChain/LangGraph into .venv (Python 3.14) and run the first example.
#
# The PyTorch build is picked from the CUDA version nvidia-smi reports:
#   CUDA 13.x driver -> cu130 (needed for RTX 50 series)
#   CUDA 12.x driver -> cu126 (RTX 20/30/40 series on a CUDA 12 driver)
#   no NVIDIA GPU    -> cpu
# Override with -Cuda cu126 | cu130 | cpu.
#
# Usage: .\scripts\install.ps1 [-ModelDir C:\laya\laya] [-Cuda cu126]
param(
    [string]$ModelDir = $env:LAYA_MODEL_DIR,
    [ValidateSet("", "cu126", "cu130", "cpu")]
    [string]$Cuda = ""
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not $ModelDir) { $ModelDir = Join-Path $root "models\laya" }
if (-not (Test-Path (Join-Path $ModelDir "multilingual\model.safetensors"))) {
    throw "Model folder not found or incomplete: $ModelDir (pass -ModelDir or set LAYA_MODEL_DIR)"
}

function Get-TorchBuild {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $smi) { return "cpu" }
    $header = (& $smi.Source | Select-Object -First 4) -join "`n"
    if ($header -notmatch "CUDA (?:UMD )?Version:\s*(\d+)\.(\d+)") { return "cpu" }
    $major = [int]$Matches[1]
    Write-Host "nvidia-smi reports CUDA $($Matches[1]).$($Matches[2])"
    if ($major -ge 13) { return "cu130" }
    if ($major -eq 12) { return "cu126" }
    Write-Warning "CUDA $major is too old for PyTorch 2.14; update the NVIDIA driver. Using CPU."
    return "cpu"
}

if (-not $Cuda) { $Cuda = Get-TorchBuild }
Write-Host "PyTorch build: $Cuda"

py -3.14 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.14 not found. Install it from python.org first." }
$py = Join-Path $root ".venv\Scripts\python.exe"

& $py -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

# Install torch from the matching PyTorch index BEFORE requirements.txt, and replace any
# other build already in the venv: pip treats 2.14.0+cpu as satisfying "torch", so a
# plain install would keep a CPU build.
$current = & $py -c "import importlib.util as u; print(__import__('torch').__version__ if u.find_spec('torch') else 'none')"
if ($current -notlike "*+$Cuda") {
    if ($current -ne "none") {
        Write-Host "Replacing torch $current with the $Cuda build"
        & $py -m pip uninstall -y torch
    }
    & $py -m pip install torch --no-cache-dir --index-url "https://download.pytorch.org/whl/$Cuda"
    if ($LASTEXITCODE -ne 0) { throw "torch install failed (is download.pytorch.org reachable?)" }
}

& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install -r requirements.txt failed" }

$env:LAYA_MODEL_DIR = (Resolve-Path $ModelDir).Path
$env:PYTHONIOENCODING = "utf-8"
if ($Cuda -ne "cpu") {
    $ok = & $py -c "import torch; print(torch.cuda.is_available())"
    if ($ok -ne "True") {
        Write-Warning "torch $Cuda is installed but CUDA is not available. Check the driver with nvidia-smi. Laya will run on CPU."
    } else {
        & $py -c "import torch; print('GPU:', torch.cuda.get_device_name(0))"
        # fp16 autocast matched the CPU answers in our tests; the bf16 default changed one route.
        $env:LAYA_CUDA_AMP = "fp16"
    }
}

& $py examples\01_basic_predict.py

Write-Host ""
Write-Host "OK. To keep these settings for new shells:"
Write-Host "  setx LAYA_MODEL_DIR `"$($env:LAYA_MODEL_DIR)`""
if ($env:LAYA_CUDA_AMP) { Write-Host "  setx LAYA_CUDA_AMP fp16" }
