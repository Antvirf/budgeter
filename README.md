# budgeter
"Smart" expense tracking tool that assigns spending to defined categories

### Background
For several years now I have tracked every expense/spend, and I initially developed a simple script to categorize spending items on a weekly basis to different categories. These categories are created and updated with the script, so every time the aggregation is done and there is an item without a category, the user is asked to specify a category. In the future, items with that same name would go to that previously assigned category automatically.

### What this repository contains
I started working on a (semi) cloud-based version in order to understand IaaS and serverless architecture better, and this repository stores the results of that effort. I have yet to define how the initial upload process will work, but as of current the code in the repo handles the following steps:

* Terraform to create the required resources and policies: S3 bucket, Lambda, SQS queue
* Trigger event for S3 upload of any 'budget*.txt' file to start the Lambda process
* Lambda process that processes items to categories, and logs the category-level summary
* Any non-recognized items (i.e. those that need to be categorized) are sent to the created SQS queue for further processing

### Potential future developments
* UI / email endpoint to provide a way to upload data easily
* UI / email based process to assign categories to items
* Database setup (terraform + code integration) to store both the items as well as the summary
* Triggers to update summary when new caregories are provided
* Send out summary via SES
* Assign categories with ML
