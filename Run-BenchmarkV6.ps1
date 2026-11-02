$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -u src/benchmark_download_v6.py
if ($LASTEXITCODE -ne 0) { throw 'Benchmark download stopped; details above.' }
