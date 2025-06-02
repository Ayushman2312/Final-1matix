// Toggle subscription details
function toggleSubscriptionDetails(subscriptionId) {
    const detailsElement = document.getElementById(`subscription-details-${subscriptionId}`);
    const arrowIcon = document.getElementById(`arrow-${subscriptionId}`);
    
    if (detailsElement.classList.contains('hidden')) {
        detailsElement.classList.remove('hidden');
        arrowIcon.classList.add('rotate-180');
    } else {
        detailsElement.classList.add('hidden'); 
        arrowIcon.classList.remove('rotate-180');
    }
}

// Handle subscription status toggle
function toggleSubscriptionStatus(subscriptionId) {
    const statusSwitch = document.getElementById(`status-switch-${subscriptionId}`);
    const statusLabel = document.getElementById(`status-label-${subscriptionId}`);
    
    if (statusSwitch.checked) {
        statusLabel.textContent = 'Active';
        statusLabel.classList.remove('text-red-500');
        statusLabel.classList.add('text-green-500');
    } else {
        statusLabel.textContent = 'Inactive';
        statusLabel.classList.remove('text-green-500');
        statusLabel.classList.add('text-red-500');
    }

    // Here you would typically make an API call to update the status
    // fetch('/api/subscription/toggle-status', {
    //     method: 'POST',
    //     body: JSON.stringify({
    //         subscriptionId: subscriptionId,
    //         status: statusSwitch.checked
    //     })
    // });
}

// Handle subscription pause toggle
function toggleSubscriptionPause(subscriptionId) {
    const pauseSwitch = document.getElementById(`pause-switch-${subscriptionId}`);
    const pauseLabel = document.getElementById(`pause-label-${subscriptionId}`);
    
    if (pauseSwitch.checked) {
        pauseLabel.textContent = 'Paused';
        pauseLabel.classList.remove('text-green-500');
        pauseLabel.classList.add('text-yellow-500');
    } else {
        pauseLabel.textContent = 'Running';
        pauseLabel.classList.remove('text-yellow-500');
        pauseLabel.classList.add('text-green-500');
    }

    // Here you would typically make an API call to update the pause status
    // fetch('/api/subscription/toggle-pause', {
    //     method: 'POST',
    //     body: JSON.stringify({
    //         subscriptionId: subscriptionId,
    //         paused: pauseSwitch.checked
    //     })
    // });
}

// Handle edit subscription
function editSubscription(subscriptionId) {
    // Redirect to edit page or show modal
    window.location.href = `/subscription/edit/${subscriptionId}`;
}

// Handle delete subscription
function deleteSubscription(subscriptionId) {
    if (confirm('Are you sure you want to delete this subscription?')) {
        // Here you would typically make an API call to delete the subscription
        // fetch(`/api/subscription/delete/${subscriptionId}`, {
        //     method: 'DELETE'
        // }).then(() => {
        //     // Remove the subscription element from DOM
        //     document.getElementById(`subscription-${subscriptionId}`).remove();
        // });
    }
}

// Filter subscriptions
function filterSubscriptions(status) {
    const subscriptions = document.querySelectorAll('.subscription-item');
    
    subscriptions.forEach(subscription => {
        const isActive = subscription.getAttribute('data-status') === 'active';
        if (status === 'all' || 
            (status === 'active' && isActive) || 
            (status === 'inactive' && !isActive)) {
            subscription.classList.remove('hidden');
        } else {
            subscription.classList.add('hidden');
        }
    });
}

// Search subscriptions
function searchSubscriptions(query) {
    const subscriptions = document.querySelectorAll('.subscription-item');
    const searchQuery = query.toLowerCase();
    
    subscriptions.forEach(subscription => {
        const name = subscription.getAttribute('data-name').toLowerCase();
        if (name.includes(searchQuery)) {
            subscription.classList.remove('hidden');
        } else {
            subscription.classList.add('hidden');
        }
    });
}

// Show subscription popup
function showSubscriptionPopup() {
    Swal.fire({
        title: 'Edit Subscription',
        html: `
            <div class="space-y-4">
                <select id="plan-type" class="w-full bg-[#252525] text-white rounded-lg px-3 py-2 text-sm">
                    <option value="Monthly">Monthly</option>
                    <option value="Quarterly">Quarterly</option>
                    <option value="Yearly">Yearly</option>
                </select>
                <input type="number" id="price" placeholder="Price" class="w-full bg-[#252525] text-white rounded-lg px-3 py-2 text-sm">
                <input type="number" id="users" placeholder="Number of Users" class="w-full bg-[#252525] text-white rounded-lg px-3 py-2 text-sm">
                <input type="number" id="validity" placeholder="Validity (days)" class="w-full bg-[#252525] text-white rounded-lg px-3 py-2 text-sm">
                <input type="number" id="discount" placeholder="Discount %" class="w-full bg-[#252525] text-white rounded-lg px-3 py-2 text-sm">
            </div>
        `,
        background: '#212121',
        color: '#ffffff',
        confirmButtonColor: '#4CAF50',
        showCancelButton: true,
        cancelButtonColor: '#F44336',
        confirmButtonText: 'Save Changes',
        preConfirm: () => {
            return {
                planType: document.getElementById('plan-type').value,
                price: document.getElementById('price').value,
                users: document.getElementById('users').value,
                validity: document.getElementById('validity').value,
                discount: document.getElementById('discount').value
            }
        }
    }).then((result) => {
        if (result.isConfirmed) {
            // Handle form submission
            console.log(result.value);
            Swal.fire({
                title: 'Success!',
                text: 'Subscription updated successfully',
                icon: 'success',
                background: '#212121',
                color: '#ffffff',
                confirmButtonColor: '#4CAF50'
            });
        }
    });
}

