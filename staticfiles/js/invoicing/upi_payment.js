function handleFileUpload(input) {
    if (input.files && input.files[0]) {
        const label = input.previousElementSibling;
        label.classList.add('uploading');
        
        // Show thank you message immediately before form submission
        showThankYouMessage();
        
        // Submit the form after a short delay to allow the user to see the message
        setTimeout(() => {
            const form = document.getElementById('screenshot-form');
            form.submit();
        }, 1000);
    }
}

// #2
 // Function to check if device is mobile
 function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Function to show thank you message
function showThankYouMessage() {
    document.getElementById('thank-you-message').classList.remove('hidden');
}

// Function to close thank you message
function closeThankYouMessage() {
    document.getElementById('thank-you-message').classList.add('hidden');
}

// Check if form was just submitted (using URL parameter or session storage)
function checkFormSubmission() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check URL parameter
    if (urlParams.get('submitted') === 'true') {
        showThankYouMessage();
        return;
    }
    
    // Check session storage as fallback
    if (sessionStorage.getItem('screenshotSubmitted') === 'true') {
        showThankYouMessage();
        sessionStorage.removeItem('screenshotSubmitted');
    }
}

// Execute immediately when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check for form submission
    checkFormSubmission();
    
    // Store submission state before form submits
    document.getElementById('screenshot-form').addEventListener('submit', function() {
        sessionStorage.setItem('screenshotSubmitted', 'true');
    });
    
    // Add desktop-specific instructions if not on mobile
    if (!isMobileDevice()) {
        // Update the instruction text for desktop users
        const instructionText = document.querySelector('.text-center.text-sm.text-gray-500.mt-4');
        if (instructionText) {
            instructionText.innerHTML = `
                <p class="font-bold">You're on desktop:</p>
                <p>Scan the QR code with your UPI app to make payment.</p>
                <p>The app buttons below are for reference only.</p>
            `;
        }
        
        // Make QR code larger on desktop
        const qrImage = document.querySelector('img[alt="UPI QR Code"]');
        if (qrImage) {
            qrImage.classList.remove('w-48', 'h-48');
            qrImage.classList.add('w-64', 'h-64');
        }
    }
});