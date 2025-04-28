function openFolderModal() {
    document.getElementById('folderModal').classList.remove('hidden');
}

function closeFolderModal() {
    document.getElementById('folderModal').classList.add('hidden');
}

document.getElementById('folderForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    const title = document.getElementById('folderTitle').value;
    const description = document.getElementById('folderDescription').value;
    const logoFile = document.getElementById('folderLogo').files[0];

    // Add form data directly without Blob wrapping
    formData.append('folderTitle', title);
    formData.append('folderDescription', description);

    if (logoFile) {
        // Validate file type and size
        if (!logoFile.type.match('image.*')) {
            alert('Please upload an image file');
            return;
        }
        if (logoFile.size > 10 * 1024 * 1024) { // 10MB limit
            alert('File size should be less than 10MB');
            return;
        }
        formData.append('folderLogo', logoFile);
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch('/hr_management/create-folder/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken,
            // Remove Content-Type header to let browser set it with boundary
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Folder created successfully');
            closeFolderModal();
            location.reload();
        } else {
            throw new Error(data.error || 'Error creating folder');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating folder: ' + error.message);
    });
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

document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrfToken) {
        console.error('CSRF token not found in the form');
    }
});