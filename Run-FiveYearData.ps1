param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python -u (Join-Path $PSScriptRoot 'src/five_year_download.py') --execute
if ($LASTEXITCODE -ne 0) { throw 'Download stopped; completed chunks are preserved for resuming.' }
