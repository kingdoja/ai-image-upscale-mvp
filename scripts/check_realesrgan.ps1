param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,

    [string]$Model = "realesrgan-x4plus",

    [ValidateSet(2, 4)]
    [int]$Scale = 4,

    [string]$WorkDir = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Real-ESRGAN executable not found: $Executable"
}

$root = Resolve-Path "."
if ($WorkDir -eq "") {
    $WorkDir = Join-Path $env:TEMP "ai-upscale-realesrgan-check"
}
$checkDir = $WorkDir
New-Item -ItemType Directory -Force -Path $checkDir | Out-Null

$inputPath = Join-Path $checkDir "input.png"
$outputPath = Join-Path $checkDir "output.png"

Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap 96, 64
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::FromArgb(238, 242, 247))
$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(31, 78, 121)), 3
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(31, 78, 121))
$font = New-Object System.Drawing.Font "Arial", 12
$graphics.DrawRectangle($pen, 12, 14, 72, 36)
$graphics.DrawString("NINEBOT", $font, $brush, 20, 24)
$bitmap.Save($inputPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Force
}

Write-Host "Running Real-ESRGAN check..."
Write-Host "Executable: $Executable"
Write-Host "Model: $Model"
Write-Host "Scale: $Scale"

Push-Location (Split-Path -Parent $Executable)
try {
    & $Executable -i $inputPath -o $outputPath -s $Scale -n $Model
}
finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) {
    throw "Real-ESRGAN exited with code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $outputPath)) {
    throw "Real-ESRGAN did not create output: $outputPath"
}

$source = [System.Drawing.Image]::FromFile($inputPath)
$result = [System.Drawing.Image]::FromFile($outputPath)
$expectedWidth = $source.Width * $Scale
$expectedHeight = $source.Height * $Scale
Write-Host "input=$($source.Width)x$($source.Height), output=$($result.Width)x$($result.Height), expected=$($expectedWidth)x$($expectedHeight)"
if ($result.Width -ne $expectedWidth -or $result.Height -ne $expectedHeight) {
    $source.Dispose()
    $result.Dispose()
    throw "Unexpected output size: $($result.Width)x$($result.Height), expected $($expectedWidth)x$($expectedHeight)"
}
$source.Dispose()
$result.Dispose()

Write-Host "Real-ESRGAN check passed."
Write-Host "Sample input: $inputPath"
Write-Host "Sample output: $outputPath"
