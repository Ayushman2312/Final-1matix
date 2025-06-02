function openCreateDataModal() {
    document.getElementById('createDataModal').classList.remove('hidden');
}

function closeCreateDataModal() {
    document.getElementById('createDataModal').classList.add('hidden');
}

document.getElementById('createDataForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const title = document.getElementById('dataTitle').value;
    const content = document.getElementById('dataContent').value;
    const folderId = document.querySelector('input[name="folder_id"]').value;

    try {
        const response = await fetch(`/hr_management/create-data/${folderId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                title: title,
                content: content
            })
        });

        const data = await response.json();

        if (data.success) {
            // Add new data to the grid
            const dataGrid = document.querySelector('.grid');
            const newDiv = document.createElement('div');
            newDiv.className = 'bg-white rounded-lg shadow-sm p-4';
            newDiv.innerHTML = `
                <h3 class="text-gray-700 font-medium">${data.title}</h3>
                <p class="text-gray-600 mt-1">${data.content}</p>
            `;
            dataGrid.appendChild(newDiv);

            // Clear form and close modal
            document.getElementById('dataTitle').value = '';
            document.getElementById('dataContent').value = '';
            closeCreateDataModal();
        } else {
            alert(data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while saving the data');
    }
});
function openCreateDataModal() {
    document.getElementById('createDataModal').classList.remove('hidden');
}

function closeCreateDataModal() {
    document.getElementById('createDataModal').classList.add('hidden');
}

document.getElementById('createDataForm').addEventListener('submit', function(e) {
    e.preventDefault();
    // Add your form submission logic here
});

// #2

function openEditDataModal(title, content) {
    document.getElementById('originalTitle').value = title;
    document.getElementById('editDataTitle').value = title;
    document.getElementById('editDataContent').value = content;
    document.getElementById('editDataModal').classList.remove('hidden');
}

function closeEditDataModal() {
    document.getElementById('editDataModal').classList.add('hidden');
}

async function deleteData(title) {
    if (!confirm('Are you sure you want to delete this item?')) {
        return;
    }

    try {
        const response = await fetch(`/hr_management/delete-data/${folderId}/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                title: title
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the page to reflect changes
            window.location.reload();
        } else {
            alert(data.error || 'An error occurred while deleting the data');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while deleting the data');
    }
}

document.getElementById('editDataForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const originalTitle = document.getElementById('originalTitle').value;
    const newTitle = document.getElementById('editDataTitle').value;
    const newContent = document.getElementById('editDataContent').value;

    try {
        const response = await fetch(`/hr_management/update-data/${folderId}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                originalTitle: originalTitle,
                newTitle: newTitle,
                newContent: newContent
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the page to reflect changes
            window.location.reload();
        } else {
            alert(data.error || 'An error occurred while updating the data');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while updating the data');
    }
});