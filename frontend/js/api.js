// frontend/js/api.js

const API_BASE_URL = ''; // Assuming Flask serves on the same origin

async function initVm() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/init`, { method: 'POST' });
        return await response.json();
    } catch (error) {
        console.error("API call to /api/init failed:", error);
        return { success: false, error: "Network error or server down." };
    }
}

async function stepVm() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/step`, { method: 'POST' });
        return await response.json();
    } catch (error) {
        console.error("API call to /api/step failed:", error);
        return { success: false, error: "Network error or server down." };
    }
}

async function provideVmInput(value = null) { // Add default value = null
    try {
        const payload = {};
        if (value !== null) { // Only include 'value' in payload if it's provided
            payload.value = value;
        }
        // If value is null, an empty JSON {} will be sent, or you could choose not to send a body.
        // Flask's request.get_json(silent=True) in app.py will handle {} or missing body gracefully.

        const response = await fetch(`${API_BASE_URL}/api/provide_input`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // Send empty JSON object if no value, app.py's get_json(silent=True) handles this
            body: JSON.stringify(payload), 
        });
        return await response.json();
    } catch (error) {
        console.error("API call to /api/provide_input failed:", error);
        return { success: false, error: "Network error or server down." };
    }
}