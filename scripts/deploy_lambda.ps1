param(
    [string]$FunctionName = "stock-ingest-lambda",
    [string]$RoleName = "stock-predictor-lambda-role",
    [string]$BucketName = "",
    [string]$Region = "us-east-2",
    [string]$ZipPath = (Join-Path $PSScriptRoot "..\lambda-deployment.zip"),
    [string]$S3Key = "lambda-deployments/stock-ingest-lambda.zip"
)

$ErrorActionPreference = "Stop"

function Invoke-AwsCli {
    param(
        [string[]]$CliArgs,
        [switch]$AllowFailure
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & aws @CliArgs 2>&1
        $exitCode = $LASTEXITCODE
    }
    catch {
        throw "Could not run the AWS CLI: $_"
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $outputText = ($output | ForEach-Object { "$_" }) -join [Environment]::NewLine
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "AWS CLI command failed (exit code $exitCode): aws $($CliArgs -join ' ')`n$outputText"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $outputText.Trim()
    }
}

if (-not $BucketName -or $BucketName -eq "YOUR_S3_BUCKET_NAME") {
    throw "Pass the name of your existing S3 bucket with -BucketName."
}

if (-not (Test-Path $ZipPath)) {
    throw "Deployment zip not found at $ZipPath. Build the Lambda package first."
}
$ZipPath = (Resolve-Path $ZipPath).Path

Write-Host "Uploading the deployment package to S3"
$null = Invoke-AwsCli -CliArgs @("s3", "cp", $ZipPath, "s3://$BucketName/$S3Key", "--region", $Region)

$identity = Invoke-AwsCli -CliArgs @("sts", "get-caller-identity", "--query", "Account", "--output", "text")
$accountId = $identity.Output
if (-not $accountId) {
    throw "Unable to find the AWS account ID. Run 'aws configure' first."
}

$roleArn = "arn:aws:iam::${accountId}:role/$RoleName"
Write-Host "Using the existing Lambda execution role: $roleArn"

Write-Host "Creating or updating the Lambda function in $Region"
$functionCheck = Invoke-AwsCli -CliArgs @(
    "lambda", "get-function",
    "--function-name", $FunctionName,
    "--region", $Region
) -AllowFailure
if ($functionCheck.ExitCode -ne 0) {
    if ($functionCheck.Output -notmatch "\(ResourceNotFoundException\)") {
        throw "Unable to check the Lambda function: $($functionCheck.Output)"
    }
    $null = Invoke-AwsCli -CliArgs @(
        "lambda", "create-function",
        "--function-name", $FunctionName,
        "--region", $Region,
        "--runtime", "python3.12",
        "--role", $roleArn,
        "--handler", "lambda_function.lambda_handler",
        "--code", "S3Bucket=$BucketName,S3Key=$S3Key",
        "--timeout", "120",
        "--memory-size", "512",
        "--environment", "Variables={S3_BUCKET_NAME=$BucketName}"
    )
} else {
    $null = Invoke-AwsCli -CliArgs @(
        "lambda", "update-function-code",
        "--function-name", $FunctionName,
        "--region", $Region,
        "--s3-bucket", $BucketName,
        "--s3-key", $S3Key
    )
    $null = Invoke-AwsCli -CliArgs @(
        "lambda", "update-function-configuration",
        "--function-name", $FunctionName,
        "--region", $Region,
        "--runtime", "python3.12",
        "--handler", "lambda_function.lambda_handler",
        "--role", $roleArn,
        "--timeout", "120",
        "--memory-size", "512",
        "--environment", "Variables={S3_BUCKET_NAME=$BucketName}"
    )
}

Write-Host "Deployment complete"
Write-Host "The Lambda is now configured to fetch stock data and save it to S3."
Write-Host "Next, run the invoke script to test it manually."
