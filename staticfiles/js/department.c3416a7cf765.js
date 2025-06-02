function showCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.remove('hidden');
}

function hideCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.add('hidden');
}

document.getElementById('createDepartmentForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        department_name: document.getElementById('department_name').value,
        department_terms: document.getElementById('department_terms').value
    };

    try {
        const response = await fetch('/masteradmin/departments/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        // Check if response has content before trying to parse JSON
        const text = await response.text();
        let data;
        try {
            data = text ? JSON.parse(text) : {};
        } catch (err) {
            console.error('Error parsing JSON:', err);
            throw new Error('Invalid JSON response from server');
        }

        if (response.ok) {
            alert('Department created successfully!');
            hideCreateDepartmentPopup();
            location.reload();
        } else {
            alert(data.message || 'Error creating department');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while creating the department');
    }
});

// Helper function to get CSRF token
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

function showCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.remove('hidden');
}

function hideCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.add('hidden');
    // Clear form fields
    document.getElementById('department_name').value = '';
    document.getElementById('department_terms').value = '';
}

async function showEditDepartmentPopup(id, name, terms) {
    // Create modal HTML
    const modalHTML = `
        <div id="editDepartmentPopup" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-[#212121] rounded-xl p-6 w-full max-w-md">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-[#ffffff] text-lg font-bold">Edit Department</h3>
                    <button onclick="hideEditDepartmentPopup()" class="text-[#b3b3b3] hover:text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <form id="editDepartmentForm" class="space-y-4">
                    <input type="hidden" id="edit_department_id" value="${id}">
                    <div>
                        <label for="edit_department_name" class="block text-[#b3b3b3] text-sm mb-2">Department Name</label>
                        <input type="text" id="edit_department_name" value="${name}" class="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#4CAF50]">
                    </div>
                    <div class="flex justify-end space-x-3">
                        <button type="button" onclick="hideEditDepartmentPopup()" class="px-4 py-2 bg-[#2a2a2a] text-white rounded-lg hover:bg-[#343434] transition-all duration-300">Cancel</button>
                        <button type="submit" class="px-4 py-2 bg-[#4CAF50] text-white rounded-lg hover:bg-[#45a049] transition-all duration-300">Update</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    // Add modal to document
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add submit handler
    document.getElementById('editDepartmentForm').addEventListener('submit', handleEditDepartmentSubmit);
}

function hideEditDepartmentPopup() {
    const popup = document.getElementById('editDepartmentPopup');
    if (popup) {
        popup.remove();
    }
}

async function handleEditDepartmentSubmit(e) {
    e.preventDefault();

    const id = document.getElementById('edit_department_id').value;
    const formData = {
        department_name: document.getElementById('edit_department_name').value,
        department_terms: document.getElementById('edit_department_terms').value
    };

    try {
        const response = await fetch(`/masteradmin/departments/${id}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const text = await response.text();
        let data;
        try {
            data = text ? JSON.parse(text) : {};
        } catch (err) {
            console.error('Error parsing JSON:', err);
            throw new Error('Invalid JSON response from server');
        }

        if (response.ok) {
            alert('Department updated successfully!');
            hideEditDepartmentPopup();
            location.reload();
        } else {
            alert(data.message || 'Error updating department');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while updating the department');
    }
}

function showDeleteDepartmentPopup(id, name) {
    // Remove any existing delete popup first
    hideDeleteDepartmentPopup();
    
    const modalHTML = `
        <div id="deleteDepartmentPopup" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-[#212121] rounded-xl p-6 w-full max-w-md">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-[#ffffff] text-lg font-bold">Delete Department</h3>
                    <button onclick="hideDeleteDepartmentPopup()" class="text-[#b3b3b3] hover:text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <p class="text-white mb-4">Are you sure you want to delete department "${name}"? This action cannot be undone.</p>

                <div class="flex justify-end space-x-3">
                    <button onclick="hideDeleteDepartmentPopup()" class="px-4 py-2 bg-[#2a2a2a] text-white rounded-lg hover:bg-[#343434] transition-all duration-300">Cancel</button>
                    <button onclick="confirmDeleteDepartment('${id}')" class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all duration-300">Delete</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function hideDeleteDepartmentPopup() {
    const popup = document.getElementById('deleteDepartmentPopup');
    if (popup) {
        popup.remove();
    }
}

async function confirmDeleteDepartment(id) {
    try {
        // Disable delete button to prevent double clicks
        const deleteButton = document.querySelector('#deleteDepartmentPopup button:last-child');
        if (deleteButton) {
            deleteButton.disabled = true;
            deleteButton.textContent = 'Deleting...';
        }

        const response = await fetch(`/masteradmin/delete_department/${id}/`, { // Updated URL
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        // Only try to parse JSON if there is content
        if (response.status !== 204) { // 204 No Content
            const text = await response.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (err) {
                console.error('Error parsing JSON:', err);
                data = {}; // Use empty object if parsing fails
            }

            if (!response.ok) {
                throw new Error(data.message || 'Failed to delete department');
            }
        }

        // Success case
        hideDeleteDepartmentPopup();
        alert('Department deleted successfully!');
        location.reload();

    } catch (error) {
        console.error('Error deleting department:', error);
        alert(error.message || 'An error occurred while deleting the department. Please try again.');
        
        // Re-enable delete button on error
        const deleteButton = document.querySelector('#deleteDepartmentPopup button:last-child');
        if (deleteButton) {
            deleteButton.disabled = false;
            deleteButton.textContent = 'Delete';
        }
    }
}
