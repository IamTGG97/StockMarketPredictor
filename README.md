# StockMarketPredictor

A Flask dashboard that fetches historical stock prices, displays a simple forecast, and stores market data in S3. The repository also contains a scheduled AWS ingestion pipeline for the S&P 500.

## What is implemented

- Flask dashboard and `/api/stock_data` endpoint.
- Yahoo Finance history fetching, with a chart API fallback.
- Explainable linear-trend forecast baseline.
- S3 storage of raw JSON and processed CSV market data.
- Lambda dispatcher that looks up S&P 500 constituents and sends one message per ticker to SQS.
- Lambda worker that fetches one ticker per SQS message and writes its data to S3.
- CloudFormation stack for the SQS work queue and dead-letter queue, the two Lambdas, least-privilege execution roles, and the weekday schedule.

## Deploy the AWS ingestion stack

### Prerequisites

- AWS CLI installed and configured with credentials for the target AWS account.
- Deployment credentials permitted to upload the package, create/update the CloudFormation stack, and create/pass the stack's IAM roles.
- An existing S3 bucket in the target region. The deployment package and collected data use this bucket.
- Docker Desktop, for building native dependencies in the Lambda-compatible Linux environment.

Build the dependency directory:

```powershell
.\scripts\build_lambda_dependencies.ps1
```

Deploy the stack with the schedule **disabled** first:

```powershell
.\scripts\deploy_ingestion.ps1 -BucketName YOUR_EXISTING_BUCKET
```

The script packages both handlers, uploads the package to S3 under a unique key, and deploys `infrastructure/stock-ingestion.yaml`. The artifact bucket must be in the same AWS region as the Lambda functions. CloudFormation creates:

1. An encrypted SQS work queue and a dead-letter queue. Messages are retried up to three receives before moving to the DLQ.
2. A dispatcher Lambda with permission to send jobs to the work queue.
3. A worker Lambda with permission to consume the queue and write only to the `raw/` and `processed/` prefixes of the configured bucket.
4. An SQS event source mapping with batch size one and a maximum concurrency of five workers.
5. An EventBridge Scheduler schedule for 5:00 PM on weekdays in `America/New_York`.

The schedule defaults to `DISABLED` so you can inspect the stack and test ingestion manually before it starts running automatically. First send a single test job to the work queue using the `WorkQueueUrl` output:

```powershell
$testPayloadPath = Join-Path $env:TEMP "stock-ingestion-test.json"
$testMessage = @{
    symbol = "AAPL"
    start_date = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")
    end_date = (Get-Date).ToString("yyyy-MM-dd")
} | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText(
    $testPayloadPath,
    $testMessage,
    (New-Object System.Text.UTF8Encoding($false))
)

aws sqs send-message `
    --queue-url "<WorkQueueUrl>" `
    --message-body "file://$testPayloadPath" `
    --region us-east-2
Remove-Item -LiteralPath $testPayloadPath
```

The worker Lambda is triggered by SQS; do not invoke it directly with a plain symbol payload. Once the single-ticker test writes objects to S3, you can invoke the dispatcher manually to enqueue the S&P 500:

```powershell
aws lambda invoke `
    --function-name stock-market-ingestion-dispatcher `
    --region us-east-2 `
    --cli-binary-format raw-in-base64-out `
    --payload '{}' `
    dispatcher-response.json
Get-Content .\dispatcher-response.json
Remove-Item .\dispatcher-response.json
```

Replace the example queue URL, region, or function name if you used different deployment parameters. Check CloudWatch logs and the `DeadLetterQueueUrl` output before enabling the recurring schedule:

```powershell
.\scripts\deploy_ingestion.ps1 -BucketName YOUR_EXISTING_BUCKET -ScheduleState ENABLED
```

The schedule follows Eastern daylight/standard time. It runs on weekdays, including market holidays; the stock-data provider may return no data on those dates, and such messages can eventually be sent to the DLQ. The worker role grants writes to the configured S3 prefixes; if the bucket enforces a customer-managed KMS key, grant the worker role the required KMS permissions as well.

### Updating or removing the stack

Run the same deployment command again to update the stack. Each run uploads the deployment package to a new S3 object key so CloudFormation can detect code updates. Removing the CloudFormation stack deletes the queue, Lambdas, schedule, and roles; the existing S3 bucket is not managed by the stack and is not deleted.

AWS usage can incur charges for Lambda, SQS, S3, CloudWatch Logs, and EventBridge Scheduler. Review the AWS cost details for your account before enabling the schedule.

## Local development and tests

Install the application dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the Flask application:

```powershell
python app.py
```

Run the tests:

```powershell
python -m unittest discover -s tests
```

## Current limitations and possible next work

- The Flask dashboard is a local/demo app; hosting it publicly and adding API Gateway are separate deployment tasks.
- The forecast is a simple linear trend baseline, not investment advice or a validated trading model.
- News sentiment is currently marked unavailable in the API response.
- S&P 500 constituents are fetched from Wikipedia at dispatcher runtime, so the dispatcher needs outbound internet access and depends on that source being available.
