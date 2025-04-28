function toggleQuickNote() {
    const panel = document.getElementById('quickNotePanel');
    if (panel) {
        panel.classList.toggle('hidden'); // Using 'hidden' class from Tailwind instead of 'show'
        console.log('Quick note panel toggled:', !panel.classList.contains('hidden')); // Debug log
    } else {
        console.error('Quick note panel element not found'); // Error handling
    }
}
tailwind.config = {
    theme: {
        extend: {
            fontFamily: {
                'inter': ['Inter', 'sans-serif']
            },
            backdropBlur: {
                'glass': 'blur(10px)'
            },
            backgroundColor: {
                'glass': 'rgba(33, 33, 33, 0.85)'
            },
            transitionProperty: {
                'transform': 'transform'
            },
            transitionTimingFunction: {
                'hover': 'ease'
            },
            transitionDuration: {
                'hover': '0.3s'
            },
            scale: {
                'hover': '1.02'
            }
        }
    }
}
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('hidden')) {
        sidebar.classList.remove('hidden');
        sidebar.classList.add('block', 'animate__slideInLeft');
    } else {
        sidebar.classList.remove('block', 'animate__slideInLeft');
        sidebar.classList.add('hidden');
    }
}

function toggleQuickNote() {
    const quickNotePanel = document.getElementById('quickNotePanel');
    quickNotePanel.classList.toggle('hidden');
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
    Swal.fire({
        title: 'Add New User',
        html: `
            <div class="space-y-4">
                <input type="email" id="userEmail" class="swal2-input bg-[#2a2a2a] text-white" placeholder="Email">
                <input type="text" id="userName" class="swal2-input bg-[#2a2a2a] text-white" placeholder="Full Name">
                <select id="userRole" class="swal2-input bg-[#2a2a2a] text-white">
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                </select>
            </div>
        `,
        background: '#212121',
        color: '#ffffff',
        confirmButtonColor: '#2196F3',
        showCancelButton: true,
        cancelButtonColor: '#FF5252',
        focusConfirm: false
    });
}

function showNotificationPopup() {
    Swal.fire({
        title: 'Create Notification',
        html: `
            <div class="space-y-4">
                <input type="text" id="notificationTitle" class="swal2-input bg-[#2a2a2a] text-white border-0 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-[#FF9800] focus:outline-none" placeholder="Title">
                
                <textarea id="notificationMessage" class="swal2-textarea bg-[#2a2a2a] text-white border-0 rounded-lg px-4 py-2 w-full h-24 resize-none focus:ring-2 focus:ring-[#FF9800] focus:outline-none" placeholder="Message"></textarea>
                
                <select id="notificationType" class="swal2-input bg-[#2a2a2a] text-white border-0 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-[#FF9800] focus:outline-none">
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="success">Success</option>
                </select>

                <select id="notificationRecipient" class="swal2-input bg-[#2a2a2a] text-white border-0 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-[#FF9800] focus:outline-none">
                    <option value="all">All Users</option>
                    <option value="specific">Specific User</option>
                </select>

                <input type="text" id="specificUserId" class="swal2-input bg-[#2a2a2a] text-white border-0 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-[#FF9800] focus:outline-none hidden" placeholder="Enter user ID">
            </div>
        `,
        background: '#212121',
        color: '#ffffff',
        confirmButtonColor: '#FF9800',
        showCancelButton: true,
        cancelButtonColor: '#FF5252',
        focusConfirm: false,
        didOpen: () => {
            // Show/hide user ID input based on recipient selection
            const recipientSelect = document.getElementById('notificationRecipient');
            const userIdInput = document.getElementById('specificUserId');
            
            recipientSelect.addEventListener('change', (e) => {
                userIdInput.classList.toggle('hidden', e.target.value !== 'specific');
                if (e.target.value === 'specific') {
                    userIdInput.focus();
                }
            });
        }
    });
}

function toggleBroadcastPanel() {
    const panel = document.getElementById('mobileBroadcastPanel');
    panel.classList.toggle('hidden');
}

