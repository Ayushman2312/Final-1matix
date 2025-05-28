// Tab switching functionality
function switchTab(tab) {
    const addEmployeeTab = document.getElementById('addEmployeeTab');
    const viewEmployeesTab = document.getElementById('viewEmployeesTab');
    const employeeForm = document.getElementById('employeeForm');
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');

    if (tab === 'add') {
        // Switch to Add Employee tab
        addEmployeeTab.classList.add('bg-[#7B3DF3]');
        addEmployeeTab.classList.remove('bg-gray-100');
        addEmployeeTab.classList.add('text-white');
        viewEmployeesTab.classList.remove('bg-[#7B3DF3]');
        viewEmployeesTab.classList.remove('text-white');
        viewEmployeesTab.classList.add('bg-gray-100');
        
        // Show the form
        if (employeeForm) {
            employeeForm.classList.remove('hidden');
        }
        
        // Hide the employees section
        if (viewEmployeesSection) {
            viewEmployeesSection.classList.add('hidden');
        }
    } else {
        // Switch to View Employees tab
        viewEmployeesTab.classList.add('bg-[#7B3DF3]');
        viewEmployeesTab.classList.remove('bg-gray-100');
        viewEmployeesTab.classList.add('text-white');
        addEmployeeTab.classList.remove('text-white');
        addEmployeeTab.classList.remove('bg-[#7B3DF3]');
        addEmployeeTab.classList.add('bg-gray-100');
        
        // Show the employees section
        if (viewEmployeesSection) {
            viewEmployeesSection.classList.remove('hidden');
            populateEmployeesTable();
        }
    }
}

// Policy tag management
function addPolicy(policyText) {
    const policyContainer = document.querySelector('.flex.flex-wrap.gap-2');
    if (!policyContainer) return;
    
    const policyTag = document.createElement('span');
    policyTag.className = 'inline-flex items-center px-3 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800';
    policyTag.innerHTML = `${policyText} <button class="ml-1 text-gray-500 hover:text-gray-700" onclick="removePolicy(this)">&times;</button>`;
    
    policyContainer.appendChild(policyTag);
}

function removePolicy(button) {
    const tag = button.parentElement;
    if (tag) {
        tag.remove();
    }
}

