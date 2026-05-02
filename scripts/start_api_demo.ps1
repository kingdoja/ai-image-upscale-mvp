param(
  [int]$Port = 8000,
  [ValidateSet("realesrgan", "stub")]
  [string]$Backend = "realesrgan",
  [switch]$Queued,
  [string]$DatabaseUrl = "sqlite:///./test-tmp/local-demo.db"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiRoot = Join-Path $ProjectRoot "apps\api"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
  throw "Project virtual environment not found: $Python. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e .\apps\api"
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "storage") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ApiRoot "test-tmp") | Out-Null

$env:STORAGE_ROOT = (Resolve-Path (Join-Path $ProjectRoot "storage")).Path
$env:DATABASE_URL = $DatabaseUrl
$env:ENQUEUE_JOBS = "false"
$env:UPSCALE_PROCESS_INLINE = if ($Queued) { "false" } else { "true" }
$env:UPSCALE_FAITHFUL_BACKEND = $Backend

if ($Backend -eq "realesrgan") {
  $Executable = Join-Path $ProjectRoot "models\realesrgan\realesrgan-ncnn-vulkan.exe"
  $ModelPath = Join-Path $ProjectRoot "models\realesrgan\models"
  if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Real-ESRGAN executable not found: $Executable. Use -Backend stub for a no-model demo, or run scripts\install_realesrgan.ps1."
  }
  if (-not (Test-Path -LiteralPath $ModelPath)) {
    throw "Real-ESRGAN model directory not found: $ModelPath. Use -Backend stub for a no-model demo, or run scripts\install_realesrgan.ps1."
  }
  $env:REALESRGAN_EXECUTABLE = (Resolve-Path $Executable).Path
  $env:REALESRGAN_MODEL_PATH = (Resolve-Path $ModelPath).Path
  $env:REALESRGAN_MODEL = "realesrgan-x4plus"
}

Write-Host "Starting API demo on http://127.0.0.1:$Port"
Write-Host "Backend: $Backend; inline processing: $($env:UPSCALE_PROCESS_INLINE); database: $DatabaseUrl"
Push-Location $ApiRoot
try {
  & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally {
  Pop-Location
}
