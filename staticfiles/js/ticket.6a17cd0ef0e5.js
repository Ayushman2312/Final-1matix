// Ticket Actions
let currentTicketId = null; // Moved declaration to top

function markAsResolved() {
    const ticketId = getCurrentTicketId(); // Implement this based on your ticket display logic
    fetch('/api/tickets/resolve/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ ticketId: ticketId })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            showNotification('Ticket marked as resolved', 'success');
            updateTicketStatus(ticketId, 'resolved');
        }
    })
    .catch(error => showNotification('Error resolving ticket', 'error'));
}

function hideTicket() {
    const ticketId = getCurrentTicketId();
    fetch('/api/tickets/hide/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ ticketId: ticketId })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            showNotification('Ticket hidden successfully', 'success');
            removeTicketFromView(ticketId);
        }
    })
    .catch(error => showNotification('Error hiding ticket', 'error'));
}

function showAssignTicketModal() {
    const modal = document.getElementById('assignTicketModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    loadAgents();
}

function closeAssignModal() {
    const modal = document.getElementById('assignTicketModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function loadAgents() {
    fetch('/api/agents/list/')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('agentSelect');
            select.innerHTML = '<option value="">Select Agent</option>';
            data.agents.forEach(agent => {
                select.innerHTML += `<option value="${agent.id}">${agent.name}</option>`;
            });
        });
}

function assignTicketToAgent() {
    const ticketId = getCurrentTicketId();
    const agentId = document.getElementById('agentSelect').value;
    
    if (!agentId) {
        showNotification('Please select an agent', 'warning');
        return;
    }

    fetch('/api/tickets/assign/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ 
            ticketId: ticketId,
            agentId: agentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            showNotification('Ticket assigned successfully', 'success');
            closeAssignModal();
            updateTicketAssignment(ticketId, agentId);
        }
    })
    .catch(error => showNotification('Error assigning ticket', 'error'));
}

function deleteTicket() {
    if(!confirm('Are you sure you want to delete this ticket?')) return;
    
    const ticketId = getCurrentTicketId();
    fetch('/api/tickets/delete/', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ ticketId: ticketId })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            showNotification('Ticket deleted successfully', 'success');
            removeTicketFromView(ticketId);
        }
    })
    .catch(error => showNotification('Error deleting ticket', 'error'));
}

function searchTicket() {
    const mobile = document.getElementById('customerMobile').value;
    const email = document.getElementById('customerEmail').value;
    
    fetch('/api/tickets/search/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ 
            mobile: mobile,
            email: email
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.tickets) {
            displaySearchResults(data.tickets);
        } else {
            showNotification('No tickets found', 'info');
        }
    })
    .catch(error => showNotification('Error searching tickets', 'error'));
}

// Utility Functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function showNotification(message, type) {
    // Implement your notification system
    console.log(`${type}: ${message}`);
}

function updateTicketStatus(ticketId, status) {
    // Implement UI update logic
}

function removeTicketFromView(ticketId) {
    // Implement UI removal logic
}

function updateTicketAssignment(ticketId, agentId) {
    // Implement UI update logic
}

function displaySearchResults(tickets) {
    // Implement search results display logic
}

function getCurrentTicketId() {
    // Implement logic to get current ticket ID
    return document.querySelector('[data-ticket-id]').dataset.ticketId;
}

function openReplyModal() {
    const modal = document.getElementById('replyTicketModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeReplyModal() {
    const modal = document.getElementById('replyTicketModal');
    modal.classList.remove('flex');
    modal.classList.add('hidden');
}

document.getElementById('replyTicketForm').addEventListener('submit', function(e) {
    e.preventDefault();
    // Handle form submission here
    closeReplyModal();
});

function toggleCreateTicketForm() {
    const createTicketPopup = document.getElementById('createTicketPopup');
    const ticketForm = document.getElementById('ticketForm');
    
    if (createTicketPopup.classList.contains('hidden')) {
        createTicketPopup.classList.remove('hidden');
        createTicketPopup.classList.add('flex');
    } else {
        createTicketPopup.classList.add('hidden');
        createTicketPopup.classList.remove('flex');
        ticketForm.reset(); // Reset form when closing
    }
}

document.getElementById('ticketForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = {
        title: document.getElementById('ticketTitle').value,
        description: document.getElementById('ticketDescription').value,
        priority: document.getElementById('ticketPriority').value,
        support_user: document.getElementById('ticketSupportUser').value || null
    };

    // Validate required fields
    if (!formData.title || !formData.description || !formData.priority) {
        Swal.fire({
            icon: 'error',
            title: 'Validation Error',
            text: 'Please fill in all required fields',
            background: '#2a2a2a',
            color: '#ffffff'
        });
        return;
    }

    // Send request to create ticket
    fetch('/masteradmin/create-ticket/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            Swal.fire({
                icon: 'success',
                title: 'Success',
                text: data.message,
                background: '#2a2a2a',
                color: '#ffffff'
            }).then(() => {
                toggleCreateTicketForm(); // Close the form
                location.reload(); // Refresh the page to show new ticket
            });
        } else {
            throw new Error(data.message);
        }
    })
    .catch(error => {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'An error occurred while creating the ticket',
            background: '#2a2a2a',
            color: '#ffffff'
        });
    });
});

// Add this to your existing script section or in a separate JS file
function openAssignToOtherModal(ticketId) {
    currentTicketId = ticketId;
    const modal = document.getElementById('assignToOtherModal');
    modal.classList.remove('hidden');
    // Reset selections
    document.getElementById('departmentSelect').value = '';
    document.getElementById('supportUserSelect').innerHTML = '<option value="">Select Support User</option>';
}

function closeAssignToOtherModal() {
    const modal = document.getElementById('assignToOtherModal');
    modal.classList.add('hidden');
    currentTicketId = null;
}

async function loadSupportUsers() {
    const departmentId = document.getElementById('departmentSelect').value;
    const supportUserSelect = document.getElementById('supportUserSelect');
    
    if (!departmentId) {
        supportUserSelect.innerHTML = '<option value="">Select Support User</option>';
        return;
    }

    try {
        const response = await fetch(`/masteradmin/get_support_users/${departmentId}/`);
        const data = await response.json();
        
        if (data.status === 'success') {
            let options = '<option value="">Select Support User</option>';
            data.users.forEach(user => {
                options += `<option value="${user.id}">${user.name} (${user.pending_tickets} pending tickets)</option>`;
            });
            supportUserSelect.innerHTML = options;
        } else {
            throw new Error(data.message || 'Failed to load support users');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: error.message,
            icon: 'error',
            confirmButtonColor: '#F44336'
        });
    }
}

async function assignTicketToUser() {
    const supportUserId = document.getElementById('supportUserSelect').value;
    
    if (!supportUserId) {
        Swal.fire({
            title: 'Error!',
            text: 'Please select a support user',
            icon: 'error',
            confirmButtonColor: '#F44336'
        });
        return;
    }

    try {
        const response = await fetch(`/masteradmin/assign_ticket/${currentTicketId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                support_user_id: supportUserId
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            Swal.fire({
                title: 'Success!',
                text: data.message,
                icon: 'success',
                confirmButtonColor: '#4CAF50'
            }).then(() => {
                window.location.reload();
            });
            closeAssignToOtherModal();
        } else {
            throw new Error(data.message || 'Failed to assign ticket');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: error.message,
            icon: 'error',
            confirmButtonColor: '#F44336'
        });
    }
}

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
