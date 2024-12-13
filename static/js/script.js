const outputDiv = document.getElementById("output");

// Function to submit trip planner details
async function submitTripPlanner() {
    const location = document.getElementById("location").value.trim();
    const duration = document.getElementById("duration").value.trim();
    const budget = document.getElementById("budget").value.trim();

    if (!location || !duration || !budget) {
        outputDiv.innerHTML = `<p style="color: red;">Please fill in all fields.</p>`;
        return;
    }

    outputDiv.innerHTML = `<p>Submitting your request...</p>`;

    try {
        const response = await fetch("/generate_content", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location, duration, budget }),
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
                outputDiv.innerHTML = `
                    <h3>Trip Details</h3>
                    <pre>${JSON.stringify(result.data, null, 2)}</pre>
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
