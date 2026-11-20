param([string]$InnoCompiler = "")
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name AsciiArtStudio ascii_art_studio.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
if (!$InnoCompiler) { $InnoCompiler = (Get-Command ISCC.exe -ErrorAction Stop).Source }
& $InnoCompiler installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
