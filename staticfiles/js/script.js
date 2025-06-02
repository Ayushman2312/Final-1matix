tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                'poppins': ['Poppins', 'sans-serif']
            },
            backdropBlur: {
                'glass': 'blur(10px)'
            },
            scrollbar: {
                none: 'none'
            }
        }
    },
    plugins: [
        function ({ addComponents }) {
            addComponents({
                '::-webkit-scrollbar': {
                    display: 'none'
                },
                '::-moz-scrollbar': {
                    display: 'none'
                },
                '*': {
                    scrollbarWidth: 'none'
                }
            });
        }
    ]
}


function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isLargeScreen = window.innerWidth >= 1024; // 1024px is typically 'lg' breakpoint

    if (isLargeScreen) {
        // On large screens, ensure sidebar is always visible
        sidebar.classList.remove('hidden');
        sidebar.classList.add('block');
        return;
    }

    if (sidebar.classList.contains('hidden')) {
        // Show sidebar on mobile
        sidebar.classList.remove('hidden');
        sidebar.classList.add('block', 'fixed', 'left-0', 'top-0', 'h-full', 'z-50', 'animate__animated', 'animate__slideInLeft');
        sidebar.style.boxShadow = '2px 0 5px rgba(0,0,0,0.1)';
        sidebar.style.width = '250px';
        sidebar.style.backgroundColor = '#1a1a1a';
    } else {
        // Hide sidebar on mobile
        sidebar.classList.remove('animate__slideInLeft');
        sidebar.classList.add('animate__slideOutLeft');
        
        // Wait for animation to complete before hiding
        setTimeout(() => {
            sidebar.classList.remove('block', 'animate__slideOutLeft');
            sidebar.classList.add('hidden');
            sidebar.style.boxShadow = 'none';
            sidebar.style.width = '';
            sidebar.style.backgroundColor = '';
        }, 300);
    }
}

function deleteSubscription(id) {
    Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#4F46E5',
        cancelButtonColor: '#EF4444',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            // Submit form to delete subscription
            const form = document.createElement('form');
            form.method = 'POST';
            form.innerHTML = `
                {% csrf_token %}
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="subscription_id" value="${id}">
            `;
            document.body.appendChild(form);
            form.submit();
        }
    })
}
function showPerformers(type) {
    // Hide all performers
    document.getElementById('salesPerformers').classList.add('hidden');
    document.getElementById('meetingsPerformers').classList.add('hidden');
    
    // Remove active state from all tabs
    document.getElementById('salesTab').classList.remove('bg-[#343434]');
    document.getElementById('meetingsTab').classList.remove('bg-[#343434]');
    
    // Show selected performers and activate tab
    if (type === 'sales') {
        document.getElementById('salesPerformers').classList.remove('hidden');
        document.getElementById('salesTab').classList.add('bg-[#343434]');
    } else {
        document.getElementById('meetingsPerformers').classList.remove('hidden');
        document.getElementById('meetingsTab').classList.add('bg-[#343434]');
    }
}

// Initialize with sales tab active
showPerformers('sales');

function showSubscriptionPopup() {
    Swal.fire({
        title: 'Create New Subscription',
        html: `
            <div class="space-y-4">
                <input type="text" id="planName" class="swal2-input bg-[#2a2a2a] text-white" placeholder="Plan Name">
                <input type="number" id="planPrice" class="swal2-input bg-[#2a2a2a] text-white" placeholder="Price">
                <select id="planDuration" class="swal2-input bg-[#2a2a2a] text-white">
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                </select>
            </div>
        `,
        background: '#212121',
        color: '#ffffff',
        confirmButtonColor: '#4CAF50',
        showCancelButton: true,
        cancelButtonColor: '#FF5252',
        focusConfirm: false,
        preConfirm: () => {
            // Handle form submission
            return {
                name: document.getElementById('planName').value,
                price: document.getElementById('planPrice').value,
                duration: document.getElementById('planDuration').value
            }
        }
    });
}

function showUserPopup() {
    document.getElementById('addUserModal').classList.remove('hidden');
    document.getElementById('addUserModal').classList.add('flex');
}

function closeUserPopup() {
    document.getElementById('addUserModal').classList.add('hidden');
    document.getElementById('addUserModal').classList.remove('flex');
}

