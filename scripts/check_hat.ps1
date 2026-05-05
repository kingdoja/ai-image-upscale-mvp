param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [string]$ModelPath,

    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path "."

if ($Python -eq "") {
    $Python = Join-Path $root ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "HAT repo not found: $RepoPath"
}
if (-not (Test-Path -LiteralPath $ModelPath)) {
    throw "HAT model not found: $ModelPath"
}

$workDir = Join-Path $env:TEMP "ai-upscale-hat-check"
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$inputPath = Join-Path $workDir "input.png"
$outputPath = Join-Path $workDir "output.png"

Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap 16, 12
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::FromArgb(30, 120, 200))
$bitmap.Save($inputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

& $Python (Join-Path $root "tools\run_hat_external.py") --input $inputPath --output $outputPath --scale 4 --model-path $ModelPath --repo-path $RepoPath
if ($LASTEXITCODE -ne 0) { throw "HAT check failed with code $LASTEXITCODE" }

Write-Host "HAT check passed."
