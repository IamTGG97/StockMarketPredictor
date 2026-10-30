param(
    [Parameter(Mandatory = $true)]
    [string]$BucketName,
    [string]$Region = "us-east-2",
    [string]$StackName = "stock-market-ingestion",
    [ValidateSet("ENABLED", "DISABLED")]
    [string]$ScheduleState = "ENABLED",
    [string]$BuildDirectory = (Join-Path $PSScriptRoot "..\.lambda-build"),
    [string]$ZipPath = (Join-Path $PSScriptRoot "..\lambda-deployment.zip")
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI was not found. Install it and configure credentials before deploying."
}
if (-not $BucketName.Trim()) {
    throw "Pass the name of an existing S3 bucket with -BucketName."
}

$ZipPath = [System.IO.Path]::GetFullPath($ZipPath)
$BuildDirectory = [System.IO.Path]::GetFullPath($BuildDirectory)
$TemplatePath = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\infrastructure\stock-ingestion.yaml")
)
$PackageScript = Join-Path $PSScriptRoot "package_lambda.ps1"

Write-Host "Step 1: package Lambda handlers, the API app, assets, and dependencies"
& $PackageScript -BuildDirectory $BuildDirectory -OutputPath $ZipPath
if (-not (Test-Path -LiteralPath $ZipPath)) {
    throw "Lambda package was not created at $ZipPath."
}

$artifactKey = "lambda-deployments/stock-ingestion-$([guid]::NewGuid().ToString('N')).zip"
Write-Host "Step 2: upload the package to s3://$BucketName/$artifactKey"
& aws s3 cp $ZipPath "s3://$BucketName/$artifactKey" --region $Region --only-show-errors
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload the Lambda package to S3 (exit code $LASTEXITCODE)."
}

Write-Host "Step 3: deploy CloudFormation stack '$StackName' in $Region"
& aws cloudformation deploy `
    --stack-name $StackName `
    --template-file $TemplatePath `
    --region $Region `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides `
        "ArtifactBucket=$BucketName" `
        "ArtifactKey=$artifactKey" `
        "DataBucketName=$BucketName" `
        "ScheduleState=$ScheduleState"
if ($LASTEXITCODE -ne 0) {
    throw "CloudFormation deployment failed (exit code $LASTEXITCODE). Check the stack events in AWS."
}

Write-Host "Step 4: review the deployed stack outputs"
& aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --query "Stacks[0].Outputs" `
    --output table
if ($LASTEXITCODE -ne 0) {
    throw "The stack deployed, but its outputs could not be retrieved (exit code $LASTEXITCODE)."
}

Write-Host "Deployment complete. Schedule state: $ScheduleState"
Write-Host "Verify the stack outputs and CloudWatch logs."