function toggleBroadcastPanel() {
    const panel = document.getElementById('mobileBroadcastPanel');
    panel.classList.toggle('hidden');
}


function toggleAgentsMenu() {
    const submenu = document.getElementById('agentsSubmenu');
    const arrow = document.getElementById('agentsArrow');
    
    if (submenu.classList.contains('hidden')) {
        submenu.classList.remove('hidden');
        submenu.classList.add('block');
        arrow.classList.add('rotate-180');
    } else {
        submenu.classList.add('hidden');
        submenu.classList.remove('block');
        arrow.classList.remove('rotate-180');
    }
}

function toggleUsersMenu() {
    const submenu = document.getElementById('usersSubmenu');
    const arrow = document.getElementById('usersArrow');
    
    if (submenu.classList.contains('hidden')) {
        submenu.classList.remove('hidden');
        submenu.classList.add('block');
        arrow.classList.add('rotate-180');
    } else {
        submenu.classList.add('hidden');
        submenu.classList.remove('block');
        arrow.classList.remove('rotate-180');
    }
}

function toggleSupportMenu() {
    const submenu = document.getElementById('supportSubmenu');
    const arrow = document.getElementById('supportArrow');
    
    if (submenu.classList.contains('hidden')) {
        submenu.classList.remove('hidden');
        submenu.classList.add('block');
        arrow.classList.add('rotate-180');
    } else {
        submenu.classList.add('hidden');
        submenu.classList.remove('block');
        arrow.classList.remove('rotate-180');
    }
}

function toggleDropdown(submenuId, arrowId) {
    // Get the clicked submenu and arrow
    const clickedSubmenu = document.getElementById(submenuId);
    const clickedArrow = document.getElementById(arrowId);

    // Close all dropdowns first
    const allSubmenus = document.querySelectorAll('[id$="Submenu"]');
    const allArrows = document.querySelectorAll('[id$="Arrow"]');
    
    allSubmenus.forEach(submenu => {
        if (submenu.id !== submenuId) {
            submenu.classList.add('hidden');
            submenu.classList.remove('block');
        }
    });
    
    allArrows.forEach(arrow => {
        if (arrow.id !== arrowId) {
            arrow.classList.remove('rotate-180');
        }
    });

    // Toggle the clicked dropdown
    if (clickedSubmenu.classList.contains('hidden')) {
        clickedSubmenu.classList.remove('hidden');
        clickedSubmenu.classList.add('block');
        clickedArrow.classList.add('rotate-180');
    } else {
        clickedSubmenu.classList.add('hidden');
        clickedSubmenu.classList.remove('block');
        clickedArrow.classList.remove('rotate-180');
    }
}

function openViewAllPopup() {
    const popup = document.getElementById('viewAllPopup');
    const contentContainer = document.getElementById('popupContentContainer');
    
    // Generate content for at least 50 people with a beautiful row-wise layout
    let content = `
        <div class="relative">
            <button onclick="closeViewAllPopup()" class="absolute top-4 right-4 text-white hover:text-gray-300">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 max-h-[80vh] overflow-y-auto no-scrollbar">
    `; // Add max height and scrolling with hidden scrollbar
    
    for (let i = 1; i <= 50; i++) {
        content += `
            <div class="person-details bg-[#333333] p-4 rounded-lg shadow-lg transition-transform transform hover:scale-105">
                <h4 class="text-white font-bold text-lg">Person ${i}</h4>
                <p class="text-white">Details for person ${i}...</p>
                <button class="text-[#2196F3] hover:underline mt-2">View Profile</button>
            </div>
        `;
    }
    content += '</div></div>';
    
    contentContainer.innerHTML = content;
    popup.classList.remove('hidden');
    popup.style.display = 'flex';
    popup.style.alignItems = 'center';
    popup.style.justifyContent = 'center';
    
    // Set max width and height for the content container
    contentContainer.style.maxWidth = '90vw';
    contentContainer.style.width = '1200px'; // Maximum width
    contentContainer.style.margin = 'auto';
    contentContainer.style.backgroundColor = '#1a1a1a';
    contentContainer.style.borderRadius = '1rem';
    contentContainer.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
    contentContainer.style.msOverflowStyle = 'none'; // Hide scrollbar in IE/Edge
    contentContainer.style.scrollbarWidth = 'none'; // Hide scrollbar in Firefox
    
    // Hide scrollbar in Chrome/Safari/Opera
    const style = document.createElement('style');
    style.textContent = `
        #popupContentContainer::-webkit-scrollbar {
            display: none;
        }
    `;
    document.head.appendChild(style);
    
    setTimeout(() => {
        contentContainer.classList.remove('scale-0');
    }, 10);
}

