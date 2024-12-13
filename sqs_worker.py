import boto3
import json
import pymysql
import os
import google.generativeai as genai
from dotenv import load_dotenv
import re
import uuid
import boto3
from fpdf import FPDF

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# SQS and Database details
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = int(os.getenv("RDS_PORT", 3306))
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_DB = os.getenv("RDS_DB")

sqs = boto3.client('sqs', region_name='us-east-1')

S3_BUCKET_NAME = "trip-planner-responses"
s3_client = boto3.client('s3', region_name='us-east-1')  # Change region if needed


# Function to get database connection
def get_db_connection():
    return pymysql.connect(
        host=RDS_HOST,
        port=RDS_PORT,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DB
    )

def parse_response(response):
    try:
        # Parse Itinerary
        itinerary_match = re.search(r"## Itinerary\n([\s\S]*?)\n##", response)
        itinerary = itinerary_match.group(1).strip() if itinerary_match else "Itinerary not found"

        # Parse Best Month to Visit
        best_month_match = re.search(r"## Best Month to Visit\n([\s\S]*?)\n##", response)
        best_month = best_month_match.group(1).strip() if best_month_match else "Best month not found"

        # Parse Budget Breakdown
        budget_breakdown_match = re.search(r"## Budget Breakdown\n([\s\S]*?)\n##", response)
        budget_breakdown = budget_breakdown_match.group(1).strip() if budget_breakdown_match else "Budget breakdown not found"

        # Parse Weather Forecast
        weather_forecast_match = re.search(r"## Weather Forecast\n([\s\S]*?)\n##", response)
        weather_forecast = weather_forecast_match.group(1).strip() if weather_forecast_match else "Weather forecast not found"

        # Parse Restaurants
        restaurants_match = re.search(r"## Restaurants\n([\s\S]*?)\n## Hotels", response)
        restaurants = restaurants_match.group(1).strip() if restaurants_match else "Restaurants not found"

        # Parse Hotels
        hotels_match = re.search(r"## Hotels\n([\s\S]*?)$", response)
        hotels = hotels_match.group(1).strip() if hotels_match else "Hotels not found"

        return {
            "itinerary": itinerary,
            "best_month": best_month,
            "budget_breakdown": budget_breakdown,
            "weather": weather_forecast,
            "restaurants": restaurants,
            "hotels": hotels
        }
    except Exception as e:
        raise ValueError(f"Failed to parse response: {str(e)}")

from fpdf import FPDF

def generate_pdf(data, file_name):
    """
    Generate a PDF from plain text data and save it locally.

    Parameters:
    - data (str): The plain text content to be written to the PDF.
    - file_name (str): The name of the PDF file to save.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Trip Planner Response", ln=True, align="C")
    
    # Add response content
    pdf.ln(10)  # Add a blank line for spacing
    pdf.multi_cell(0, 10, data)  # Add the plain text content
    
    # Save PDF locally
    pdf.output(file_name)

def upload_to_s3(file_name, s3_key):
    try:
        s3_client.upload_file(file_name, S3_BUCKET_NAME, s3_key)
        print(f"Uploaded {file_name} to S3 bucket {S3_BUCKET_NAME} with key {s3_key}")
        return True
    except Exception as e:
        print(f"Failed to upload {file_name} to S3: {e}")
        return False

def process_message(message):
    data = json.loads(message['Body'])
    location = data['location']
    duration = data['duration']
    budget = data['budget']
    fromDate = data['fromDate']
    toDate = data['toDate']
    request_id = data['request_id']

    print(f"Processing message for request_id: {request_id}")

    conn = get_db_connection()
    try:
        # Generate AI response
        prompt = f"""
            You are an expert Tour Planner. Create a detailed travel plan for the following:
            - Location: {location}
            - Duration: {duration} days
            - Budget: ${budget}
            Include:
            - Daily itinerary with activities and accommodations.
            - Best month to visit.
            - Budget breakdown (accommodation, food, travel, activities).
            - Weather forecast from {fromDate} to {toDate}. 
            - Top restaurants and hotels in the area with ratings and average costs.
            Return the response in markdown format with headings:
            ## Itinerary, ## Best Month to Visit, ## Budget Breakdown, ## Weather Forecast, ## Restaurants, ## Hotels.
            """
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        processed_response = response.text.strip().replace("*", "")
        parsed_data = parse_response(processed_response)
        
        print("Parsed Data:", parsed_data)
        # Insert into database
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO trip_plans (id, request_id, itinerary, best_month_to_visit, budget_breakdown, restaurants, hotels, weather) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), request_id, parsed_data['itinerary'], 
                parsed_data['best_month'], parsed_data['budget_breakdown'],
                parsed_data['restaurants'], parsed_data['hotels'], parsed_data['weather']),
            )
        conn.commit()

        # Generate and upload PDF
        pdf_file_name = f"trip_plan_{request_id}.pdf"
        generate_pdf(processed_response, pdf_file_name)
        s3_key = f"trip_plans/{pdf_file_name}"
        upload_to_s3(pdf_file_name, s3_key)

        # Remove local file after upload
        if os.path.exists(pdf_file_name):
            os.remove(pdf_file_name)

    except Exception as e:
        print(f"Failed to process request_id {request_id}: {e}")
    finally:
        conn.close()

# Function to poll SQS for messages
def poll_sqs():
    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )

        messages = response.get('Messages', [])
        for message in messages:
            process_message(message)
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )

if __name__ == "__main__":
    poll_sqs()