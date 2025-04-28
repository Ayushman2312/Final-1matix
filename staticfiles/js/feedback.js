const itemsPerPage = 6;  // Show 6 items per page (3 rows of 2)
let currentPage = 1;
let currentFeedbackType = 'all'; // Track the current feedback type

// Debug function
function updateDebug(type, page, error = null) {
    const debugInfo = document.getElementById('debugInfo');
    if (debugInfo) {
        document.getElementById('debugType').textContent = type;
        document.getElementById('debugPage').textContent = page;
        if (error) {
            document.getElementById('debugError').textContent = error;
        }
        debugInfo.style.display = 'block';
    }
}

// Function to update section title based on feedback type
function updateSectionTitle(type) {
    const sectionTitle = document.querySelector('.feedback-section-title');
    if (sectionTitle) {
        let title = 'Recent Feedbacks';
        if (type === 'positive') {
            title = 'Positive Feedbacks (4-5 Stars)';
        } else if (type === 'negative') {
            title = 'Negative Feedbacks (2-3 Stars)';
        } else if (type === 'one_star') {
            title = 'One Star Feedbacks';
        }
        sectionTitle.textContent = title;
    }
}

function loadFeedbacks(page, type = currentFeedbackType) {
    const container = document.getElementById('feedbackContainer');
    if (!container) {
        console.error('Feedback container not found');
        updateDebug(type, page, 'Container not found');
        return;
    }

    // Update current type and debug info
    currentFeedbackType = type;
    updateDebug(type, page);
    
    // Update section title
    updateSectionTitle(type);

    // Show loading state
    container.innerHTML = '<div class="text-center py-4"><p class="text-[#b3b3b3]">Loading feedbacks...</p></div>';

    // Add console log to debug the request
    console.log(`Loading feedbacks: page=${page}, type=${type}`);

    fetch(`/masteradmin/get-feedbacks/?page=${page}&type=${type}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Add console log to debug the response
            console.log('Received feedback data:', data);

            // Clear existing content
            container.innerHTML = '';
            
            if (data.feedbacks && data.feedbacks.length > 0) {
                // Create a grid container for the feedbacks
                const gridContainer = document.createElement('div');
                gridContainer.className = 'grid grid-cols-1 sm:grid-cols-2 gap-4';
                container.appendChild(gridContainer);

                data.feedbacks.forEach(feedback => {
                    const feedbackElement = document.createElement('div');
                    feedbackElement.className = 'bg-[#2a2a2a] p-3 rounded-lg';
                    
                    // Create the star rating HTML
                    const stars = Array(5).fill(0).map((_, index) => {
                        const starClass = index < feedback.rating ? 'text-[#6633FF]' : 'text-gray-300';
                        return `
                            <svg class="w-3 h-3 ${starClass}" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                            </svg>
                        `;
                    }).join('');

                    feedbackElement.innerHTML = `
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center">
                                <div class="w-8 h-8 rounded-full bg-[#6633FF] flex items-center justify-center mr-2">
                                    <span class="text-white text-sm font-bold">${feedback.name.slice(0,1)}</span>
                                </div>
                                <h4 class="text-white font-medium">${feedback.name}</h4>
                            </div>
                            <div class="flex">
                                ${stars}
                            </div>
                        </div>
                        <p class="text-[#b3b3b3] text-xs">${feedback.message}</p>
                        <p class="text-[#777777] text-xs mt-2">${timeSince(new Date(feedback.created_at))} ago</p>
                    `;
                    gridContainer.appendChild(feedbackElement);
                });

                // Update pagination buttons
                const prevBtn = document.getElementById('prevBtn');
                const nextBtn = document.getElementById('nextBtn');
                const currentPageEl = document.getElementById('currentPage');

                if (prevBtn) prevBtn.disabled = page === 1;
                if (nextBtn) nextBtn.disabled = !data.has_more;
                if (currentPageEl) currentPageEl.textContent = data.current_page;
            } else {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <p class="text-[#b3b3b3]">No feedback available for this category</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading feedbacks:', error);
            updateDebug(type, page, error.message);
            container.innerHTML = `
                <div class="text-center py-4">
                    <p class="text-red-500">Error loading feedbacks. Please try again.</p>
                </div>
            `;
        });
}

// Helper function to format time
function timeSince(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = seconds / 31536000;
    
    if (interval > 1) return Math.floor(interval) + " years";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes";
    return Math.floor(seconds) + " seconds";
}

// Function to safely add event listeners
function addClickHandler(elementId, handler) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener('click', handler);
    } else {
        console.warn(`Element with id '${elementId}' not found`);
        updateDebug(currentFeedbackType, currentPage, `Button '${elementId}' not found`);
    }
}

// Load initial feedbacks and set up click handlers
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Setting up handlers');
    
    // Load initial feedbacks
    loadFeedbacks(currentPage);

    // Set up click handlers for the view detail buttons
    addClickHandler('viewAllFeedbacks', () => {
        console.log('All Feedbacks clicked');
        currentPage = 1;
        loadFeedbacks(1, 'all');
    });

    addClickHandler('viewPositiveFeedbacks', () => {
        console.log('Positive Feedbacks clicked');
        currentPage = 1;
        loadFeedbacks(1, 'positive');
    });

    addClickHandler('viewNegativeFeedbacks', () => {
        console.log('Negative Feedbacks clicked');
        currentPage = 1;
        loadFeedbacks(1, 'negative');
    });

    addClickHandler('viewOneStarFeedbacks', () => {
        console.log('One Star Feedbacks clicked');
        currentPage = 1;
        loadFeedbacks(1, 'one_star');
    });
    
    // Add pagination event listeners
    addClickHandler('prevBtn', () => {
        if (currentPage > 1) {
            currentPage--;
            loadFeedbacks(currentPage, currentFeedbackType);
        }
    });

    addClickHandler('nextBtn', () => {
        currentPage++;
        loadFeedbacks(currentPage, currentFeedbackType);
    });
});

// Auto-refresh feedbacks every 30 seconds
setInterval(() => {
    loadFeedbacks(currentPage, currentFeedbackType);
}, 30000);