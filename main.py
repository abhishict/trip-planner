from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import google.generativeai as genai
import pymysql  # For connecting to MySQL
import boto3  # For interacting with AWS SQS
import re
import uuid
import json
from flask_cors import CORS

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)
CORS(app)

# Database connection details
RDS_HOST = os.getenv("RDS_HOST")  # RDS endpoint
RDS_PORT = int(os.getenv("RDS_PORT", 3306))  # Default MySQL port
RDS_USER = os.getenv("RDS_USER")  # Database username
RDS_PASSWORD = os.getenv("RDS_PASSWORD")  # Database password
RDS_DB = os.getenv("RDS_DB")  # Database name

# SQS details
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")  # SQS Queue URL
sqs = boto3.client('sqs', region_name='us-east-1')  # Initialize SQS client

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

# Function to send messages to SQS
def send_to_sqs(location, duration, budget, request_id):
    message_body = {
        "location": location,
        "duration": duration,
        "budget": budget,
        "request_id": request_id
    }
    try:
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        print(f"Message sent to SQS: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Failed to send message to SQS: {e}")
        return False

# Function to initialize database schema
def init_db():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Create input_requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS input_requests (
                id VARCHAR(255) PRIMARY KEY,
                location TEXT NOT NULL,
                duration INT NOT NULL,
                budget FLOAT NOT NULL
            )
        """)
        # Create trip_plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trip_plans (
                id VARCHAR(255) PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                itinerary TEXT NOT NULL,
                best_month_to_visit TEXT NOT NULL,
                budget_breakdown TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES input_requests (id)
            )
        """)
        # Create weather table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id VARCHAR(255) PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                forecast TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES input_requests (id)
            )
        """)
        # Create restaurants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id VARCHAR(255) PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES input_requests (id)
            )
        """)
        # Create hotels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotels (
                id VARCHAR(255) PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES input_requests (id)
            )
        """)
    conn.commit()
    conn.close()

# Call this function once at the start of your application
init_db()

# Utility to generate response using Generative AI
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

# Flask routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate_content", methods=["POST"])
def generate_content():
    data = request.json
    location = data.get("location", "").strip()
    duration = data.get("duration", "").strip()
    budget = data.get("budget", "").strip()

    if not location or not duration or not budget:
        return jsonify({"error": "All fields (location, duration, budget) are required!"}), 400

    request_id = str(uuid.uuid4())

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Failed to connect to the database."}), 500

    try:
        with conn.cursor() as cursor:
            # Save input request
            cursor.execute(
                "INSERT INTO input_requests (id, location, duration, budget) VALUES (%s, %s, %s, %s)",
                (request_id, location, duration, budget)
            )
            print("Inserted input_request:", request_id)

        conn.commit()

        # Send request to SQS for asynchronous processing
        if send_to_sqs(location, duration, budget, request_id):
            return jsonify({"message": "Your request has been submitted for processing."}), 200
        else:
            return jsonify({"error": "Failed to send message to SQS."}), 500

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return jsonify({"error": f"Failed to generate content: {str(e)}"}), 500

    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
