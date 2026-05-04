param(
    [string]$Executable = "tesseract",
    [string]$WorkDir = ""
)

$ErrorActionPreference = "Stop"

if ($WorkDir -eq "") {
    $WorkDir = Join-Path $env:TEMP "ai-upscale-tesseract-check"
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$inputPath = Join-Path $WorkDir "ocr-input.png"
$outputBase = Join-Path $WorkDir "ocr-output"
$tsvPath = "$outputBase.tsv"

Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap 360, 120
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::White)
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::Black)
$font = New-Object System.Drawing.Font "Arial", 34, ([System.Drawing.FontStyle]::Bold)
$graphics.DrawString("NINEBOT 2026", $font, $brush, 24, 34)
$bitmap.Save($inputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

if (Test-Path -LiteralPath $tsvPath) {
    Remove-Item -LiteralPath $tsvPath -Force
}

Write-Host "Checking Tesseract OCR..."
Write-Host "Executable: $Executable"
& $Executable --version
if ($LASTEXITCODE -ne 0) {
    throw "Tesseract version check failed with code $LASTEXITCODE"
}

& $Executable $inputPath $outputBase --psm 6 tsv
if ($LASTEXITCODE -ne 0) {
    throw "Tesseract OCR check failed with code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $tsvPath)) {
    throw "Tesseract did not create TSV output: $tsvPath"
}

$content = Get-Content -LiteralPath $tsvPath -Raw
if ($content -notmatch "NINEBOT") {
    Write-Warning "TSV output was created, but expected text was not found. OCR may still work on real images; inspect $tsvPath."
}

Write-Host "Tesseract check completed."
Write-Host "Sample input: $inputPath"
Write-Host "TSV output: $tsvPath"
Write-Host "Set UPSCALE_REGION_DETECTOR_BACKEND=tesseract and UPSCALE_TESSERACT_COMMAND=$Executable to enable OCR-backed region detection."
