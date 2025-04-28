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
            <input type="text" name="coordinates[]" placeholder="Enter coordinates" class="border rounded-md px-4 py-3 text-base" required>
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
    
    // Get CSRF token from the form
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Collect all location names and coordinates
    const locationNames = Array.from(document.getElementsByName('location_names[]')).map(input => input.value);
    const coordinates = Array.from(document.getElementsByName('coordinates[]')).map(input => input.value);
    
    // Create the data object
    const formData = {
        company: document.querySelector('select[name="company"]').value,
        locations: locationNames.map((name, index) => ({
            name: name,
            coordinates: coordinates[index]
        }))
    };

    // Send the data to the server
    fetch('/hr_management/generate-qr-code/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,  // Use the token from the form
            'Accept': 'application/json'
        },
        credentials: 'include',  // Important for CSRF
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal and refresh the page to show new QR code
            closeQRModal();
            window.location.reload();
        } else {
            alert(data.error || 'Error creating QR code');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating QR code');
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

    fetch(`/invoicing/edit-company/${companyId}/`, {
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
        fetch(`/invoicing/delete-company/${companyId}/`, {
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