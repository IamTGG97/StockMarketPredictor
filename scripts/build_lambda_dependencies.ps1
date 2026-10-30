param(
    [string]$BuildDirectory = (Join-Path $PSScriptRoot "..\.lambda-build")
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Install Docker Desktop to build Linux-compatible Lambda dependencies."
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$BuildDirectory = [System.IO.Path]::GetFullPath($BuildDirectory)
$requirementsPath = Join-Path $repositoryRoot "lambda_requirements.txt"
if (-not (Test-Path -LiteralPath $requirementsPath)) {
    throw "Lambda requirements file was not found at $requirementsPath."
}

New-Item -ItemType Directory -Force -Path $BuildDirectory | Out-Null
$repositoryMount = "type=bind,source=$($repositoryRoot.Replace('\', '/')),target=/var/task,readonly"
$buildMount = "type=bind,source=$($BuildDirectory.Replace('\', '/')),target=/asset-output"

Write-Host "Building Python 3.12 Lambda dependencies in the AWS Lambda Linux container"
& docker run --rm `
    --platform linux/amd64 `
    --mount $repositoryMount `
    --mount $buildMount `
    --entrypoint /bin/bash `
    public.ecr.aws/lambda/python:3.12 `
    -c "python -m pip install --upgrade -r /var/task/lambda_requirements.txt --target /asset-output"
if ($LASTEXITCODE -ne 0) {
    throw "Docker failed to build Lambda dependencies (exit code $LASTEXITCODE)."
}

Write-Host "Lambda dependencies are ready in $BuildDirectory"
