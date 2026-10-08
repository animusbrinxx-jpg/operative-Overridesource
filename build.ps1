# Run from the extracted source folder on Windows x64 with Python 3.12.
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    python -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Use 64-bit Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw 'Python version check failed' }
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    $buildPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $buildPython -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & $buildPython -m PyInstaller --clean --noconfirm --distpath dist --workpath build OperativeOverride.spec
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
    foreach ($asset in @('catalog.json','build-profile.json','HOW-TO.txt')) {
        Copy-Item -LiteralPath $asset -Destination 'dist\OperativeOverride'
    }
    Write-Output 'Build complete: dist\OperativeOverride\OperativeOverride.exe'
} finally { Pop-Location }
