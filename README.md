Here’s a comprehensive **README** file for your project:

---

# Dynamic Trip Itinerary Planner

## Overview
The **Dynamic Trip Itinerary Planner** is a Flask-based web application that leverages AI and cloud technologies to create personalized travel itineraries. Users can input trip details such as destination, travel dates, and budget to generate tailored plans that include activities, accommodations, weather updates, and a detailed budget breakdown. The application outputs the results on an interactive web interface and provides downloadable PDFs.

---

## Features
- **User-Friendly Web Interface**: Intuitive form-based UI for submitting trip details.
- **AI-Generated Itineraries**: Uses Google Generative AI to create customized trip plans.
- **Secure Cloud Infrastructure**: Leverages AWS services like SQS, RDS, and S3 for scalability and reliability.
- **PDF Generation**: Automatically generates a downloadable PDF of the itinerary.
- **API Endpoints**: Provides RESTful API for programmatic interaction.
- **Containerization**: Fully Dockerized for seamless deployment on Amazon ECS.

---

## Architecture
1. **User Interaction**: Users input trip details via the web application or REST API.
2. **Data Queuing**: Requests are queued in Amazon SQS for asynchronous processing.
3. **Worker Service**: Processes requests, generates itineraries using AI, stores results in Amazon RDS, and uploads PDFs to Amazon S3.
4. **Result Retrieval**: Users can view trip details on the web application or download the PDF.
5. **Containerization**: Application components are containerized with Docker and deployed using Amazon ECS.

---

## Tech Stack
### **Frontend**
- HTML, CSS, JavaScript (Flask templates)

### **Backend**
- Flask (Python) for API and web application
- fpdf for PDF generation

### **Cloud Services**
- **Amazon SQS**: Asynchronous request queuing
- **Amazon RDS**: Relational database for structured data storage
- **Amazon S3**: Secure storage for generated PDFs
- **Amazon ECR**: Container image registry for deployment
- **Amazon ECS**: Cluster-based container orchestration

### **Other Tools**
- Docker: Containerization
- boto3: AWS SDK for Python
- pymysql: MySQL connectivity
- Flask-CORS: Enable cross-origin resource sharing
- dotenv: Environment variable management

---

## Setup Instructions

### Prerequisites
1. Python 3.12+ installed on your machine.
2. Docker and Docker Compose installed.
3. AWS CLI configured with necessary permissions.

### Steps
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Build Docker images:
   ```bash
   docker-compose build
   ```

4. Start the application:
   ```bash
   docker-compose up -d
   ```

5. Access the application:
   - Open the browser and navigate to `http://<ec2-public-ip>:5000`.

---

## Usage

1. Input your trip details (destination, dates, and budget) in the web form.
2. Submit the request and wait for processing.
3. View your generated trip itinerary on the webpage or download the PDF.

---

## Debugging and Testing

1. **Flask Debug Mode**: Enabled during development for runtime error tracking.
2. **Docker Logs**: Monitor container logs for debugging.
3. **AWS CloudWatch Logs**: Analyze logs for SQS and worker services.
4. **Testing**: Simulated high-traffic scenarios to evaluate performance.

---

## Potential Enhancements
- **Caching Mechanisms**: Reduce latency by caching frequently accessed results.
- **Real-Time Updates**: Enable dynamic itinerary adjustments.
- **Advanced Algorithms**: Implement optimization techniques for itinerary planning.

---

## Contributors
- **Your Name(s)**

---

## License
This project is licensed under the MIT License. See `LICENSE` for more details.

---

## Acknowledgments
Special thanks to the contributors, instructors, and the OpenAI & AWS communities for their guidance and resources.

--- 
