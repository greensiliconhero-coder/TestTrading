param([switch]$Execute, [switch]$Login, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$created = @()
function Invoke-CheckedPython {
    param([string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Research command stopped (exit $LASTEXITCODE)." }
}
try {
    if ($Login) {
        Invoke-CheckedPython -Arguments @((Join-Path $PSScriptRoot 'src/kite_login.py'))
        return
    }
    if (-not $Execute) {
        Invoke-CheckedPython -Arguments @((Join-Path $PSScriptRoot 'src/kite_repair.py'), 'fetch')
        return
    }
    foreach ($name in @('KITE_API_KEY', 'KITE_ACCESS_TOKEN')) {
        if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
            $secure = Read-Host "Enter $name (hidden, used only in this process)" -AsSecureString
            $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
            try {
                [Environment]::SetEnvironmentVariable($name, [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer), 'Process')
                $created += $name
            } finally {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
                $secure.Dispose()
            }
        }
    }
    Invoke-CheckedPython -Arguments @((Join-Path $PSScriptRoot 'src/kite_repair.py'), 'instruments', '--execute')
    Invoke-CheckedPython -Arguments @((Join-Path $PSScriptRoot 'src/kite_repair.py'), 'fetch', '--execute')
    Invoke-CheckedPython -Arguments @((Join-Path $PSScriptRoot 'src/compare_downloads.py'))
} finally {
    foreach ($name in $created) { [Environment]::SetEnvironmentVariable($name, $null, 'Process') }
}
