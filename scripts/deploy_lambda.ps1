param(
    [string]$FunctionName = "stock-ingest-lambda",
    [string]$RoleName = "stock-predictor-lambda-role",
    [string]$BucketName = "",
    [string]$Region = "us-east-2",
    [string]$ZipPath = (Join-Path $PSScriptRoot "..\lambda-deployment.zip")
)

$ErrorActionPreference = "Stop"

if (-not $BucketName -or $BucketName -eq "YOUR_S3_BUCKET_NAME") {
    throw "Pass the name of your existing S3 bucket with -BucketName."
}

if (-not (Test-Path $ZipPath)) {
    throw "Deployment zip not found at $ZipPath. Build the Lambda package first."
}
$ZipPath = (Resolve-Path $ZipPath).Path

$accountId = (aws sts get-caller-identity --query Account --output text)
if (-not $accountId) {
    throw "Unable to find the AWS account ID. Run 'aws configure' first."
}

Write-Host "Step 1: create Lambda execution role if it does not already exist"
$roleExists = aws iam get-role --role-name $RoleName 2>$null
if ($LASTEXITCODE -ne 0) {
    aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' | Out-Null
}

Write-Host "Step 2: attach the basic execution policy and S3 access"
aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole | Out-Null
$fullS3AccessArn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
$attachedPolicies = aws iam list-attached-role-policies --role-name $RoleName --query "AttachedPolicies[?PolicyArn=='$fullS3AccessArn'].PolicyArn" --output text
if ($LASTEXITCODE -ne 0) {
    throw "Unable to check the role's attached policies."
}
if ($attachedPolicies -and $attachedPolicies -ne "None") {
    aws iam detach-role-policy --role-name $RoleName --policy-arn $fullS3AccessArn | Out-Null
}
$s3WritePolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = @("s3:PutObject")
            Resource = "arn:aws:s3:::$BucketName/*"
        }
    )
} | ConvertTo-Json -Depth 5 -Compress
aws iam put-role-policy `
    --role-name $RoleName `
    --policy-name "stock-predictor-s3-write" `
    --policy-document $s3WritePolicy | Out-Null

$roleArn = aws iam get-role --role-name $RoleName --query 'Role.Arn' --output text

Write-Host "Step 3: create or update the Lambda function"
$functionArn = aws lambda get-function --function-name $FunctionName 2>$null
if ($LASTEXITCODE -ne 0) {
    aws lambda create-function `
        --function-name $FunctionName `
        --runtime python3.12 `
        --role $roleArn `
        --handler lambda_function.lambda_handler `
        --zip-file fileb://$ZipPath `
        --timeout 120 `
        --memory-size 512 `
        --environment "Variables={S3_BUCKET_NAME=$BucketName,AWS_REGION=$Region}" | Out-Null
} else {
    aws lambda update-function-code --function-name $FunctionName --zip-file fileb://$ZipPath | Out-Null
    aws lambda update-function-configuration `
        --function-name $FunctionName `
        --runtime python3.12 `
        --handler lambda_function.lambda_handler `
        --role $roleArn `
        --timeout 120 `
        --memory-size 512 `
        --environment "Variables={S3_BUCKET_NAME=$BucketName,AWS_REGION=$Region}" | Out-Null
}

Write-Host "Step 4: this is the first real AWS milestone"
Write-Host "The Lambda is now configured to fetch stock data and save it to S3."
Write-Host "Next, run the invoke script to test it manually."
