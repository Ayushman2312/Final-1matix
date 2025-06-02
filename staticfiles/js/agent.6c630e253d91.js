function approveAgent(url) {
    // Get CSRF token from cookie instead of DOM
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

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            Swal.fire({
                title: 'Success!',
                text: data.message,
                icon: 'success'
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                title: 'Error!',
                text: data.message,
                icon: 'error'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: 'An error occurred while processing your request',
            icon: 'error'
        });
    });
}

function rejectAgent(agentId) {
    Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#F44336',
        cancelButtonColor: '#b3b3b3',
        confirmButtonText: 'Yes, reject it!'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/masteradmin/reject-agent/${agentId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    Swal.fire({
                        title: 'Success!',
                        text: data.message,
                        icon: 'success'
                    }).then(() => {
                        location.reload();
                    });
                } else {
                    Swal.fire({
                        title: 'Error!',
                        text: data.message,
                        icon: 'error'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred while rejecting the agent',
                    icon: 'error'
                });
            });
        }
    });
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
function viewAgentDetails(agentId) {
    const modal = document.getElementById(`agentModal-${agentId}`);
    modal.classList.remove('hidden');
}

function closeAgentModal(agentId) {
    const modal = document.getElementById(`agentModal-${agentId}`);
    modal.classList.add('hidden');
}

function viewSupportDetails(supportId) {
    const modal = document.getElementById(`supportModal-${supportId}`);
    modal.classList.remove('hidden');
}

function closeSupportModal(supportId) {
    const modal = document.getElementById(`supportModal-${supportId}`);
    modal.classList.add('hidden');
}

function viewEmployeeDetails(employeeId) {
    const modal = document.getElementById(`employeeModal-${employeeId}`);
    modal.classList.remove('hidden');
}

function closeEmployeeModal(employeeId) {
    const modal = document.getElementById(`employeeModal-${employeeId}`);
    modal.classList.add('hidden');
}

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('agent-search');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const agentCards = document.querySelectorAll('.flex.justify-between.items-center.p-3.bg-\\[\\#252525\\].rounded-lg');
            
            agentCards.forEach(card => {
                const name = card.querySelector('p.text-white.text-xs')?.textContent.toLowerCase() || '';
                const email = card.querySelector('p.text-\\[\\#b3b3b3\\].text-\\[11px\\]')?.textContent.toLowerCase() || '';
                
                if (name.includes(searchTerm) || email.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
});

// Filter functionality 
function filterAgents(status) {
    const agentCards = document.querySelectorAll('.flex.justify-between.items-center.p-3.bg-\\[\\#252525\\].rounded-lg');
    const buttons = document.querySelectorAll('.filter-btn');
    
    // Update active button
    buttons.forEach(btn => {
        if(btn.textContent.toLowerCase().includes(status)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    agentCards.forEach(card => {
        const statusElement = card.querySelector('[data-status]');
        const cardStatus = statusElement ? statusElement.dataset.status : 'active';
        
        if (status === 'all') {
            card.style.display = '';
        } else if (status === cardStatus) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

function switchUserType(type) {
    const userTypeButtons = document.querySelectorAll('.user-type-btn');
    const agentsList = document.getElementById('agentsList');
    const employeesList = document.getElementById('employeesList'); // Assuming you have this element
    const supportList = document.getElementById('supportList'); // Assuming you have this element

    // Hide all lists initially
    agentsList.style.display = 'none';
    employeesList.style.display = 'none';
    supportList.style.display = 'none';

    // Remove active class from all buttons
    userTypeButtons.forEach(button => {
        button.classList.remove('active');
    });

    // Show the selected list and set the active button
    if (type === 'agent') {
        agentsList.style.display = 'block';
        userTypeButtons[0].classList.add('active');
    } else if (type === 'employee') {
        employeesList.style.display = 'block';
        userTypeButtons[1].classList.add('active');
    } else if (type === 'support') {
        supportList.style.display = 'block';
        userTypeButtons[2].classList.add('active');
    }
}

function showNotificationPopup() {
    document.getElementById('notificationModal').classList.remove('hidden');
    document.getElementById('notificationModal').classList.add('flex');
}

function closeNotificationPopup() {
    document.getElementById('notificationModal').classList.remove('flex');
    document.getElementById('notificationModal').classList.add('hidden');
}

// Agent search functionality
document.getElementById('agentSearch').addEventListener('input', function(e) {
    const searchText = e.target.value.toLowerCase();
    const options = document.getElementById('agentSelect').options;
    
    for (let option of options) {
        const agentName = option.text.toLowerCase();
        option.style.display = agentName.includes(searchText) ? '' : 'none';
    }
});