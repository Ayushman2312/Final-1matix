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