function closeViewAllPopup() {
    const popup = document.getElementById('viewAllPopup');
    const contentContainer = document.getElementById('popupContentContainer');
    contentContainer.classList.add('scale-0');
    setTimeout(() => {
        popup.classList.add('hidden');
        popup.style.display = 'none';
    }, 300); // Match the duration of the transition
}
function showAddAgentPopup() {
    const modal = document.getElementById('addAgentModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    } else {
        console.error('Add agent modal element not found');
    }
}

function closeAddAgentPopup() {
    const modal = document.getElementById('addAgentModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    } else {
        console.error('Add agent modal element not found');
    }
}

// Wait for DOM to be ready
// document.addEventListener('DOMContentLoaded', function() {
//     const form = document.getElementById('addAgentForm');
//     if (!form) {
//         console.error('Add agent form not found');
//         return;
//     }

//     form.addEventListener('submit', async function(e) {
//         e.preventDefault();
        
//         const emailInput = document.getElementById('agentEmail');
//         const passcodeInput = document.getElementById('agentPasscode'); 
//         const templateInput = document.getElementById('agentTemplate');
//         const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');

//         if (!emailInput || !passcodeInput || !templateInput || !csrfToken) {
//             console.error('Required form elements not found');
//             return;
//         }

//         const formData = new FormData();
//         formData.append('email', emailInput.value.trim());
//         formData.append('passcode', passcodeInput.value.trim());
//         formData.append('template', templateInput.value.trim());
//         formData.append('csrfmiddlewaretoken', csrfToken.value);

//         if (!formData.get('email') || !formData.get('passcode') || !formData.get('template')) {
//             Swal.fire({
//                 icon: 'error',
//                 title: 'Validation Error',
//                 text: 'Please fill in all required fields'
//             });
//             return;
//         }

//         try {
//             const response = await fetch('/masteradmin/agents/add_agent/', {
//                 method: 'POST',
//                 body: formData,
//                 headers: {
//                     'X-CSRFToken': csrfToken.value
//                 }
//             });

//             const data = await response.json();

//             if (response.ok) {
//                 this.reset();
//                 closeAddAgentPopup();
                
//                 Swal.fire({
//                     icon: 'success',
//                     title: 'Success',
//                     text: data.message || 'Agent added successfully!'
//                 });

//                 // Refresh the agents list if needed
//                 window.location.reload();
//             } else {
//                 throw new Error(data.message || 'Failed to add agent');
//             }
//         } catch (error) {
//             Swal.fire({
//                 icon: 'error',
//                 title: 'Error',
//                 text: error.message
//             });
//             console.error('Error:', error);
//         }
//     });

//     // Close modal when clicking outside
//     const modal = document.getElementById('addAgentModal');
//     if (modal) {
//         modal.addEventListener('click', function(e) {
//             if (e.target === this) {
//                 closeAddAgentPopup();
//             }
//         });
//     }
// });

function paginate(pageNumber) {
    // Fetch the new page of employees
    fetch(`?page=${pageNumber}`)
        .then(response => response.text())
        .then(html => {
            // Update the content of the employees table
            document.querySelector('.bg-[#212121]').innerHTML = new DOMParser().parseFromString(html, 'text/html').querySelector('.bg-[#212121]').innerHTML;
        })
        .catch(error => console.error('Error fetching page:', error));
    return false; // Prevent default link behavior
}

function showPerformers(type) {
    document.getElementById('salesPerformers').classList.add('hidden');
    document.getElementById('meetingsPerformers').classList.add('hidden');
    if (type === 'sales') {
        document.getElementById('salesPerformers').classList.remove('hidden');
    } else {
        document.getElementById('meetingsPerformers').classList.remove('hidden');
    }
}