const feedbackData = [
    {
        name: "John Doe",
        time: "2 hours",
        message: "Great service! Really impressed with the features."
    },
    {
        name: "Jane Smith", 
        time: "5 hours",
        message: "The interface is very intuitive and user-friendly."
    },
    {
        name: "Mike Johnson",
        time: "1 day", 
        message: "Could use some improvements in the mobile version."
    },
    {
        name: "Sarah Williams",
        time: "2 days",
        message: "Excellent customer support team!"
    },
    {
        name: "David Brown",
        time: "3 days",
        message: "Love the new updates and features."
    }
];

const itemsPerPage = 3;
let currentPage = 1;
const totalPages = Math.ceil(feedbackData.length / itemsPerPage);

function displayFeedbacks(page) {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => displayFeedbacks(page));
        return;
    }

    const container = document.getElementById('feedbackContainer');
    if (!container) {
        console.error('Feedback container element not found');
        // Retry after a short delay in case the element is not yet available
        setTimeout(() => displayFeedbacks(page), 100);
        return;
    }
    
    container.innerHTML = '';
    
    const start = (page - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const paginatedItems = feedbackData.slice(start, end);

    paginatedItems.forEach(feedback => {
        const feedbackElement = document.createElement('div');
        feedbackElement.className = 'flex justify-between items-center p-2 bg-[#252525] rounded-lg';
        feedbackElement.innerHTML = `
            <div class="flex items-center space-x-2">
                <div class="w-8 h-8 bg-[#333333] rounded-full flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                </div>
                <div>
                    <p class="text-white text-sm">${feedback.name}</p>
                    <p class="text-[#b3b3b3] text-xs">${feedback.time} ago</p>
                </div>
            </div>
            <p class="text-[#b3b3b3] text-sm">${feedback.message}</p>
        `;
        container.appendChild(feedbackElement);
    });

    // Update pagination elements
    const currentPageEl = document.getElementById('currentPage');
    const totalPagesEl = document.getElementById('totalPages');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (currentPageEl) currentPageEl.textContent = page;
    if (totalPagesEl) totalPagesEl.textContent = totalPages;
    
    // Update button states
    if (prevBtn) prevBtn.disabled = page === 1;
    if (nextBtn) nextBtn.disabled = page === totalPages;
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        displayFeedbacks(currentPage);
    }
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayFeedbacks(currentPage);
    }
}

// Initialize display
displayFeedbacks(currentPage);

// Also listen for DOM content loaded to ensure initialization
document.addEventListener('DOMContentLoaded', () => {
    displayFeedbacks(currentPage);
});

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

async function fetchMeetingStats() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select both start and end dates');
        return;
    }

    try {
        const response = await fetch('/api/meeting-stats/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        
        // Update the statistics
        document.getElementById('attendedMeetings').textContent = data.attended_meetings;
        document.getElementById('cancelledMeetings').textContent = data.cancelled_meetings;

    } catch (error) {
        console.error('Error fetching meeting statistics:', error);
        alert('Error fetching meeting statistics. Please try again.');
    }
}

// Set default date range (last 7 days)
window.addEventListener('DOMContentLoaded', () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);
    
    document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
    document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
    
    fetchMeetingStats();
});

document.addEventListener('DOMContentLoaded', function() {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationPanel = document.getElementById('notificationPanel');
    const notificationList = document.getElementById('notificationList');
    const notificationCount = document.getElementById('notificationCount');

    notificationBtn.addEventListener('click', function() {
        notificationPanel.classList.toggle('hidden');
    });

    // Close notification panel when clicking outside
    document.addEventListener('click', function(event) {
        if (!notificationBtn.contains(event.target) && !notificationPanel.contains(event.target)) {
            notificationPanel.classList.add('hidden');
        }
    });

    // Function to add a new notification
    function addNotification(notification) {
        const notificationElement = document.createElement('div');
        notificationElement.className = 'p-2 bg-[#333333] rounded text-white text-sm';
        notificationElement.innerHTML = `
            <p class="font-semibold">${notification.title}</p>
            <p class="text-gray-300">${notification.message}</p>
            <p class="text-xs text-gray-400 mt-1">${new Date(notification.timestamp).toLocaleString()}</p>
        `;
        notificationList.prepend(notificationElement);
        
        // Update notification count
        notificationCount.textContent = parseInt(notificationCount.textContent) + 1;
    }

    // Example: You can call this function when receiving new notifications
    // addNotification({
    //     title: "New Message",
    //     message: "You have a new message from admin",
    //     timestamp: new Date()
    // });
});