param(
    [string]$FunctionName = "stock-ingest-lambda",
    [string]$Symbol = "AAPL",
    [string]$StartDate = "2024-01-01",
    [string]$EndDate = "2024-01-30",
    [string]$Region = "us-east-2"
)

Write-Host "Step 1: test the Lambda manually before scheduling it"
$payload = @{
    symbol = $Symbol
    start_date = $StartDate
    end_date = $EndDate
} | ConvertTo-Json -Compress

$responsePath = Join-Path ([System.IO.Path]::GetTempPath()) ("stock-ingest-response-" + [guid]::NewGuid().ToString("N") + ".json")
$payloadPath = Join-Path ([System.IO.Path]::GetTempPath()) ("stock-ingest-payload-" + [guid]::NewGuid().ToString("N") + ".json")
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($payloadPath, $payload, $utf8WithoutBom)
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $invokeOutput = & aws lambda invoke `
        --function-name $FunctionName `
        --region $Region `
        --cli-binary-format raw-in-base64-out `
        --payload "fileb://$payloadPath" `
        $responsePath 2>&1
    $invokeExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

try {
    if ($invokeExitCode -ne 0) {
        $errorOutput = ($invokeOutput | ForEach-Object { "$_" }) -join [Environment]::NewLine
        throw "AWS Lambda invocation failed (exit code $invokeExitCode):`n$errorOutput"
    }
    if (-not (Test-Path $responsePath)) {
        throw "AWS CLI returned success but did not create a Lambda response file."
    }

    $metadata = ($invokeOutput -join "`n") | ConvertFrom-Json -ErrorAction Stop
    if ($metadata.FunctionError) {
        $functionResponse = Get-Content -Path $responsePath -Raw
        throw "Lambda ran but returned a function error ($($metadata.FunctionError)):`n$functionResponse"
    }

    Write-Host "Step 2: Lambda response"
    Get-Content -Path $responsePath -Raw | Write-Host
    Write-Host "Lambda invocation succeeded."
}
finally {
    Remove-Item -Path $responsePath -ErrorAction SilentlyContinue
    Remove-Item -Path $payloadPath -ErrorAction SilentlyContinue
}
