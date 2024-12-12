import boto3
import json
import pymysql
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
import uuid

# Load environment variables
load_dotenv()

# Database connection details
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = int(os.getenv("RDS_PORT", 3306))
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_DB = os.getenv("RDS_DB")

# SQS details
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
sqs = boto3.client('sqs', region_name='us-east-1')

# Function to get database connection
def get_db_connection():
    try:
        conn = pymysql.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB
        )
        return conn
    except Exception as e:
        print(f"Error connecting to RDS MySQL: {e}")
        return None
    
def get_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text.strip() if response else "No response generated."
    except Exception as e:
        raise RuntimeError(f"Error generating response: {str(e)}")

# Function to parse AI response
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
        restaurants = []
        restaurants_match = re.search(r"## Restaurants\n([\s\S]*?)\n## Hotels", response)
        if restaurants_match:
            restaurants_text = restaurants_match.group(1).strip()
            restaurant_lines = restaurants_text.split("\n")
            for line in restaurant_lines:
                match = re.match(r"\*\*\s*(.*?)\s*:", line)
                if match:
                    name = match.group(1).strip()
                    restaurants.append(name)

        # Parse Hotels
        hotels = []
        hotels_match = re.search(r"## Hotels\n([\s\S]*?)$", response)
        if hotels_match:
            hotels_text = hotels_match.group(1).strip()
            hotel_lines = hotels_text.split("\n")
            for line in hotel_lines:
                match = re.match(r"\*\*\s*(.*?)\s*:", line)
                if match:
                    name = match.group(1).strip()
                    hotels.append(name)

        return {
            "itinerary": itinerary,
            "best_month": best_month,
            "budget_breakdown": budget_breakdown,
            "weather_forecast": weather_forecast,
            "restaurants": restaurants,
            "hotels": hotels
        }
    except Exception as e:
        raise ValueError(f"Failed to parse response: {str(e)}")

# Function to process messages from SQS
def process_sqs_messages():
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10  # Long polling
            )
            if 'Messages' in response:
                for message in response['Messages']:
                    message_body = json.loads(message['Body'])
                    print(f"Processing message: {message_body}")

                    # Extract details
                    request_id = message_body['request_id']
                    location = message_body['location']
                    duration = message_body['duration']
                    budget = message_body['budget']

                    # Simulate generating a response
                    prompt = f"""
                    You are an expert Tour Planner. Create a detailed travel plan for the following:
                    - Location: {location}
                    - Duration: {duration} days
                    - Budget: ${budget}
                    Include:
                    - Daily itinerary with activities and accommodations.
                    - Best month to visit.
                    - Budget breakdown (accommodation, food, travel, activities).
                    - Weather forecast for the duration.
                    - Top restaurants and hotels in the area with ratings and average costs.
                    Return the response in markdown format with headings:
                    ## Itinerary, ## Best Month to Visit, ## Budget Breakdown, ## Weather Forecast, ## Restaurants, ## Hotels.
                    """
                    generated_response = get_response(prompt)
                    # Parse and save the response
                    parsed_data = parse_response(generated_response)
                    store_response(request_id, parsed_data)

                    # Delete the message from the queue
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print(f"Message processed and deleted: {request_id}")
            else:
                print("No messages in queue. Waiting...")
        except Exception as e:
            print(f"Error processing messages: {e}")

# Function to store response in database
def store_response(request_id, parsed_data):
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return
    try:
        with conn.cursor() as cursor:
            # Store itinerary details
            cursor.execute(
                "INSERT INTO trip_plans (id, request_id, itinerary, best_month_to_visit, budget_breakdown) VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), request_id, parsed_data['itinerary'], parsed_data['best_month'], parsed_data['budget_breakdown'])
            )
            # Store restaurants
            for restaurant in parsed_data['restaurants']:
                cursor.execute(
                    "INSERT INTO restaurants (id, request_id, name) VALUES (%s, %s, %s)",
                    (str(uuid.uuid4()), request_id, restaurant)
                )
            # Store hotels
            for hotel in parsed_data['hotels']:
                cursor.execute(
                    "INSERT INTO hotels (id, request_id, name) VALUES (%s, %s, %s)",
                    (str(uuid.uuid4()), request_id, hotel)
                )
        conn.commit()
        print(f"Response stored for request ID: {request_id}")
    except Exception as e:
        print(f"Error storing response: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting SQS worker...")
    process_sqs_messages()
