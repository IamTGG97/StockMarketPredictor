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

function Add-PackageFile([string]$FilePath, [string]$EntryName, [switch]$Executable) {
    $EntryName = $EntryName.Replace("\", "/")
    if (-not $entryNames.Add($EntryName)) {
        throw "Duplicate Lambda package path: $EntryName"
    }
    $entry = [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $archive,
        $FilePath,
        $EntryName,
        [System.IO.Compression.CompressionLevel]::Optimal
    )
    if ($Executable) {
        $unixExecutableMode = ([int]0x81ED) -shl 16
        $entry.ExternalAttributes = $unixExecutableMode
    }
}

function Set-ZipEntryUnixPlatform([string]$ArchivePath, [string]$EntryName) {
    [byte[]]$bytes = [System.IO.File]::ReadAllBytes($ArchivePath)
    $minimumEndRecordOffset = [Math]::Max(0, $bytes.Length - 65557)
    $endRecordOffset = -1
    for ($index = $bytes.Length - 22; $index -ge $minimumEndRecordOffset; $index--) {
        if ($bytes[$index] -eq 0x50 -and $bytes[$index + 1] -eq 0x4B -and
            $bytes[$index + 2] -eq 0x05 -and $bytes[$index + 3] -eq 0x06) {
            $endRecordOffset = $index
            break
        }
    }
    if ($endRecordOffset -lt 0) {
        throw "The Lambda package has no ZIP end-of-central-directory record."
    }

    $centralDirectoryOffset = [int][BitConverter]::ToUInt32($bytes, $endRecordOffset + 16)
    $centralDirectorySize = [int][BitConverter]::ToUInt32($bytes, $endRecordOffset + 12)
    $centralDirectoryEnd = $centralDirectoryOffset + $centralDirectorySize
    [byte[]]$targetName = [System.Text.Encoding]::UTF8.GetBytes($EntryName)
    $found = $false

    for ($index = $centralDirectoryOffset; $index -lt $centralDirectoryEnd;) {
        if ($bytes[$index] -ne 0x50 -or $bytes[$index + 1] -ne 0x4B -or
            $bytes[$index + 2] -ne 0x01 -or $bytes[$index + 3] -ne 0x02) {
            throw "The Lambda package central directory is invalid."
        }
        $nameLength = [BitConverter]::ToUInt16($bytes, $index + 28)
        $extraLength = [BitConverter]::ToUInt16($bytes, $index + 30)
        $commentLength = [BitConverter]::ToUInt16($bytes, $index + 32)
        $nameOffset = $index + 46

        if ($nameLength -eq $targetName.Length) {
            $matchesName = $true
            for ($nameIndex = 0; $nameIndex -lt $nameLength; $nameIndex++) {
                if ($bytes[$nameOffset + $nameIndex] -ne $targetName[$nameIndex]) {
                    $matchesName = $false
                    break
                }
            }
            if ($matchesName) {
                $bytes[$index + 4] = 20
                $bytes[$index + 5] = 3
                $found = $true
                break
            }
        }
        $index += 46 + $nameLength + $extraLength + $commentLength
    }

    if (-not $found) {
        throw "Could not set Unix ZIP metadata for $EntryName."
    }
    [System.IO.File]::WriteAllBytes($ArchivePath, $bytes)
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
    Add-PackageFile (Join-Path $repositoryRoot "app.py") "app.py"
    Add-PackageFile (Join-Path $repositoryRoot "run.sh") "run.sh" -Executable
    Get-ChildItem -Path (Join-Path $repositoryRoot "utils") -Filter "*.py" -File -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Substring($repositoryRoot.Length).TrimStart("\").Replace("\", "/")
        Add-PackageFile $_.FullName $relativePath
    }
    foreach ($assetDirectory in @("template", "static")) {
        Get-ChildItem -Path (Join-Path $repositoryRoot $assetDirectory) -File -Recurse | ForEach-Object {
            $relativePath = $_.FullName.Substring($repositoryRoot.Length).TrimStart("\").Replace("\", "/")
            Add-PackageFile $_.FullName $relativePath
        }
    }
}
finally {
    $archive.Dispose()
    $stream.Dispose()
}

Set-ZipEntryUnixPlatform $temporaryPath "run.sh"

$checkArchive = [System.IO.Compression.ZipFile]::OpenRead($temporaryPath)
try {
    $uncompressedBytes = [long](($checkArchive.Entries | Measure-Object -Property Length -Sum).Sum)
    foreach ($requiredPath in @(
        "lambda_function.py",
        "lambda_dispatcher.py",
        "app.py",
        "run.sh",
        "utils/market_api.py",
        "utils/storage.py",
        "utils/sp500_symbols.py",
        "template/index.html",
        "static/main.js",
        "static/style.css",
        "flask/__init__.py",
        "gunicorn/__init__.py"
    )) {
        if (-not $checkArchive.GetEntry($requiredPath)) {
            throw "Lambda package is missing $requiredPath."
        }
    }
    $runScript = $checkArchive.GetEntry("run.sh")
    if ((($runScript.ExternalAttributes -shr 16) -band 0x1FF) -ne 0x1ED -or
        (($runScript.ExternalAttributes -shr 28) -band 0xF) -ne 0x8) {
        throw "run.sh must have Unix file metadata and executable permissions (755) in the Lambda package."
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
