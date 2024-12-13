from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import boto3
import pymysql
import uuid
import json
import redis
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database connection details
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = int(os.getenv("RDS_PORT", 3306))
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_DB = os.getenv("RDS_DB")

# SQS details
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
sqs = boto3.client('sqs', region_name='us-east-1')

# Redis details
REDIS_HOST = "trip-planner-redis-ohjbrj.serverless.use1.cache.amazonaws.com"
REDIS_PORT = 6379
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True  # Decode bytes to strings automatically
)

# Function to get database connection
def get_db_connection():
    return pymysql.connect(
        host=RDS_HOST,
        port=RDS_PORT,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DB
    )

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

# Initialize the database schema
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
            cursor.execute(
                "INSERT INTO input_requests (id, location, duration, budget) VALUES (%s, %s, %s, %s)",
                (request_id, location, duration, budget)
            )
        conn.commit()

        # Send request to SQS for asynchronous processing
        if send_to_sqs(location, duration, budget, request_id):
            return jsonify({"message": "Request submitted", "request_id": request_id}), 200
        else:
            return jsonify({"error": "Failed to send message to SQS."}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/get_result/<request_id>", methods=["GET"])
def get_result(request_id):
    # Check Redis cache first
    cached_result = redis_client.get(request_id)
    if cached_result:
        print(f"Cache hit for request_id: {request_id}")
        return jsonify({"status": "completed", "data": json.loads(cached_result)}), 200

    # If not in cache, check the database
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM trip_plans WHERE request_id = %s", (request_id,))
            result = cursor.fetchone()
            if result:
                data = {
                    "itinerary": result[2],
                    "best_month_to_visit": result[3],
                    "budget_breakdown": result[4]
                }
                # Cache the result in Redis
                redis_client.set(request_id, json.dumps(data), ex=3600)  # Cache for 1 hour
                return jsonify({"status": "completed", "data": data}), 200
            else:
                print(f"No result found for request_id: {request_id}")
                return jsonify({"status": "processing"}), 200
    except Exception as e:
        print(f"Error fetching result for request_id {request_id}: {e}")
        return jsonify({"error": f"Failed to fetch result: {str(e)}"}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