// Employee table management
function populateEmployeesTable() {
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');
    if (!viewEmployeesSection) return;
    
    // Show loading state
    viewEmployeesSection.innerHTML = '<div class="text-center py-4">Loading invitations...</div>';
    
    // Fetch invitations from context data
    const invitations = window.invitationsData || [];
    
    if (invitations.length === 0) {
        viewEmployeesSection.innerHTML = '<div class="text-center py-4 text-gray-500">No invitations found.</div>';
        return;
    }
    
    // Generate table HTML
    let tableHTML = `
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Department</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sent Date</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
    `;
    
    // Add invitation rows
    invitations.forEach(invitation => {
        // Format date
        const sentDate = invitation.sent_at ? new Date(invitation.sent_at).toLocaleDateString() : 'Not sent';
        
        // Determine status class
        let statusClass = '';
        switch(invitation.status) {
            case 'pending':
                statusClass = 'bg-gray-100 text-gray-800';
                break;
            case 'sent':
                statusClass = 'bg-yellow-100 text-yellow-800';
                break;
            case 'completed':
                statusClass = 'bg-green-100 text-green-800';
                break;
            case 'rejected':
                statusClass = 'bg-red-100 text-red-800';
                break;
            case 'expired':
                statusClass = 'bg-red-100 text-red-800';
                break;
            default:
                statusClass = 'bg-gray-100 text-gray-800';
        }
        
        // Make sure invitation_id is available and not undefined
        const invitationId = invitation.invitation_id || '';
        
        tableHTML += `
            <tr>
                <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">${invitation.name || '-'}</td>
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">${invitation.email || '-'}</td>
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">${invitation.department || '-'}</td>
                <td class="px-4 py-2 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                        ${invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
                    </span>
                </td>
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">${sentDate}</td>
                <td class="px-4 py-2 whitespace-nowrap">
                    <div class="flex items-center space-x-3">
                        ${invitation.status === 'completed' ? `
                            <button 
                                class="text-blue-600 hover:text-blue-800 focus:outline-none" 
                                title="View Details"
                                onclick="viewInvitationDetails('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                            </button>
                            <button 
                                class="text-green-600 hover:text-green-800 focus:outline-none" 
                                title="Accept" 
                                onclick="acceptInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                </svg>
                            </button>
                            <button 
                                class="text-red-600 hover:text-red-800 focus:outline-none" 
                                title="Reject" 
                                onclick="rejectInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        ` : `
                            <button 
                                class="text-red-600 hover:text-red-800 focus:outline-none" 
                                title="Delete" 
                                onclick="deleteInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        `}
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
            </tbody>
        </table>
    `;
    
    viewEmployeesSection.innerHTML = tableHTML;
}

// View invitation details
function viewInvitationDetails(invitationId) {
    // Show loading indicator
    Swal.fire({
        title: 'Loading...',
        text: 'Fetching invitation details',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    // Fetch invitation details from the server
    fetch(`/hr_management/onboarding/invitation/${invitationId}/`)
        .then(response => response.json())
        .then(data => {
            Swal.close();
            
            if (data.success) {
                const invitation = data.invitation;
                
                // Format dates for display
                const createdAt = invitation.created_at ? new Date(invitation.created_at).toLocaleString() : 'N/A';
                const sentAt = invitation.sent_at ? new Date(invitation.sent_at).toLocaleString() : 'N/A';
                const completedAt = invitation.completed_at ? new Date(invitation.completed_at).toLocaleString() : 'N/A';
                
                // Prepare policies list
                let policiesList = '';
                if (invitation.policies && invitation.policies.length > 0) {
                    policiesList = invitation.policies.map(policy => `<li>${policy}</li>`).join('');
                } else {
                    policiesList = '<li>No policies attached</li>';
                }
                
                // Show invitation details in a modal
                Swal.fire({
                    title: 'Invitation Details',
                    html: `
                        <div class="text-left">
                            <div class="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <p class="text-sm font-bold">Name:</p>
                                    <p class="text-sm">${invitation.name || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Email:</p>
                                    <p class="text-sm">${invitation.email || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Department:</p>
                                    <p class="text-sm">${invitation.department || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Designation:</p>
                                    <p class="text-sm">${invitation.designation || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Role:</p>
                                    <p class="text-sm">${invitation.role || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Status:</p>
                                    <p class="text-sm font-semibold ${
                                        invitation.status === 'completed' ? 'text-green-600' : 
                                        invitation.status === 'rejected' ? 'text-red-600' : 
                                        invitation.status === 'sent' ? 'text-yellow-600' : 'text-gray-600'
                                    }">${invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}</p>
                                </div>
                            </div>
                            
                            <div class="mb-4">
                                <p class="text-sm font-bold mb-1">Policies:</p>
                                <ul class="list-disc list-inside text-sm">
                                    ${policiesList}
                                </ul>
                            </div>
                            
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <p class="text-sm font-bold">Created At:</p>
                                    <p class="text-sm">${createdAt}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Sent At:</p>
                                    <p class="text-sm">${sentAt}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-bold">Completed At:</p>
                                    <p class="text-sm">${completedAt}</p>
                                </div>
                            </div>
                        </div>
                    `,
                    width: '600px',
                    confirmButtonText: 'Close',
                    confirmButtonColor: '#3085d6'
                });
            } else {
                showNotification('Error: ' + (data.message || 'Failed to fetch invitation details'), 'error');
            }
        })
        .catch(error => {
            Swal.close();
            console.error('Error:', error);
            showNotification('An error occurred while fetching invitation details', 'error');
        });
}

// Accept invitation
function acceptInvitation(invitationId) {
    Swal.fire({
        title: 'Accept Employee',
        html: `
            <div class="text-left">
                <p class="mb-3">Are you sure you want to accept this employee?</p>
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-3">
                    <div class="flex">
                        <div class="ml-3">
                            <p class="text-sm text-green-700">
                                By accepting, you will:
                            </p>
                            <ul class="mt-1 text-sm text-green-700 list-disc list-inside">
                                <li>Grant the employee access to the dashboard</li>
                                <li>Send them a welcome email with login details</li>
                                <li>Set their status as active in the system</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Yes, accept',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#10B981',
        cancelButtonColor: '#6B7280'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show processing state
            Swal.fire({
                title: 'Processing...',
                text: 'Accepting invitation',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Send accept request with action parameter to indicate we're accepting a completed invitation
            fetch(`/hr_management/onboarding/invitation/${invitationId}/accept/?v=2`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                },
                body: JSON.stringify({
                    action: 'approve_completed',
                    from_status: 'completed',
                    to_status: 'accepted'
                })
            })
            .then(response => response.json())
            .then(data => {
                Swal.close();
                if (data.success) {
                    showNotification(data.message || 'Invitation accepted successfully. Employee now has dashboard access.', 'success');
                    // Reload the invites table
                    populateEmployeesTable();
                } else {
                    let errorMsg = data.message || 'Failed to accept invitation';
                    
                    // Handle specific error cases
                    if (errorMsg.includes('already been completed')) {
                        errorMsg = 'There was an issue updating the invitation status. Please refresh the page and try again.';
                    }
                    
                    showNotification('Error: ' + errorMsg, 'error');
                }
            })
            .catch(error => {
                Swal.close();
                console.error('Error:', error);
                showNotification('An error occurred while accepting the invitation. Please try again.', 'error');
            });
        }
    });
}

// Reject invitation
function rejectInvitation(invitationId) {
    Swal.fire({
        title: 'Reject Employee',
        html: `
            <div class="text-left">
                <p class="mb-3">Are you sure you want to reject this employee?</p>
                <div class="bg-red-50 border-l-4 border-red-400 p-4 mb-3">
                    <div class="flex">
                        <div class="ml-3">
                            <p class="text-sm text-red-700">
                                By rejecting, you will:
                            </p>
                            <ul class="mt-1 text-sm text-red-700 list-disc list-inside">
                                <li>Deny the employee access to the dashboard</li>
                                <li>Send them a rejection notification</li>
                                <li>Keep their information in the system for reference</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, reject',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#EF4444',
        cancelButtonColor: '#6B7280',
    }).then((result) => {
        if (result.isConfirmed) {
            // Show processing state
            Swal.fire({
                title: 'Processing...',
                text: 'Rejecting invitation',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Send reject request with action parameter to indicate we're rejecting a completed invitation
            fetch(`/hr_management/onboarding/invitation/${invitationId}/reject/?v=2`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                },
                body: JSON.stringify({
                    action: 'reject_completed',
                    from_status: 'completed',
                    to_status: 'rejected'
                })
            })
            .then(response => response.json())
            .then(data => {
                Swal.close();
                if (data.success) {
                    showNotification(data.message || 'Invitation rejected successfully', 'success');
                    // Reload the invites table
                    populateEmployeesTable();
                } else {
                    let errorMsg = data.message || 'Failed to reject invitation';
                    
                    // Handle specific error cases
                    if (errorMsg.includes('already been completed')) {
                        errorMsg = 'There was an issue updating the invitation status. Please refresh the page and try again.';
                    }
                    
                    showNotification('Error: ' + errorMsg, 'error');
                }
            })
            .catch(error => {
                Swal.close();
                console.error('Error:', error);
                showNotification('An error occurred while rejecting the invitation. Please try again.', 'error');
            });
        }
    });
}

// Delete invitation
function deleteInvitation(invitationId) {
    Swal.fire({
        title: 'Delete Invitation',
        text: 'Are you sure you want to delete this invitation? This action cannot be undone.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, delete it',
        cancelButtonText: 'Cancel',
        confirmButtonColor: '#EF4444',
        cancelButtonColor: '#6B7280',
    }).then((result) => {
        if (result.isConfirmed) {
            // Send delete request
            fetch(`/hr_management/onboarding/invitation/${invitationId}/delete/?v=2`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message || 'Invitation deleted successfully', 'success');
                    // Reload the invites table
                    populateEmployeesTable();
                } else {
                    showNotification('Error: ' + (data.message || 'Failed to delete invitation'), 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while deleting the invitation', 'error');
            });
        }
    });
}

// Function to send onboarding invitation
function sendOnboardingInvitation() {
    // Get form values
    const companySelect = document.querySelector('select[class*="w-full border text-sm border-gray-200 rounded-md"]');
    const nameInput = document.querySelector('input[placeholder="Name"]');
    const emailInput = document.querySelector('input[placeholder="Select and Paste"]');
    const departmentSelect = document.getElementById('departmentSelect');
    const designationSelect = document.getElementById('designationSelect');
    const roleSelect = document.getElementById('roleSelect');
    const offerLetterSelect = document.getElementById('offerLetterSelect');
    const photoInput = document.getElementById('photoUpload');
    
    // Validate required fields
    if (!companySelect.value) {
        showNotification('Please select a company', 'error');
        return;
    }
    
    if (!nameInput.value.trim()) {
        showNotification('Please enter a name', 'error');
        return;
    }
    
    if (!emailInput.value.trim()) {
        showNotification('Please enter an email', 'error');
        return;
    }
    
    // Validate email format
    if (!isValidEmail(emailInput.value.trim())) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    // Collect policies
    const policyTags = document.querySelectorAll('.flex.flex-wrap.gap-2 > span');
    const policies = Array.from(policyTags).map(tag => tag.textContent.trim().replace('×', '').trim());
    
    // Create FormData object for file upload
    const formData = new FormData();
    formData.append('company', companySelect.value);
    formData.append('name', nameInput.value.trim());
    formData.append('email', emailInput.value.trim());
    
    // Send IDs for foreign key fields, only if they have a value
    if (departmentSelect && departmentSelect.value) {
        formData.append('department', departmentSelect.value);
    }
    
    if (designationSelect && designationSelect.value) {
        formData.append('designation', designationSelect.value);
    }
    
    if (roleSelect && roleSelect.value) {
        formData.append('role', roleSelect.value);
    }
    
    if (offerLetterSelect.value) {
        formData.append('offer_letter', offerLetterSelect.value);
    }
    
    // Add photo file if selected
    if (photoInput && photoInput.files.length > 0) {
        formData.append('photo', photoInput.files[0]);
    }
    
    // Add policies
    if (policies.length > 0) {
        formData.append('policies', JSON.stringify(policies));
    }
    
    // Show loading state
    const sendButton = document.getElementById('sendButton');
    const originalText = sendButton.textContent;
    sendButton.textContent = 'Sending...';
    sendButton.disabled = true;
    
    // Send API request
    fetch('/hr_management/onboarding/send-invitation/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Invitation sent successfully!', 'success');
            resetForm();
            // Reload the invites table if on the view tab
            if (document.getElementById('viewEmployeesTab').classList.contains('bg-[#7B3DF3]')) {
                populateEmployeesTable();
            }
        } else {
            showNotification(data.message || 'Failed to send invitation', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        // Reset button state
        sendButton.textContent = originalText;
        sendButton.disabled = false;
    });
}

// Helper function to get CSRF token
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

// Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Function to show notification
function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-md shadow-md transition-all duration-300 z-50 ${
        type === 'success' ? 'bg-green-100 text-green-800 border-l-4 border-green-500' : 
        'bg-red-100 text-red-800 border-l-4 border-red-500'
    }`;
    notification.innerHTML = message;
    
    // Add to DOM
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Function to reset the form
function resetForm() {
    const nameInput = document.querySelector('input[placeholder="Name"]');
    const emailInput = document.querySelector('input[placeholder="Select and Paste"]');
    const departmentSelect = document.getElementById('departmentSelect');
    const designationSelect = document.getElementById('designationSelect');
    const roleSelect = document.getElementById('roleSelect');
    const offerLetterSelect = document.getElementById('offerLetterSelect');
    const photoInput = document.getElementById('photoUpload');
    const photoPreview = document.getElementById('photoPreview');
    const photoPlaceholder = document.getElementById('photoPlaceholder');
    
    // Reset input values
    nameInput.value = '';
    emailInput.value = '';
    if (departmentSelect) departmentSelect.selectedIndex = 0;
    if (designationSelect) designationSelect.selectedIndex = 0;
    if (roleSelect) roleSelect.selectedIndex = 0;
    offerLetterSelect.selectedIndex = 0;
    
    // Reset photo
    if (photoInput) photoInput.value = '';
    if (photoPreview) {
        photoPreview.src = '';
        photoPreview.classList.add('hidden');
    }
    if (photoPlaceholder) {
        photoPlaceholder.classList.remove('hidden');
    }
    
    // Clear policy tags
    const policyContainer = document.querySelector('.flex.flex-wrap.gap-2');
    if (policyContainer) {
        policyContainer.innerHTML = '';
    }
}

// #2
function updateOfferLetterContent() {
    const select = document.getElementById('offerLetterSelect');
    const previewContent = document.querySelector('.offer-letter-preview-content');
    
    // Get the selected template ID
    const templateId = select.value;
    
    if (!templateId) {
        previewContent.innerHTML = '<p class="text-gray-500">Select an offer letter template and click the preview button to see it here.</p>';
        return;
    }
    
    // Show loading state
    previewContent.innerHTML = '<p class="text-gray-500">Loading preview...</p>';
    
    // Fetch template content
    fetch(`/hr_management/templates/offer-letter/preview/${templateId}/`)
        .then(response => response.text())
        .then(html => {
            previewContent.innerHTML = html;
        })
        .catch(error => {
            console.error('Error:', error);
            previewContent.innerHTML = '<p class="text-red-500">Error loading preview. Please try again.</p>';
        });
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up photo upload preview
    const photoUpload = document.getElementById('photoUpload');
    const photoPreview = document.getElementById('photoPreview');
    const photoPlaceholder = document.getElementById('photoPlaceholder');
    
    if (photoUpload && photoPreview && photoPlaceholder) {
        photoUpload.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    photoPreview.src = e.target.result;
                    photoPreview.classList.remove('hidden');
                    photoPlaceholder.classList.add('hidden');
                };
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Set up policy input
    const policyInput = document.querySelector('input[placeholder="Attach Upload (Min. 2)"]');
    const policyAddButton = policyInput?.nextElementSibling;
    
    if (policyInput && policyAddButton) {
        // Add policy when button is clicked
        policyAddButton.addEventListener('click', function() {
            const policyText = policyInput.value.trim();
            if (policyText) {
                addPolicy(policyText);
                policyInput.value = '';
            }
        });
        
        // Add policy when Enter is pressed
        policyInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                const policyText = this.value.trim();
                if (policyText) {
                    addPolicy(policyText);
                    this.value = '';
                }
            }
        });
    }
    
    // Set up offer letter preview
    const previewButton = document.getElementById('previewButton');
    if (previewButton) {
        previewButton.addEventListener('click', function() {
            updateOfferLetterContent();
        });
    }
    
    // Set up send button
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            sendOnboardingInvitation();
        });
    }
    
    // Initialize invitation data for the table
    window.invitationsData = Array.from(document.querySelectorAll('#invitationsData > div')).map(div => {
        return {
            invitation_id: div.dataset.id,
            name: div.dataset.name,
            email: div.dataset.email,
            department: div.dataset.department,
            designation: div.dataset.designation,
            role: div.dataset.role,
            status: div.dataset.status,
            sent_at: div.dataset.sentAt,
            created_at: div.dataset.createdAt,
            completed_at: div.dataset.completedAt
        };
    });
    
    // Populate the employees table if viewing that tab
    if (document.getElementById('viewEmployeesTab').classList.contains('bg-[#7B3DF3]')) {
        populateEmployeesTable();
    }
});