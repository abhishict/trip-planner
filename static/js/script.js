const outputDiv = document.getElementById("output");

// Function to submit trip planner details
async function submitTripPlanner() {
    const location = document.getElementById("location").value.trim();
    const fromDateElement = document.getElementById("from-date").value;
    const toDateElement = document.getElementById("to-date").value;
    const budget = document.getElementById("budget").value.trim();

    // Ensure all fields are filled
    if (!location || !fromDateElement || !toDateElement || !budget) {
        outputDiv.innerHTML = `<p style="color: red;">Please fill in all fields.</p>`;
        return;
    }

    // Calculate duration in days
    const fromDateObj = new Date(fromDateElement);
    const toDateObj = new Date(toDateElement);
    const duration = Math.ceil((toDateObj - fromDateObj) / (1000 * 60 * 60 * 24)).toString();

    const fromDate = fromDateObj.toDateString();
    const toDate = toDateObj.toDateString();

    if (duration <= 0) {
        outputDiv.innerHTML = `<p style="color: red;">To Date must be after From Date.</p>`;
        return;
    }

    outputDiv.innerHTML = `<p>Submitting your request...</p>`;

    try {
        const response = await fetch("/generate_content", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({location, duration, budget, fromDate, toDate}),
        });

        const result = await response.json();

        if (response.ok) {
            const requestId = result.request_id;
            outputDiv.innerHTML = `<p>Request submitted successfully! Processing your trip details. Please wait...</p>`;
            await pollForResult(requestId);
        } else {
            outputDiv.innerHTML = `<p style="color: red;">Error: ${result.error}</p>`;
        }
    } catch (error) {
        outputDiv.innerHTML = `<p style="color: red;">Failed to submit request. Please try again later.</p>`;
    }
}


// Function to poll for results
async function pollForResult(requestId) {
    const pollInterval = 5000; // Poll every 5 seconds
    const timeout = 300000; // Stop polling after 5 minutes
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
        try {
            const response = await fetch(`/get_result/${requestId}`, { method: "GET" });
            const result = await response.json();

            if (response.ok && result.status === "completed") {
                // Create HTML structure for trip details
                const data = result.data;
                const pdfUrl = result.pdf_url;

                outputDiv.innerHTML = `
                    <h3>Trip Details</h3>
                    <div class="trip-detail-section">
                        <h4>Itinerary</h4>
                        <p>${data.itinerary.replace(/\n/g, "<br>")}</p>
                    </div>
                    <div class="trip-detail-section">
                        <h4>Best Month to Visit</h4>
                        <p>${data.best_month_to_visit}</p>
                        <p>${data.weather}</p>
                    </div>
                    <div class="trip-detail-section">
                        <h4>Budget Breakdown</h4>
                        <p>${data.budget_breakdown.replace(/\n/g, "<br>")}</p>
                    </div>
                    <div class="trip-detail-section">
                        <h4>Restaurants</h4>
                        <ul>${data.restaurants
                            .split("\n")
                            .map((item) => `<li>${item}</li>`)
                            .join("")}</ul>
                    </div>
                    <div class="trip-detail-section">
                        <h4>Hotels</h4>
                        <ul>${data.hotels
                            .split("\n")
                            .map((item) => `<li>${item}</li>`)
                            .join("")}</ul>
                    </div>
                    <a href="${result.pdf_url}" class="download-link" target="_blank">Download PDF</a>
                `;
                return;
            } else if (result.status === "processing") {
                outputDiv.innerHTML = `<p>Processing your request. Please wait...</p>`;
            } else {
                outputDiv.innerHTML = `<p style="color: red;">Unexpected status: ${result.status}</p>`;
                return;
            }
        } catch (error) {
            outputDiv.innerHTML = `<p style="color: red;">Error: ${error.message}. Retrying...</p>`;
        }

        await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    outputDiv.innerHTML = `<p style="color: red;">Request timed out. Please try again later.</p>`;
}

// Function to clear the form and output
function clearForm() {
    document.getElementById("location").value = "";
    document.getElementById("duration").value = "";
    document.getElementById("budget").value = "";
    outputDiv.innerHTML = "";
}