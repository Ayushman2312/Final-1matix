// Get DOM elements
const notificationBtn = document.getElementById('notificationBtn');
const notificationPanel = document.getElementById('notificationPanel');
const notificationCount = document.getElementById('notificationCount');

// Toggle notification panel visibility
notificationBtn.addEventListener('click', () => {
    notificationPanel.classList.toggle('hidden');
});

// Close notification panel when clicking outside
document.addEventListener('click', (event) => {
    if (!notificationBtn.contains(event.target) && 
        !notificationPanel.contains(event.target)) {
        notificationPanel.classList.add('hidden');
    }
});

// Function to update notification count
function updateNotificationCount(count) {
    notificationCount.textContent = count;
    if (count === 0) {
        notificationCount.classList.add('hidden');
    } else {
        notificationCount.classList.remove('hidden');
    }
}

// Function to add new notification
function addNotification(message, timestamp) {
    const notificationList = document.getElementById('notificationList');
    const notification = document.createElement('div');
    notification.className = 'bg-[#2a2a2a] p-3 rounded-lg';
    notification.innerHTML = `
        <p class="text-white text-sm">${message}</p>
        <span class="text-[#b3b3b3] text-xs">${timestamp}</span>
    `;
    notificationList.prepend(notification);
    
    // Update count
    const currentCount = parseInt(notificationCount.textContent);
    updateNotificationCount(currentCount + 1);
}

// Function to clear all notifications
function clearNotifications() {
    const notificationList = document.getElementById('notificationList');
    notificationList.innerHTML = '<p class="text-[#b3b3b3] text-sm">No notifications yet</p>';
    updateNotificationCount(0);
    
    // Store cleared notifications in localStorage
    const notifications = Array.from(notificationList.children).map(notification => {
        return {
            message: notification.querySelector('p')?.textContent,
            timestamp: notification.querySelector('span')?.textContent
        };
    });
    localStorage.setItem('clearedNotifications', JSON.stringify(notifications));
    localStorage.setItem('notificationsCleared', 'true');
    
    // Disable the clear notifications button
    const clearBtn = document.querySelector('[onclick="clearNotifications()"]');
    if (clearBtn) {
        clearBtn.disabled = true;
        clearBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

// Optional: WebSocket connection for real-time notifications
// const ws = new WebSocket('your_websocket_url');
// ws.onmessage = (event) => {
//     const data = JSON.parse(event.data);
//     addNotification(data.message, 'Just now');
// };

function showNotificationDetails(message, datetime, department) {
    const modal = document.getElementById('notificationModal');
    const modalContent = document.getElementById('modalContent');
    
    // Set content
    document.getElementById('modalMessage').textContent = message;
    document.getElementById('modalDateTime').textContent = datetime;
    document.getElementById('modalDepartment').textContent = department;
    
    // Show modal with animation
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    setTimeout(() => {
        modalContent.classList.add('scale-100');
    }, 10);
}

function closeNotificationModal() {
    const modal = document.getElementById('notificationModal');
    const modalContent = document.getElementById('modalContent');
    
    // Hide with animation
    modalContent.classList.remove('scale-100');
    modalContent.classList.add('scale-0');
    setTimeout(() => {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }, 300);
}

// Close modal when clicking outside
document.getElementById('notificationModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeNotificationModal();
    }
});

document.getElementById('clearNotifications').addEventListener('click', function() {
    const notifications = document.querySelectorAll('.notification-item');
    notifications.forEach((notification, index) => {
        setTimeout(() => {
            notification.style.transition = 'opacity 0.5s ease-out';
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
                if (index === notifications.length - 1) {
                    // Add "No notifications" message after all notifications are removed
                    const container = document.getElementById('notificationsContainer');
                    const emptyMessage = document.createElement('div');
                    emptyMessage.className = 'p-2 bg-[#252525] rounded-lg flex items-center justify-center';
                    emptyMessage.innerHTML = '<p class="text-white text-xs sm:text-sm">No notifications</p>';
                    container.appendChild(emptyMessage);
                }
            }, 500);
        }, index * 200); // 200ms delay between each notification
    });
});