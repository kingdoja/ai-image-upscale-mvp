param(
  [int]$Port = 3000,
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [switch]$Production
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$WebRoot = Join-Path $ProjectRoot "apps\web"
$NextCli = Join-Path $WebRoot "node_modules\.bin\next.cmd"

if (-not (Test-Path -LiteralPath $NextCli)) {
  throw "Web dependencies not found under apps\web\node_modules. Run: cd apps\web; npm install"
}

$env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl

Write-Host "Starting web demo on http://127.0.0.1:$Port"
Write-Host "API base URL: $ApiBaseUrl"
Push-Location $WebRoot
try {
  if ($Production) {
    npm run build
    & $NextCli start -p $Port
  } else {
    & $NextCli dev -p $Port
  }
} finally {
  Pop-Location
}
