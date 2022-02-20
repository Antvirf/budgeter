import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client('s3')


class spendItem():
    def __init__(self, amount_in, description_in):
        self.amount = amount_in
        self.description = description_in
        self.category = ""
        self.source_file = ""

    def __repr__(self):
        if self.category:
            return str("{:2f}".format(self.amount)) + " | " + self.description + " | " + self.category
        else:
            return str("{:.2f}".format(self.amount)) + " | " + self.description + " | no category assigned" 

    def get_json(self):
        return json.dumps({
            "amount": self.amount,
            "description": self.description,
            "category": self.category,
            "source_file":self.source_file
        })

def categories_load_json():
    with open('categories.json', 'r') as fp:
        categories_json = json.load(fp)
    return categories_json

def budgetfile_read_bucket(obj):
    budget = []
    for line in obj['Body'].iter_lines():
        line = line.decode('utf-8')
        if (line !='\n'):
            try:
                entry = line.split()
                entry[0] = float(entry[0])
                entry[1] = str(entry[1]).lower()    # Name
                if(len(entry)>2):
                    entry[1]=entry[1]+" "+entry[2]
                    if(len(entry)>3):
                        entry[1]=entry[1]+" "+entry[2] + " "+entry[3]
                budget.append(entry)
            except:
                logging.warning("Line skipped: " + str(line))
        # Add entry into list of entries
    return budget

def line_item_process(line, categories_dict, source_file_name=""):
    spend_item = spendItem(line[0], line[1])

    # Assign category, if exists. Otherwise, leave as "False"
    for cat in categories_dict.keys():
        if spend_item.description in categories_dict[cat]:
            spend_item.category = cat
            break
    
    # Assign source, if given
    if source_file_name:
        spend_item.source_file = source_file_name
    
    return spend_item

def summary_process(list_of_processed_spend_items):
    dict_existing_categories = {}
    list_of_no_cat_items = []

    for entry in list_of_processed_spend_items:
        if entry.category not in dict_existing_categories.keys():
            dict_existing_categories[entry.category] = entry.amount
        else:
            dict_existing_categories[entry.category] = dict_existing_categories[entry.category] + entry.amount
    
        if entry.category == "":
            list_of_no_cat_items.append(entry)

    output_string = """Weekly Spending across categories\n"""

    for key in dict_existing_categories.keys():
        key_to_show = key if key != "" else "NOT CATEGORIZED"

        output_string += str(
            key_to_show + ": " + str( "{:.2f}".format(dict_existing_categories[key])) + "\n"
            )
        
    # If food is present, give a daily
    eating_target_categories = [x for x in ["food", "unhealthy"] if x in dict_existing_categories.keys()]
    if len(eating_target_categories) >=1:
        eating_sum = 0.0
        for target_cat in eating_target_categories:
            eating_sum += dict_existing_categories[target_cat]
        eating_sum /= 7
        output_string += "\nAVG eating per day: " + str("{:.2f}".format(eating_sum)) + "\n"
    
    # Show what was not categorized
    if list_of_no_cat_items:
        output_string += "Non-categorized items: " + ", ".join([x.description for x in list_of_no_cat_items])
    return output_string

def send_queue_error(body):
    client = boto3.client('sqs')
    client.send_message(
    QueueUrl='https://sqs.ap-southeast-1.amazonaws.com/750704564056/terraform-example-queue.fifo',
    MessageBody=body,
    DelaySeconds=0,
    MessageGroupId="budgeterErrorQueue"
    )

def send_email(text_body):
    sender_address = "antti@aviitala.com"
    target_address = "antti.viitala@icloud.com"
    aws_region = "ap-southeast-1" # Singapore
    subject = "Budgeter Result"

    charset = "UTF-8"
    client = boto3.client('ses', region_name=aws_region)

    client.send_email(
    Destination = {'ToAddresses' : [target_address]},
    Message={
        'Body': {
            'Text': {
                'Charset': charset,
                'Data': text_body,
            },
        },
        'Subject': {
            'Charset': charset,
            'Data': subject,
        },
    },
    Source=sender_address,
    )

def run_on_lambda(event, context):
    # retrieve bucket name and file_key from the S3 event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    logger.info('Reading {} from {}'.format(file_key, bucket_name))
    
    # read categories
    cat = s3.get_object(Bucket=bucket_name, Key="categories.json")
    categories = json.loads(cat['Body'].read())

    # read budget file
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
    budget = budgetfile_read_bucket(obj)

    processed_line_items = []
    # Loop through each line, process each line. Add category to each item where it is missing
    for budget_line in budget:
        processed_line_items.append(
            line_item_process(budget_line, categories, file_key)
        )
    
    # Print out what we don't have a category for - to be processed. 
    for line_item in processed_line_items:
        if not line_item.category:
            logging.info("MISSING CAT: "+str(line_item))
            send_queue_error(line_item.get_json())

    # Create summary
    out = summary_process(processed_line_items)
    
    #send_email(out)
    logging.info(out)