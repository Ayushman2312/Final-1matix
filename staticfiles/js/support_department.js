function showCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.remove('hidden');
}

function showDeleteDepartmentPopup(id, name) {
    Swal.fire({
        title: 'Are you sure?',
        text: `Do you want to delete the department "${name}"?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel'
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                const response = await fetch(`/masteradmin/delete_support_department/${id}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `action=delete&department_id=${id}`
                });

                const data = await response.json();

                if (response.ok) {
                    Swal.fire({
                        title: 'Success!',
                        text: 'Department deleted successfully',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    }).then(() => {
                        location.reload();
                    });
                } else {
                    throw new Error(data.message || 'Failed to delete department');
                }
            } catch (error) {
                Swal.fire({
                    title: 'Error!',
                    text: error.message,
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        }
    });
}

function hideDeleteDepartmentPopup() {
    document.getElementById('deleteDepartmentPopup').classList.add('hidden');
}

function hideCreateDepartmentPopup() {
    document.getElementById('createDepartmentPopup').classList.add('hidden');
}

function showEditDepartmentPopup(id, name) {
    document.getElementById('editDepartmentPopup').classList.remove('hidden');
    document.getElementById('edit_department_id').value = id;
    document.getElementById('edit_department_name').value = name;

    // Set up form submission handler
    const form = document.getElementById('editDepartmentForm');
    form.onsubmit = async (e) => {
        e.preventDefault();
        
        try {
            const formData = new FormData();
            formData.append('action', 'edit');
            formData.append('department_id', id);
            formData.append('name', document.getElementById('edit_department_name').value);

            const response = await fetch('/masteradmin/support_department/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                Swal.fire({
                    title: 'Success!',
                    text: 'Department updated successfully',
                    icon: 'success',
                    confirmButtonText: 'OK'
                }).then(() => {
                    location.reload();
                });
            } else {
                throw new Error(data.message || 'Failed to update department');
            }
        } catch (error) {
            Swal.fire({
                title: 'Error!', 
                text: error.message,
                icon: 'error',
                confirmButtonText: 'OK'
            });
        }
    };
}

function hideEditDepartmentPopup() {
    document.getElementById('editDepartmentPopup').classList.add('hidden');
}
document.getElementById('editDepartmentForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit_department_id').value;
    const formData = {
        department_name: document.getElementById('edit_department_name').value
    };

    try {
        const response = await fetch(`/masteradmin/support_department/${id}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if(response.ok) {
            Swal.fire({
                title: 'Success!',
                text: 'Department updated successfully',
                icon: 'success',
                confirmButtonText: 'OK'
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                title: 'Error!',
                text: data.message || 'Failed to update department',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: 'An error occurred while updating the department',
            icon: 'error',
            confirmButtonText: 'OK'
        });
    }

    hideEditDepartmentPopup();
});

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

document.getElementById('createDepartmentForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    formData.append('action', 'create'); // Add action parameter
    
    fetch('/masteradmin/support_department/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success') {
            Swal.fire({
                title: 'Success!',
                text: 'Department created successfully',
                icon: 'success',
                confirmButtonText: 'OK'
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                title: 'Error!',
                text: data.message || 'Something went wrong',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: 'Something went wrong',
            icon: 'error',
            confirmButtonText: 'OK'
        });
    });

    hideCreateDepartmentPopup();
});