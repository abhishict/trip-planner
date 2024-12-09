from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import google.generativeai as genai
from PIL import Image
import base64
import io
import awsgi

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)

def get_response_image(image, prompt):
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([image, prompt])
    return response.text

def get_response(prompt, user_input):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt, user_input])
    return response.text

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/location_finder", methods=["POST"])
def location_finder():
    data = request.json
    if "image" not in data:
        return jsonify({"error": "Image is required!"}), 400

    image_data = base64.b64decode(data["image"])
    prompt = """
    You are an expert Tourist Guide. Provide a summary about the place:
    - Location of the place
    - State & Capital
    - Coordinates
    - Popular places nearby
    Return the response using markdown.
    """
    try:
        response = get_response_image(image_data, prompt)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/trip_planner", methods=["POST"])
def trip_planner():
    data = request.json
    location_days = data.get("input")
    budget = data.get("budget", "Not provided")
    prompt = f"""
    You are an expert Tour Planner. Plan an itinerary for the given location:
    {location_days}. Budget: ${budget}
    - Daily itinerary with hidden spots, hotels, and beautiful places.
    - Best month to visit the location.
    - Budget allocation: accommodation, food, travel, and activities.
    Return the response in markdown.
    """
    try:
        response = get_response(prompt, location_days)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/weather_forecasting", methods=["POST"])
def weather_forecasting():
    data = request.json
    location = data.get("location", "")
    prompt = """
    You are an expert weather forecaster. Provide a 7-day forecast for the location:
    - Precipitation, Snow, Humidity, Wind, Air Quality, Cloud Cover.
    Return the response as a markdown table.
    """
    try:
        response = get_response(prompt, location)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/restaurant_hotel_planner", methods=["POST"])
def restaurant_hotel_planner():
    data = request.json
    location = data.get("location", "")
    prompt = """
    You are an expert Restaurant & Hotel Planner. Provide recommendations for:
    - Top 5 restaurants with ratings, address, and average cost.
    - Top 5 hotels with ratings, address, and average cost per night.
    Ensure the options are neither too expensive nor too cheap.
    Return the response using markdown.
    """
    try:
        response = get_response(prompt, location)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
