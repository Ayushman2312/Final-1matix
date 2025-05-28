/**
 * Data Miner Shared JavaScript Functionality
 * Contains utilities for task tracking, notifications, and persistence
 */

// Add flashing animation styles 
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes notification-flash {
            0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.7); }
            70% { box-shadow: 0 0 0 15px rgba(79, 70, 229, 0); }
            100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
        }
        
        .notification-flashing {
            animation: notification-flash 2s infinite;
        }
    `;
    document.head.appendChild(style);
})();

// Task tracking and notification system
const DataMinerTasks = {
    // Storage key for tasks
    STORAGE_KEY: 'dataMinerTasks',
    
    // Initialize the task tracking system
    init: function() {
        // Request notification permission on page load if needed
        if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }
        
        // Check for tasks that may have completed while away
        this.checkStoredTasks();
        
        // Start polling for active tasks on the page
        this.startPolling();
    },
    
    // Store a task ID in localStorage for tracking
    storeTask: function(taskId) {
        if (!taskId) return;
        
        let tasks = this.getStoredTasks();
        if (!tasks.includes(taskId)) {
            tasks.push(taskId);
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(tasks));
            
            // Also store in a cookie for server-side detection
            this.setCookie(this.STORAGE_KEY, JSON.stringify(tasks), 1); // 1 day expiration
            
            console.log(`Task ${taskId} stored for tracking`);
            
            // If we're on the background tasks page, immediately check the task status
            // to get parameters and update UI
            if (window.location.pathname.includes('/background-tasks')) {
                this.checkTaskStatus(taskId, data => {
                    // Find the task item element
                    const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
                    if (taskItem) {
                        // Update the UI with the latest data
                        this.updateTaskUI(taskItem, data);
                    }
                });
            }
        }
    },
    
    // Get all stored task IDs
    getStoredTasks: function() {
        const tasksJson = localStorage.getItem(this.STORAGE_KEY);
        console.log("Raw tasks from localStorage:", tasksJson);
        try {
            return JSON.parse(tasksJson || '[]');
        } catch (e) {
            console.error("Error parsing tasks from localStorage:", e);
            return [];
        }
    },
    
    // Remove a task from storage
    removeTask: function(taskId) {
        let tasks = this.getStoredTasks();
        tasks = tasks.filter(id => id !== taskId);
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(tasks));
        
        // Also update the cookie
        this.setCookie(this.STORAGE_KEY, JSON.stringify(tasks), 1);
        console.log(`Task ${taskId} removed from tracking`);
    },
    
    // Helper function to set a cookie
    setCookie: function(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        document.cookie = name + '=' + encodeURIComponent(value) + expires + '; path=/; SameSite=Lax';
        console.log(`Cookie ${name} set with value length ${value.length}`);
    },
    
    // Check stored tasks on page load and periodically
    checkStoredTasks: function() {
        const tasks = this.getStoredTasks();
        
        if (tasks.length > 0) {
            console.log(`Checking ${tasks.length} stored tasks: ${JSON.stringify(tasks)}`);
            
            tasks.forEach(taskId => {
                this.checkTaskStatus(taskId, (data) => {
                    // If task completed or failed, notify and remove
                    if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
                        this.showNotification({
                            id: taskId,
                            name: data.task_name || 'Data Mining Task',
                            status: data.status,
                            historyId: data.history_id
                        });
                        
                        this.removeTask(taskId);
                    }
                });
            });
        }
    },
    
    // Check status of a specific task
    checkTaskStatus: function(taskId, callback) {
        console.log(`Checking status of task ${taskId}`);
        fetch(`/data_miner/api/task-status/${taskId}/`)
            .then(response => response.json())
            .then(data => {
                console.log(`Task ${taskId} status: ${data.status}, progress: ${data.progress}`);
                if (callback && typeof callback === 'function') {
                    callback(data);
                }
            })
            .catch(error => {
                console.error('Error checking task status:', error);
                // Remove task if we can't check it
                this.removeTask(taskId);
            });
    },
    
    // Show desktop notification for task completion
    showNotification: function(task) {
        // Check if Notification API is supported
        if (!("Notification" in window)) {
            console.log("This browser does not support desktop notifications");
            // Fall back to dashboard popup
            this.showDashboardPopup(task);
            return;
        }
        
        // Check if permission is already granted
        if (Notification.permission === "granted") {
            this.createNotification(task);
        } 
        // Otherwise, request permission and show if granted
        else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    this.createNotification(task);
                } else {
                    // Fall back to dashboard popup if denied
                    this.showDashboardPopup(task);
                }
            });
        } else {
            // Fall back to dashboard popup if denied
            this.showDashboardPopup(task);
        }
    },
    
    // Create and display a dashboard popup notification
    showDashboardPopup: function(task) {
        // Create dashboard popup modal
        const statusText = {
            'completed': 'completed successfully',
            'error': 'failed with an error',
            'cancelled': 'was cancelled'
        };
        
        // Check if we already have a notification modal
        let modalContainer = document.getElementById('data-miner-notification');
        if (!modalContainer) {
            // Create modal container
            modalContainer = document.createElement('div');
            modalContainer.id = 'data-miner-notification';
            modalContainer.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
            document.body.appendChild(modalContainer);
            
            // Create modal content
            const modalContent = document.createElement('div');
            modalContent.className = 'bg-white rounded-lg shadow-xl w-full max-w-md p-6 border-2 border-indigo-400';
            modalContainer.appendChild(modalContent);
            
            // Add content elements
            modalContent.innerHTML = `
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-bold text-gray-900">Task Complete</h3>
                    <button id="close-notification" class="text-gray-500 hover:text-gray-700">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div id="notification-message" class="mb-6 text-gray-700"></div>
                <div class="flex space-x-3">
                    <button id="view-data-btn" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
                        View Data
                    </button>
                    <button id="close-notification-btn" class="flex-1 border border-gray-300 hover:bg-gray-100 text-gray-700 font-medium py-2 px-4 rounded-lg transition duration-200">
                        Close
                    </button>
                </div>
            `;
            
            // Add event listener for close buttons
            modalContent.querySelector('#close-notification').addEventListener('click', () => {
                modalContainer.remove();
            });
            
            modalContent.querySelector('#close-notification-btn').addEventListener('click', () => {
                modalContainer.remove();
            });
        }
        
        // Update modal content
        const messageElement = modalContainer.querySelector('#notification-message');
        messageElement.textContent = `Your data mining task "${task.name}" has ${statusText[task.status] || 'finished'}. You can now view or download the data.`;
        
        // Update view data button action
        const viewDataBtn = modalContainer.querySelector('#view-data-btn');
        viewDataBtn.addEventListener('click', () => {
            modalContainer.remove();
            
            // For completed tasks, navigate to results if we have a history ID
            if (task.status === 'completed' && task.historyId) {
                window.location.href = `/data_miner/download/${task.historyId}/`;
            } else {
                // Otherwise go to the task list
                window.location.href = '/data_miner/background-tasks/';
            }
        });
        
        // Add flashing effect and play sound if available
        const modalContent = modalContainer.querySelector('.bg-white');
        modalContent.classList.add('notification-flashing');
        
        // Play sound if reminder sound function exists (from user_dashboard)
        if (typeof playReminderSound === 'function') {
            playReminderSound();
            
            // Stop sound when closing
            const closeButtons = modalContainer.querySelectorAll('#close-notification, #close-notification-btn');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    if (typeof stopReminderSound === 'function') {
                        stopReminderSound();
                    }
                });
            });
            
            viewDataBtn.addEventListener('click', () => {
                if (typeof stopReminderSound === 'function') {
                    stopReminderSound();
                }
            });
        }
    },
    
    // Create and display a notification
    createNotification: function(task) {
        const statusText = {
            'completed': 'completed successfully',
            'error': 'failed with an error',
            'cancelled': 'was cancelled'
        };
        
        const options = {
            body: `Task "${task.name}" has ${statusText[task.status] || 'finished'}`,
            icon: '/static/img/logo-icon.png',
            tag: `task-${task.id}`,
            requireInteraction: true
        };
        
        const notification = new Notification("Data Mining Task Update", options);
        
        // Close after 20 seconds even if user doesn't interact
        setTimeout(() => notification.close(), 20000);
        
        // Handle notification click
        notification.onclick = function() {
            window.focus();
            notification.close();
            
            // For completed tasks, navigate to results if we have a history ID
            if (task.status === 'completed' && task.historyId) {
                window.location.href = `/data_miner/download/${task.historyId}/`;
            } else {
                // Otherwise go to the task list
                window.location.href = '/data_miner/background-tasks/';
            }
        };
    },
    
    // Start polling for active tasks on the page
    startPolling: function() {
        const taskItems = document.querySelectorAll('.task-item');
        if (taskItems.length === 0) return;
        
        console.log(`Found ${taskItems.length} task items on page, starting polling`);
        
        // Initial check
        this.updateActiveTasks();
        
        // Continue checking every 5 seconds
        setInterval(() => this.updateActiveTasks(), 5000);
    },
    
    // Update active tasks on the current page
    updateActiveTasks: function() {
        document.querySelectorAll('.task-item').forEach(taskItem => {
            const taskId = taskItem.dataset.taskId;
            if (!taskId) return;
            
            console.log(`Tracking task ${taskId} from page element`);
            
            // Track this task
            this.storeTask(taskId);
            
            this.checkTaskStatus(taskId, (data) => {
                // Update task status in UI
                this.updateTaskUI(taskItem, data);
                
                // If task completed or failed
                if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
                    // Show notification
                    this.showNotification({
                        id: taskId,
                        name: data.task_name || taskItem.querySelector('h4,h3').textContent.trim(),
                        status: data.status,
                        historyId: data.history_id
                    });
                    
                    // Remove from tracked tasks
                    this.removeTask(taskId);
                    
                    // Reload the page to reflect changes
                    console.log(`Task ${taskId} completed, reloading page in 1 second`);
                    setTimeout(() => window.location.reload(), 1000);
                }
            });
        });
    },
    
    // Update task UI with latest status
    updateTaskUI: function(taskItem, data) {
        // Ensure we have a progress value to use
        const progress = data.progress || 0;
        
        // Update all progress elements
        
        // Update progress text
        const progressElements = taskItem.querySelectorAll('.task-progress');
        progressElements.forEach(el => {
            el.textContent = `${progress}%`;
        });
        
        // Update progress text in SVG circle
        const progressText = taskItem.querySelector('.task-progress-text');
        if (progressText) {
            progressText.textContent = `${progress}%`;
        }
        
        // Update progress circle stroke
        const progressCircle = taskItem.querySelector('.task-progress-circle');
        if (progressCircle) {
            // Calculate stroke-dasharray value based on progress
            // stroke-dasharray="circumference * progress/100 circumference"
            const circumference = 2 * Math.PI * 16; // 2πr where r=16
            const dashArray = (circumference * progress / 100) + ' ' + circumference;
            progressCircle.setAttribute('stroke-dasharray', dashArray);
        }
        
        // Update status badge if status has changed
        const statusBadge = taskItem.querySelector('.task-status');
        if (statusBadge && data.status) {
            const statusClass = {
                'pending': 'bg-yellow-100 text-yellow-800',
                'processing': 'bg-blue-100 text-blue-800',
                'completed': 'bg-green-100 text-green-800',
                'failed': 'bg-red-100 text-red-800',
                'cancelled': 'bg-gray-100 text-gray-800',
                'error': 'bg-red-100 text-red-800'
            };
            
            const statusLabel = {
                'pending': 'Pending',
                'processing': 'Processing',
                'completed': 'Completed',
                'failed': 'Failed',
                'cancelled': 'Cancelled',
                'error': 'Error'
            };
            
            const existingBadge = statusBadge.querySelector('span');
            if (existingBadge && data.status in statusClass) {
                // Remove old classes and add new ones
                Object.values(statusClass).forEach(cls => {
                    const classes = cls.split(' ');
                    classes.forEach(c => existingBadge.classList.remove(c));
                });
                
                statusClass[data.status].split(' ').forEach(cls => {
                    existingBadge.classList.add(cls);
                });
                
                // Update text
                existingBadge.textContent = statusLabel[data.status];
            }
        }
        
        // Update task parameters from data if available
        if (data.parameters) {
            // Update keyword
            const keywordElement = taskItem.querySelector('.keyword-value');
            if (keywordElement && data.parameters.keyword) {
                keywordElement.textContent = data.parameters.keyword;
            }
            
            // Update country
            const countryElement = taskItem.querySelector('.country-value');
            if (countryElement && data.parameters.country) {
                countryElement.textContent = data.parameters.country;
            }
            
            // Update max results
            const maxResultsElement = taskItem.querySelector('.max-results-value');
            if (maxResultsElement && data.parameters.max_results) {
                maxResultsElement.textContent = data.parameters.max_results;
            }
            
            // Update max runtime
            const maxRuntimeElement = taskItem.querySelector('.max-runtime-value');
            if (maxRuntimeElement && data.parameters.max_runtime_minutes) {
                maxRuntimeElement.textContent = data.parameters.max_runtime_minutes + ' minutes';
            }
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    DataMinerTasks.init();
});

// Function to call when starting a new task
function trackNewTask(taskId) {
    if (DataMinerTasks && taskId) {
        DataMinerTasks.storeTask(taskId);
    }
}

// Special function for the background_tasks page to ensure it shows all running tasks
document.addEventListener('DOMContentLoaded', function() {
    // If we're on the background tasks page and there are no task items showing
    if (window.location.pathname.includes('/background-tasks') && 
        document.querySelectorAll('.task-item').length === 0) {
        
        // Check if we have stored tasks in localStorage
        const storedTasks = JSON.parse(localStorage.getItem('dataMinerTasks') || '[]');
        
        if (storedTasks.length > 0) {
            // If we have stored tasks but they're not showing on the page, refresh once
            // This helps recover from cases where the page loads before the database is updated
            if (!sessionStorage.getItem('refreshed_for_tasks')) {
                console.log('Stored tasks exist but not showing on page, refreshing once...');
                sessionStorage.setItem('refreshed_for_tasks', 'true');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                // Already refreshed once, clear the flag for next visit
                sessionStorage.removeItem('refreshed_for_tasks');
            }
        }
    } else {
        // Not on the background tasks page, clear the refresh flag
        sessionStorage.removeItem('refreshed_for_tasks');
    }
}); 