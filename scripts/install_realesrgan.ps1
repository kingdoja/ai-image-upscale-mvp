param(
    [string]$Url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",

    [string]$InstallDir = "models/realesrgan",

    [string]$Proxy = "",

    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path "."
$targetDir = Join-Path $root $InstallDir
$downloadDir = Join-Path $targetDir "_download"
$zipPath = Join-Path $downloadDir "realesrgan-ncnn-vulkan.zip"

New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null

$requestArgs = @{
    Uri = $Url
    OutFile = $zipPath
    UseBasicParsing = $true
}

if ($Proxy -ne "") {
    $requestArgs.Proxy = $Proxy
}

Write-Host "Downloading Real-ESRGAN ncnn-vulkan..."
Write-Host "URL: $Url"
Write-Host "Target: $zipPath"
Invoke-WebRequest @requestArgs

Write-Host "Extracting..."
Expand-Archive -LiteralPath $zipPath -DestinationPath $targetDir -Force

$exe = Get-ChildItem -LiteralPath $targetDir -Recurse -Filter "realesrgan-ncnn-vulkan.exe" |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.DirectoryName "models") } |
    Select-Object -First 1
if (-not $exe) {
    $exe = Get-ChildItem -LiteralPath $targetDir -Recurse -Filter "realesrgan-ncnn-vulkan.exe" | Select-Object -First 1
}
if (-not $exe) {
    throw "Could not find realesrgan-ncnn-vulkan.exe after extraction."
}

Write-Host "Installed executable:"
Write-Host $exe.FullName

if (-not $SkipCheck) {
    & (Join-Path $root "scripts/check_realesrgan.ps1") -Executable $exe.FullName -Model "realesrgan-x4plus" -Scale 4
}

Write-Host ""
Write-Host "Use these environment variables for API:"
Write-Host "`$env:UPSCALE_FAITHFUL_BACKEND='realesrgan'"
Write-Host "`$env:REALESRGAN_EXECUTABLE='$($exe.FullName)'"
Write-Host "`$env:REALESRGAN_MODEL='realesrgan-x4plus'"
