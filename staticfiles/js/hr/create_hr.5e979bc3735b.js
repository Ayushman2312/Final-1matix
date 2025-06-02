function handleFileSelect(input, displayId) {
    const fileNameDiv = document.getElementById(displayId);
    const fileNameSpan = fileNameDiv.querySelector('span');
    
    if (input.files && input.files[0]) {
        fileNameSpan.textContent = input.files[0].name;
        fileNameDiv.classList.remove('hidden');
    } else {
        fileNameDiv.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('companyForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const submitText = document.getElementById('submitText');
        const loadingSpinner = document.getElementById('loadingSpinner');
        
        // Show loading state
        submitText.classList.add('hidden');
        loadingSpinner.classList.remove('hidden');

        const formData = new FormData(this);

        fetch('/hr_management/create-company/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': '{{ csrf_token }}'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            return response.json();  // Change to json() instead of text()
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            // If we reach here, it means the company was created successfully
            window.location.href = data.redirect_url || '/hr_management/company/';
        })
        .catch(error => {
            console.error('Error:', error);
            // Only show error alert if it's actually an error, not a redirect
            if (!window.location.href.includes('/hr_management/company/')) {
                alert('An error occurred while creating the company. Please try again.');
            }
        })
        .finally(() => {
            // Reset button state
            submitText.classList.remove('hidden');
            loadingSpinner.classList.add('hidden');
        });
    });
});