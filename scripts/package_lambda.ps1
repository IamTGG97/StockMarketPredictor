param(
    [string]$BuildDirectory = (Join-Path $PSScriptRoot "..\.lambda-build"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\lambda-deployment.zip")
)

$ErrorActionPreference = "Stop"
$BuildDirectory = (Resolve-Path $BuildDirectory).Path
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$temporaryPath = "$OutputPath.tmp"

if (-not (Test-Path (Join-Path $PSScriptRoot "..\lambda_function.py"))) {
    throw "lambda_function.py was not found in the repository."
}
if (-not (Test-Path (Join-Path $PSScriptRoot "..\lambda_dispatcher.py"))) {
    throw "lambda_dispatcher.py was not found in the repository."
}
if (-not (Test-Path (Join-Path $PSScriptRoot "..\utils\market_api.py"))) {
    throw "utils\market_api.py was not found in the repository."
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$entryNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
$stream = [System.IO.File]::Open($temporaryPath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
$archive = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create, $false)

function Add-PackageFile([string]$FilePath, [string]$EntryName) {
    $EntryName = $EntryName.Replace("\", "/")
    if (-not $entryNames.Add($EntryName)) {
        throw "Duplicate Lambda package path: $EntryName"
    }
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $archive,
        $FilePath,
        $EntryName,
        [System.IO.Compression.CompressionLevel]::Optimal
    ) | Out-Null
}

try {
    Get-ChildItem -Path $BuildDirectory -File -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Substring($BuildDirectory.Length).TrimStart("\").Replace("\", "/")
        if ($relativePath -match '(^|/)(bin|__pycache__)(/|$)' -or $relativePath -match '\.py[co]$') {
            return
        }
        if ($relativePath -eq "lambda_function.py" -or $relativePath -match '^utils/') {
            return
        }
        Add-PackageFile $_.FullName $relativePath
    }

    $repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    Add-PackageFile (Join-Path $repositoryRoot "lambda_function.py") "lambda_function.py"
    Add-PackageFile (Join-Path $repositoryRoot "lambda_dispatcher.py") "lambda_dispatcher.py"
    Get-ChildItem -Path (Join-Path $repositoryRoot "utils") -Filter "*.py" -File -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Substring($repositoryRoot.Length).TrimStart("\").Replace("\", "/")
        Add-PackageFile $_.FullName $relativePath
    }
}
finally {
    $archive.Dispose()
    $stream.Dispose()
}

$checkArchive = [System.IO.Compression.ZipFile]::OpenRead($temporaryPath)
try {
    $uncompressedBytes = [long](($checkArchive.Entries | Measure-Object -Property Length -Sum).Sum)
    foreach ($requiredPath in @(
        "lambda_function.py",
        "lambda_dispatcher.py",
        "utils/market_api.py",
        "utils/storage.py",
        "utils/sp500_symbols.py"
    )) {
        if (-not $checkArchive.GetEntry($requiredPath)) {
            throw "Lambda package is missing $requiredPath."
        }
    }
    if ($uncompressedBytes -gt 250MB) {
        throw "Uncompressed Lambda package exceeds AWS's 250 MB limit."
    }
}
finally {
    $checkArchive.Dispose()
}

Move-Item -Path $temporaryPath -Destination $OutputPath -Force
$zipSize = (Get-Item $OutputPath).Length
Write-Host ("Created {0:N1} MB package ({1:N1} MB uncompressed)." -f ($zipSize / 1MB), ($uncompressedBytes / 1MB))
