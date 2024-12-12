// Select output div for displaying results
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

    outputDiv.innerHTML = `<p>Loading your trip details...</p>`;

    try {
        const response = await fetch("/generate_content", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location, duration, budget }),
        });

        const result = await response.json();

        if (response.ok) {
            outputDiv.innerHTML = `
                <h3>Trip Details</h3>
                <pre>${result.response}</pre>
            `;
        } else {
            outputDiv.innerHTML = `<p style="color: red;">Error: ${result.error}</p>`;
        }
    } catch (error) {
        outputDiv.innerHTML = `<p style="color: red;">Failed to fetch response. Please try again later.</p>`;
    }
}

// Function to clear the form and output
function clearForm() {
    document.getElementById("location").value = "";
    document.getElementById("duration").value = "";
    document.getElementById("budget").value = "";
    outputDiv.innerHTML = "";
}
