locals {
  lambda_zip_location = "outputs/budgeter.zip"
}

# Creating an SQS queue
resource "aws_sqs_queue" "terraform_queue" {
  name                        = "errorqueue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

# Create url file
resource "local_file" "queue_url_file" {
    content     = "${aws_sqs_queue.terraform_queue.url}"
    filename = "${path.module}/lambdasetup/queue_url.txt"
    depends_on = [
      aws_sqs_queue.terraform_queue
    ]
}

# Create the zip file to upload to Lambda
data "archive_file" "budgeter" {
  type = "zip"
  source_dir = "${path.module}/lambdasetup/"
  #source_file = "run_budget_cloud.py"
  output_path = local.lambda_zip_location
  depends_on = [
    aws_sqs_queue.terraform_queue,
    local_file.queue_url_file,
  ]
}

# Allow execution of A lambda from S3 bucket
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.budgetfunc.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.bucket.arn
}

# Create lambda function
resource "aws_lambda_function" "budgetfunc" {
  filename         = local.lambda_zip_location
  function_name    = "run_on_lambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "run_budget_cloud.run_on_lambda"
  source_code_hash = filebase64sha256(local.lambda_zip_location)
  runtime          = "python3.8"
}

# Create the bucket
resource "aws_s3_bucket" "bucket" {
  bucket        = "budgeterstorage"
  force_destroy = true # To allow clean deletion later
  lifecycle {
    prevent_destroy = false # To allow clean deletion later
  }
}

# Uploading 'categories.json' to s3 bucket to set up the app
resource "aws_s3_object" "file_upload" {
  bucket = "budgeterstorage"
  key    = "categories.json"
  source = "categories.json"
  etag   = filemd5("categories.json")
  depends_on = [
    aws_s3_bucket.bucket
  ]
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.budgetfunc.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "budget"
    filter_suffix       = ".txt"
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}



# Outputs
output "errorqueue_url" {
  value = aws_sqs_queue.terraform_queue.url
  description = "Error queue URL"
}