function showAddMasterUserPopup() {
    document.getElementById('addMasterUserPopup').classList.remove('hidden');
    document.getElementById('addMasterUserPopup').classList.add('flex');
}

function closeAddMasterUserPopup() {
    document.getElementById('addMasterUserPopup').classList.remove('flex');
    document.getElementById('addMasterUserPopup').classList.add('hidden');
}

document.getElementById('addMasterUserForm').addEventListener('submit', function(e) {
    e.preventDefault();
    // Handle form submission here
    closeAddMasterUserPopup();
});

document.addEventListener('DOMContentLoaded', function() {
    const forms = ['broadcastForm', 'mobileBroadcastForm'];
    
    forms.forEach(formId => {
        const form = document.getElementById(formId);
        if (!form) {
            console.warn(`Form with id ${formId} not found`);
            return;
        }

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Get form values
            const department = this.querySelector('[name="department_type"]')?.value;
            const title = this.querySelector('[name="title"]')?.value;
            const message = this.querySelector('[name="message"]')?.value;

            // Validate required fields
            if (!department || !title || !message) {
                Swal.fire({
                    icon: 'error',
                    title: 'Error!',
                    text: 'Please fill in all required fields',
                    confirmButtonText: 'OK'
                });
                return;
            }

            // Disable form while submitting
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
            }

            try {
                const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]').value;
                if (!csrfToken) {
                    throw new Error('CSRF token not found');
                }

                // Prepare request data
                const requestData = {
                    department_type: department.trim(),
                    title: title.trim(),
                    message: message.trim()
                };

                // Make API call to WhatsOnMind view
                const response = await fetch('/masteradmin/whats_on_mind/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify(requestData)
                });

                const data = await response.json();

                if (response.ok) {
                    // Show success message
                    await Swal.fire({
                        icon: 'success',
                        title: 'Success!', 
                        text: data.message || 'Message sent successfully',
                        showConfirmButton: false,
                        timer: 1500
                    });

                    // Reset form
                    this.reset();
                } else {
                    throw new Error(data.message || 'Failed to send message');
                }

            } catch (error) {
                console.error('Error:', error);
                await Swal.fire({
                    icon: 'error',
                    title: 'Error!',
                    text: error.message || 'Something went wrong while sending the message',
                    confirmButtonText: 'OK'
                });
            } finally {
                // Re-enable form
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
    });
});

// Handle agent selection to show/hide passcode field
document.addEventListener('DOMContentLoaded', function() {
    const agentSelect = document.querySelector('select[name="agent"]');
    const passcodeField = document.getElementById('passcodeField');
    
    if (agentSelect && passcodeField) {
        agentSelect.addEventListener('change', function() {
            if (this.value) {
                passcodeField.classList.remove('hidden');
            } else {
                passcodeField.classList.add('hidden');
            }
        });
    }

    // Handle form submission
    const form = document.getElementById('addUserForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Form submission started');
            
            // Create FormData object and log its contents
            const formData = new FormData(this);
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }
            
            try {
                const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]').value;
                console.log('CSRF Token:', csrfToken);
                
                const response = await fetch('/masteradmin/create_user/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin' // Add this to ensure cookies are sent
                });

                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Response data:', data);

                if (response.ok) {
                    await Swal.fire({
                        icon: 'success',
                        title: 'Success!',
                        text: data.message || 'User added successfully!',
                        showConfirmButton: false,
                        timer: 1500
                    });
                    
                    closeUserPopup();
                    window.location.reload();
                } else {
                    throw new Error(data.message || 'Failed to add user');
                }
            } catch (error) {
                console.error('Error in form submission:', error);
                await Swal.fire({
                    icon: 'error',
                    title: 'Error!',
                    text: error.message || 'Something went wrong while adding the user',
                    confirmButtonText: 'OK'
                });
            }
        });
    }
});

// Optional: Show success/error messages using SweetAlert2
document.addEventListener('DOMContentLoaded', function() {
    // Check for Django messages
    const messages = document.querySelectorAll('.message');
    messages.forEach(function(message) {
        const text = message.textContent;
        const type = message.dataset.type;
        
        Swal.fire({
            title: type === 'error' ? 'Error!' : 'Success!',
            text: text,
            icon: type,
            timer: 3000,
            showConfirmButton: false
        });
    });
});

