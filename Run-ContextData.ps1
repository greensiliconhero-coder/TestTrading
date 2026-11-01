param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python (Join-Path $PSScriptRoot 'src/context_kite.py')
if ($LASTEXITCODE -ne 0) { throw 'Context download stopped. Completed chunks remain staged.' }
