// static/js/scripts.js

// Global function to toggle all checkboxes (reused from Tkinter concept)
function toggleAllCheckboxes(source, name) {
    const checkboxes = document.querySelectorAll('input[name="' + name + '"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = source.checked;
    });
}

// Data mapping for dynamic text model selection
const textModels = {
    "Gemini": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro"
    ],
    "OpenAI": [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o"
    ],
    "DeepSeek": [
        "deepseek-coder",
        "deepseek-r1" // Assuming this is the desired default for DeepSeek
    ],
    "Mistral": [
        "mistral",
        "mistral-openorca" // Assuming this is the desired default for Mistral
    ]
};

// Function to update text models dropdown and temperature slider visibility
function updateTextModels() {
    const providerSelect = document.getElementById('text_gen_provider');
    const modelSelect = document.getElementById('text_model_selector');
    const tempGroup = document.getElementById('gemini_temp_group');
    const selectedProvider = providerSelect.value;

    // Get references to hidden inputs
    const hiddenGeminiModelInput = document.getElementById('hidden_gemini_model');
    const hiddenOpenAIModelInput = document.getElementById('hidden_openai_text_model');


    // Clear existing options
    modelSelect.innerHTML = '';

    // Populate new options based on provider
    const modelsForProvider = textModels[selectedProvider] || [];
    modelsForProvider.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });

    // Set the selected model in the visible dropdown AND update the hidden input
    let modelToSet = '';
    if (selectedProvider === "Gemini") {
        modelToSet = modelSelect.dataset.initialGeminiModel || textModels.Gemini[0];
        hiddenGeminiModelInput.value = modelToSet; // Update hidden field
        hiddenOpenAIModelInput.value = ''; // Clear other hidden field
    } else if (selectedProvider === "OpenAI") {
        modelToSet = modelSelect.dataset.initialOpenaiTextModel || textModels.OpenAI[0];
        hiddenOpenAIModelInput.value = modelToSet; // Update hidden field
        hiddenGeminiModelInput.value = ''; // Clear other hidden field
    } else if (selectedProvider === "DeepSeek") {
        modelToSet = modelSelect.dataset.initialDeepseekModel || textModels.DeepSeek[0];
        hiddenOpenAIModelInput.value = modelToSet; // Use OpenAI hidden field for DeepSeek/Mistral for simplicity
        hiddenGeminiModelInput.value = '';
    } else if (selectedProvider === "Mistral") {
        modelToSet = modelSelect.dataset.initialMistralModel || textModels.Mistral[0];
        hiddenOpenAIModelInput.value = modelToSet; // Use OpenAI hidden field for DeepSeek/Mistral for simplicity
        hiddenGeminiModelInput.value = '';
    }

    if (modelsForProvider.includes(modelToSet)) {
        modelSelect.value = modelToSet;
    } else if (modelsForProvider.length > 0) {
        modelSelect.value = modelsForProvider[0]; // Fallback to first available if initial not found
        // Also update the hidden field if we fallback
        if (selectedProvider === "Gemini") hiddenGeminiModelInput.value = modelsForProvider[0];
        else hiddenOpenAIModelInput.value = modelsForProvider[0];
    } else {
        // No models available for provider, clear hidden fields
        hiddenGeminiModelInput.value = '';
        hiddenOpenAIModelInput.value = '';
    }


    // Toggle temperature slider visibility (only for Gemini)
    if (selectedProvider === "Gemini") {
        tempGroup.style.display = 'block';
    } else {
        tempGroup.style.display = 'none';
    }
}

// General function to handle image upload via AJAX
function uploadImage(postId, currentFilter, currentSelectedPostId) {
    const fileInput = document.getElementById('select_image_file');
    if (fileInput.files.length === 0) {
        alert('Please select an image file first.');
        return;
    }

    const formData = new FormData();
    formData.append('action', 'upload_image');
    formData.append('post_id', postId);
    formData.append('image_file', fileInput.files[0]);

    const url = `/post_review?filter=${currentFilter}&selected_post_id=${currentSelectedPostId}`;

    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return response.json();
        } else {
            return response.text().then(text => { throw new Error('Server did not return JSON: ' + text); });
        }
    })
    .then(data => {
        if (data.status === 'success') {
            alert(data.message + '. Page will refresh to show changes.');
            window.location.href = `/post_review?filter=${currentFilter}&selected_post_id=${postId}`;
        } else {
            alert('Error uploading image: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error during image upload:', error);
        alert('An error occurred during image upload. See console for details.');
    });
}


// --- Event Listeners for DOMContentLoaded (runs when HTML is loaded) ---
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages
    const flashes = document.querySelector('.flashes');
    if (flashes) {
        setTimeout(() => {
            flashes.style.display = 'none';
        }, 5000); // Hide after 5 seconds
    }

    // Initialize the text model selector and temperature slider display on Generate Posts page
    const textGenProviderSelect = document.getElementById('text_gen_provider');
    if (textGenProviderSelect) {
        updateTextModels(); // Call updateTextModels immediately to set initial state
        textGenProviderSelect.addEventListener('change', updateTextModels); // Add listener for future changes
    }
    
    // For index.html temperature slider display update
    const temperatureSlider = document.getElementById('temperature');
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', function() {
            document.getElementById('temperature_value').textContent = this.value;
        });
    }
});