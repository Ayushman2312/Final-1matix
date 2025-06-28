function showQRModal() {
    document.getElementById('qrModal').classList.remove('hidden');
}

function closeQRModal() {
    document.getElementById('qrModal').classList.add('hidden');
}

function addCoordinateField() {
    const container = document.getElementById('coordinates-container');
    const newEntry = document.createElement('div');
    newEntry.className = 'coordinate-entry flex items-center mb-4';
    newEntry.innerHTML = `
        <div class="flex-1 grid grid-cols-2 gap-4">
            <input type="text" name="location_names[]" placeholder="Enter location name" class="border rounded-md px-4 py-3 text-base" required>
            <input type="text" name="coordinates[]" placeholder="e.g., 12.9716,77.5946" class="border rounded-md px-4 py-3 text-base" required>
        </div>
        <button type="button" onclick="removeCoordinateField(this)" class="ml-4 text-red-500 hover:text-red-700">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;
    container.appendChild(newEntry);
}

function removeCoordinateField(button) {
    button.closest('.coordinate-entry').remove();
}

document.getElementById('qrCodeForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Create FormData object directly from the form
    const formData = new FormData(this);
    
    // Check if we have at least one valid location with coordinates
    const locationNames = Array.from(document.getElementsByName('location_names[]'));
    const coordinatesInputs = Array.from(document.getElementsByName('coordinates[]'));
    
    // Validate that we have at least one location with coordinates
    let hasValidLocation = false;
    for (let i = 0; i < locationNames.length; i++) {
        if (locationNames[i].value.trim() && coordinatesInputs[i].value.trim()) {
            hasValidLocation = true;
            break;
        }
    }
    
    if (!hasValidLocation) {
        alert('Please provide at least one valid location with coordinates.');
        return;
    }
    
    // Use fetch API to submit the form
    fetch('/hr/generate-qr-code/', {
        method: 'POST',
        body: formData,
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Server response was not ok: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Close modal and refresh the page to show new QR code
            closeQRModal();
            window.location.reload();
        } else {
            alert(data.message || 'Error creating QR code');
            console.error('Server returned error:', data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating QR code: ' + error.message);
    });
});

function openEditModal(companyId, name, gst, mobile, email, state, prefix, bankName, accountNumber, ifscCode, upiId, address) {
    document.getElementById('editModal').classList.remove('hidden');
    document.getElementById('edit_company_id').value = companyId;
    document.getElementById('edit_company_name').value = name;
    document.getElementById('edit_company_gst_number').value = gst;
    document.getElementById('edit_company_mobile_number').value = mobile;
    document.getElementById('edit_company_email').value = email;
    document.getElementById('edit_company_state').value = state;
    document.getElementById('edit_company_invoice_prefix').value = prefix;
    document.getElementById('edit_company_bank_name').value = bankName;
    document.getElementById('edit_company_bank_account_number').value = accountNumber;
    document.getElementById('edit_company_bank_ifsc_code').value = ifscCode;
    document.getElementById('edit_company_upi_id').value = upiId;
    document.getElementById('edit_company_address').value = address;
}

function closeEditModal() {
    document.getElementById('editModal').classList.add('hidden');
}

document.getElementById('editForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    const companyId = document.getElementById('edit_company_id').value;

    fetch(`/hr/edit-company/${companyId}/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error updating company');
        }
    });
});

function deleteCompany(companyId) {
    if (confirm('Are you sure you want to delete this company?')) {
        fetch(`/hr/delete-company/${companyId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert('Error deleting company');
            }
        });
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to view QR code details
function viewQRCode(qrCodeId) {
    // Fetch QR code details from the server
    fetch(`/hr/qr-code-details/${qrCodeId}/`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Create a modal to display QR code details
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-50 flex items-center justify-center';
            modal.id = 'qrDetailsModal';
            
            // Format location data for display
            const locationName = data.qr_code.location_and_coordinates.location_name || 'Not specified';
            const coordinates = data.qr_code.location_and_coordinates.coordinates || 'Not specified';
            
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-semibold text-gray-800">QR Code Details</h3>
                        <button onclick="closeQRDetailsModal()" class="text-gray-500 hover:text-gray-700">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <div class="space-y-4">
                        <div class="flex justify-center mb-4">
                            <img src="${data.qr_code.qr_code_image}" alt="QR Code" class="w-48 h-48 object-contain">
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-sm">
                            <span class="font-medium text-gray-700">Company:</span>
                            <span class="col-span-2">${data.qr_code.company_name}</span>
                            
                            <span class="font-medium text-gray-700">Location:</span>
                            <span class="col-span-2">${locationName}</span>
                            
                            <span class="font-medium text-gray-700">Coordinates:</span>
                            <span class="col-span-2">${typeof coordinates === 'object' ? JSON.stringify(coordinates) : coordinates}</span>
                            
                            <span class="font-medium text-gray-700">Created:</span>
                            <span class="col-span-2">${data.qr_code.created_at}</span>
                        </div>
                        <div class="mt-6 flex justify-center">
                            <a href="${data.qr_code.qr_code_image}" 
                               download="qr_code_${data.qr_code.company_name}_${locationName}.png"
                               class="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700">
                                <svg class="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                                </svg>
                                Download QR Code
                            </a>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        } else {
            alert(data.message || 'Error fetching QR code details');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error fetching QR code details. Please try again.');
    });
}

// Function to close the QR code details modal
function closeQRDetailsModal() {
    const modal = document.getElementById('qrDetailsModal');
    if (modal) {
        modal.remove();
    }
}

// Function to delete a QR code
function deleteQRCode(qrCodeId) {
    if (confirm('Are you sure you want to delete this QR code?')) {
        // Get CSRF token
        const csrfToken = getCookie('csrftoken');
        
        // Send delete request to the server
        fetch(`/hr/delete-qr-code/${qrCodeId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'  // Important for CSRF
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Refresh the page to reflect the changes
                window.location.reload();
            } else {
                alert(data.message || 'Error deleting QR code');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting QR code. Please try again.');
        });
    }
}