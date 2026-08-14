$backend = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backend '.venv\Scripts\python.exe'

$secure = Read-Host 'PostgreSQL password' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$plain = $null
$exitCode = 1

try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:VOC_DB_PASSWORD = $plain

    Push-Location $backend
    try {
        & $python -m app.bootstrap_local_training_db
        if ($LASTEXITCODE -ne 0) {
            throw "Python bootstrap failed with exit code $LASTEXITCODE."
        }
        & $python -m pytest -m localdb tests\test_local_training_db.py -v
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
} finally {
    Remove-Item Env:VOC_DB_PASSWORD -ErrorAction SilentlyContinue
    $plain = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $secure.Dispose()
}

exit $exitCode
