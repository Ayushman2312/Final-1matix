/**
 * Data Miner Shared JavaScript Functionality
 * Contains utilities for task tracking, notifications, and persistence
 */

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
                
                // Update task progress element
                const progressBar = taskItem.querySelector('.task-progress');
                if (progressBar) {
                    progressBar.textContent = `${data.progress || 0}%`;
                }
                
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
                    
                    // Reload the page to update UI
                    setTimeout(() => window.location.reload(), 1000);
                }
            });
        });
    },
    
    // Update task UI with latest status
    updateTaskUI: function(taskItem, data) {
        // Update progress if element exists
        const progressElement = taskItem.querySelector('.task-progress-text');
        if (progressElement) {
            progressElement.textContent = `${data.progress || 0}%`;
        }
        
        // Update progress circle if element exists
        const progressCircle = taskItem.querySelector('.task-progress-circle');
        if (progressCircle) {
            progressCircle.setAttribute('stroke-dasharray', `${(data.progress || 0) * 1.005} 100`);
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