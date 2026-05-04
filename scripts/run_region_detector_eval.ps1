param(
    [string]$TesseractCommand = "D:\Tools\Tesseract-OCR\tesseract.exe",
    [string]$PythonCommand = "",
    [string]$Annotations = "datasets\region-eval\annotations.json",
    [switch]$SkipLogoBaseline
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ($PythonCommand -eq "") {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $PythonCommand = $venvPython
    } else {
        $PythonCommand = "python"
    }
}

$reportsDir = Join-Path $ProjectRoot "reports"
$publicReportsDir = Join-Path $ProjectRoot "apps\web\public\reports"
New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
New-Item -ItemType Directory -Force -Path $publicReportsDir | Out-Null

$tesseractMarkdown = Join-Path $reportsDir "region-detector-eval-tesseract.md"
$tesseractCsv = Join-Path $reportsDir "region-detector-eval-tesseract.csv"
$logoMarkdown = Join-Path $reportsDir "region-detector-eval-tesseract-logo-baseline.md"
$logoCsv = Join-Path $reportsDir "region-detector-eval-tesseract-logo-baseline.csv"

$publicTesseractMarkdown = Join-Path $publicReportsDir "region-detector-eval-tesseract.md"
$publicTesseractCsv = Join-Path $publicReportsDir "region-detector-eval-tesseract.csv"
$publicLogoMarkdown = Join-Path $publicReportsDir "region-detector-eval-tesseract-logo-baseline.md"
$publicLogoCsv = Join-Path $publicReportsDir "region-detector-eval-tesseract-logo-baseline.csv"

Write-Host "Running region detector evaluation..."
Write-Host "Open this first: $logoMarkdown"
Write-Host "Secondary report: $tesseractMarkdown"
Write-Host "Python: $PythonCommand"
Write-Host "Tesseract: $TesseractCommand"

& $PythonCommand tools\evaluate_region_detector.py `
    --annotations $Annotations `
    --backend tesseract `
    --tesseract-command $TesseractCommand `
    --markdown-output $tesseractMarkdown `
    --csv-output $tesseractCsv

if ($LASTEXITCODE -ne 0) {
    throw "Tesseract evaluation failed with code $LASTEXITCODE"
}

if (-not $SkipLogoBaseline) {
    & $PythonCommand tools\evaluate_region_detector.py `
        --annotations $Annotations `
        --backend tesseract `
        --tesseract-command $TesseractCommand `
        --logo-detector-backend external `
        --logo-detector-command "$PythonCommand tools\logo_detector_baseline.py" `
        --markdown-output $logoMarkdown `
        --csv-output $logoCsv

    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract + logo baseline evaluation failed with code $LASTEXITCODE"
    }
}

Copy-Item -LiteralPath $tesseractMarkdown -Destination $publicTesseractMarkdown -Force
Copy-Item -LiteralPath $tesseractCsv -Destination $publicTesseractCsv -Force
if (-not $SkipLogoBaseline) {
    Copy-Item -LiteralPath $logoMarkdown -Destination $publicLogoMarkdown -Force
    Copy-Item -LiteralPath $logoCsv -Destination $publicLogoCsv -Force
}

Write-Host ""
Write-Host "Evaluation complete."
Write-Host "Primary report: $logoMarkdown"
Write-Host "Tesseract-only report: $tesseractMarkdown"
Write-Host "Web report URL: /reports/region-detector-eval-tesseract-logo-baseline.md"
if ($SkipLogoBaseline) {
    Write-Host "Logo baseline run skipped."
}