// Show delete subscription popup
function deleteSubscriptionPopup() {
    Swal.fire({
        title: 'Delete Subscription',
        text: 'Are you sure you want to delete this subscription? This action cannot be undone.',
        icon: 'warning',
        background: '#212121',
        color: '#ffffff',
        showCancelButton: true,
        confirmButtonColor: '#F44336',
        cancelButtonColor: '#9e9e9e',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            // Handle deletion
            Swal.fire({
                title: 'Deleted!',
                text: 'The subscription has been deleted.',
                icon: 'success',
                background: '#212121',
                color: '#ffffff',
                confirmButtonColor: '#4CAF50'
            });
        }
    });
}

// Show create subscription popup
function openSubscriptionModal() {
    document.getElementById('subscriptionDetailsModal').classList.remove('hidden');
}

let subscriptionToDelete = null;

function confirmDelete(id, name) {
    subscriptionToDelete = id;
    document.getElementById('subscriptionName').textContent = name;
    document.getElementById('deleteModal').classList.remove('hidden');
    document.getElementById('deleteModal').classList.add('flex');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.add('hidden');
    document.getElementById('deleteModal').classList.remove('flex');
    subscriptionToDelete = null;
}

function deleteSubscription() {
    if (subscriptionToDelete) {
        // Make API call to delete subscription
        fetch(`/masteradmin/delete_subscription/`, {
            method: 'POST', 
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: new URLSearchParams({
                'subscription_id': subscriptionToDelete
            })
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
                    text: 'Subscription deleted successfully',
                    icon: 'success',
                    background: '#212121',
                    color: '#ffffff',
                    confirmButtonColor: '#4CAF50'
                }).then(() => {
                    window.location.reload();
                });
            } else {
                throw new Error(data.message || 'Failed to delete subscription');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                title: 'Error!',
                text: 'Failed to delete subscription. Please try again.',
                icon: 'error',
                background: '#212121', 
                color: '#ffffff',
                confirmButtonColor: '#F44336'
            });
        })
        .finally(() => {
            closeDeleteModal();
        });
    } else {
        closeDeleteModal();
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

function openEditModal(id, name, price, planType, validityDays) {
    // Get form elements
    const subscriptionIdInput = document.getElementById('subscription_id');
    const nameInput = document.getElementById('name');
    const priceInput = document.getElementById('price_monthly');
    const planTypeInput = document.getElementById('plan_type');
    const validityDaysInput = document.getElementById('validity_days');
    const modal = document.getElementById('editModal');

    // Check if all required elements exist
    if (!subscriptionIdInput || !nameInput || !priceInput || !planTypeInput || !validityDaysInput || !modal) {
        console.error('Required form elements not found');
        Swal.fire({
            title: 'Error',
            text: 'Could not find all required form elements. Please try again.',
            icon: 'error',
            background: '#212121',
            color: '#ffffff',
            confirmButtonColor: '#F44336'
        });
        return;
    }

    // Set form values
    subscriptionIdInput.value = id;
    nameInput.value = name;
    priceInput.value = price;
    planTypeInput.value = planType;
    validityDaysInput.value = validityDays;

    // Show modal
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const editForm = document.getElementById('editSubscriptionForm');
    if (!editForm) {
        console.error('Edit subscription form not found');
        return;
    }

    editForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        try {
            const response = await fetch('/masteradmin/edit_subscription/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                Swal.fire({
                    title: 'Success!',
                    text: data.message,
                    icon: 'success',
                    background: '#212121',
                    color: '#ffffff',
                    confirmButtonColor: '#4CAF50'
                }).then(() => {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                });
            } else {
                throw new Error(data.message || 'An error occurred');
            }
        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                title: 'Error!',
                text: error.message || 'An error occurred while updating the subscription',
                icon: 'error',
                background: '#212121',
                color: '#ffffff', 
                confirmButtonColor: '#F44336'
            });
        }

        closeEditModal();
    });
});