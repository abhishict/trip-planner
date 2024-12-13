import boto3
import pymysql
import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai
import redis
import uuid

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# SQS and database details
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = int(os.getenv("RDS_PORT", 3306))
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_DB = os.getenv("RDS_DB")

# Redis details
REDIS_HOST = "trip-planner-redis-ohjbrj.serverless.use1.cache.amazonaws.com"
REDIS_PORT = 6379
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

sqs = boto3.client('sqs', region_name='us-east-1')

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

def process_message(message):
    data = json.loads(message['Body'])
    location = data['location']
    duration = data['duration']
    budget = data['budget']
    request_id = data['request_id']

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
            - Weather forecast for the duration.
            - Top restaurants and hotels in the area with ratings and average costs.
            Return the response in markdown format with headings:
            ## Itinerary, ## Best Month to Visit, ## Budget Breakdown, ## Weather Forecast, ## Restaurants, ## Hotels.
            """
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        parsed_data = parse_response(response.text.strip())

        # Insert into database
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO trip_plans (id, request_id, itinerary, best_month_to_visit, budget_breakdown) VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), request_id, parsed_data['itinerary'], parsed_data['best_month'], parsed_data['budget_breakdown'])
            )
        conn.commit()

        # Cache result in Redis
        redis_client.set(request_id, json.dumps(parsed_data), ex=3600)  # Cache for 1 hour
    except Exception as e:
        print(f"Failed to process request_id {request_id}: {e}")
    finally:
        conn.close()

def poll_sqs():
    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
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
