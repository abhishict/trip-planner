const formContainer = document.getElementById("form-container");
const outputDiv = document.getElementById("output");

function loadSection() {
    const section = document.getElementById("section").value;
    formContainer.innerHTML = "";
    outputDiv.innerHTML = "";

    if (section === "location_finder") {
        formContainer.innerHTML = `
            <input type="file" id="image" accept="image/*">
            <button onclick="submitLocationFinder()">Get Location</button>
        `;
    } else if (section === "trip_planner") {
        formContainer.innerHTML = `
            <textarea id="trip-input" placeholder="Enter location and days"></textarea>
            <input type="number" id="budget" placeholder="Enter budget" min="0">
            <button onclick="submitTripPlanner()">Plan My Trip</button>
        `;
    } else if (section === "weather_forecasting") {
        formContainer.innerHTML = `
            <textarea id="location" placeholder="Enter location"></textarea>
            <button onclick="submitWeatherForecast()">Forecast Weather</button>
        `;
    } else if (section === "restaurant_hotel_planner") {
        formContainer.innerHTML = `
            <textarea id="restaurant-hotel-location" placeholder="Enter location"></textarea>
            <button onclick="submitRestaurantHotel()">Find Restaurants & Hotels</button>
        `;
    }
}

async function submitLocationFinder() {
    const imageInput = document.getElementById("image").files[0];
    if (!imageInput) {
        outputDiv.innerText = "Please upload an image.";
        return;
    }
    const reader = new FileReader();
    reader.onload = async function () {
        const base64Image = reader.result.split(",")[1];
        try {
            const response = await fetch("/location_finder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: base64Image }),
            });
            const result = await response.json();
            outputDiv.innerText = result.response || `Error: ${result.error}`;
        } catch (error) {
            outputDiv.innerText = "Failed to fetch response.";
        }
    };
    reader.readAsDataURL(imageInput);
}

// Other functions (submitTripPlanner, submitWeatherForecast, submitRestaurantHotel) are similar to Streamlit logic.
async function submitTripPlanner() {
    const locationDays = document.getElementById("trip-input").value;
    const budget = document.getElementById("budget").value;

    if (!locationDays) {
        outputDiv.innerText = "Please enter a location and days.";
        return;
    }

    try {
        const response = await fetch("/trip_planner", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input: locationDays, budget }),
        });
        const result = await response.json();
        if (response.ok) {
            outputDiv.innerHTML = `<pre>${result.response}</pre>`;
        } else {
            outputDiv.innerHTML = `Error: ${result.error}`;
        }
    } catch (error) {
        outputDiv.innerHTML = "Failed to fetch response from the server.";
    }
}

async function submitWeatherForecast() {
    const location = document.getElementById("location").value;

    if (!location) {
        outputDiv.innerText = "Please enter a location.";
        return;
    }

    try {
        const response = await fetch("/weather_forecasting", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location }),
        });
        const result = await response.json();
        if (response.ok) {
            outputDiv.innerHTML = `<pre>${result.response}</pre>`;
        } else {
            outputDiv.innerHTML = `Error: ${result.error}`;
        }
    } catch (error) {
        outputDiv.innerHTML = "Failed to fetch response from the server.";
    }
}

async function submitRestaurantHotel() {
    const locationInput = document.getElementById("restaurant-hotel-location").value;

    if (!locationInput) {
        outputDiv.innerText = "Please enter a location.";
        return;
    }

    try {
        const response = await fetch("/restaurant_hotel_planner", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ location: locationInput }),
        });
        const result = await response.json();
        if (response.ok) {
            outputDiv.innerHTML = `<pre>${result.response}</pre>`;
        } else {
            outputDiv.innerHTML = `Error: ${result.error}`;
        }
    } catch (error) {
        outputDiv.innerHTML = "Failed to fetch response from the server.";
    }
}
