param(
    [string]$FunctionName = "stock-ingest-lambda",
    [string]$Symbol = "AAPL",
    [string]$StartDate = "2024-01-01",
    [string]$EndDate = "2024-01-30"
)

Write-Host "Step 1: test the Lambda manually before scheduling it"
$payload = @{
    symbol = $Symbol
    start_date = $StartDate
    end_date = $EndDate
} | ConvertTo-Json -Compress

aws lambda invoke `
    --function-name $FunctionName `
    --cli-binary-format raw-in-base64-out `
    --payload $payload `
    response.json | Out-Null

Write-Host "Step 2: read the Lambda response"
Get-Content response.json | Out-String | Write-Host

Write-Host "If the response contains 'storage' with raw/processed keys, the AWS ingestion step is working."
