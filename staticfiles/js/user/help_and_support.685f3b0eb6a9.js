function showArticleModal(title, imageUrl, content) {
    const modal = document.getElementById('articleModal');
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalImage').src = imageUrl;
    document.getElementById('modalContent').innerHTML = content;
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent scrolling when modal is open
}

function closeArticleModal() {
    const modal = document.getElementById('articleModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Restore scrolling
}

// Close modal when clicking outside
document.getElementById('articleModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeArticleModal();
    }
});

function toggleAccordion(element) {
    const content = element.nextElementSibling;
    const arrow = element.querySelector('svg');
    
    content.classList.toggle('hidden');
    arrow.classList.toggle('rotate-180');
}
function openSupportModal(type) {
    const modal = document.getElementById('supportModal');
    const modalTitle = document.getElementById('supportModalTitle');
    const departmentSelect = document.getElementById('supportDepartment');
    
    // Set title and pre-select department based on clicked support type
    modalTitle.textContent = type;
    
    // Pre-select the department in dropdown
    for(let i = 0; i < departmentSelect.options.length; i++) {
        if(departmentSelect.options[i].value.toLowerCase() === type.toLowerCase()) {
            departmentSelect.selectedIndex = i;
            break;
        }
    }
    
    // Show modal with fade-in effect
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.add('opacity-100');
        modal.querySelector('.flex > div').classList.add('scale-100');
    }, 10);
    
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

function closeSupportModal() {
    const modal = document.getElementById('supportModal');
    const modalContent = modal.querySelector('.flex > div');
    
    // Hide with animation
    modal.classList.remove('opacity-100');
    modalContent.classList.remove('scale-100');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto'; // Restore scrolling
    }, 300);
}

// Close modal when clicking outside
document.getElementById('supportModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeSupportModal();
    }
});

// Handle form submission
document.getElementById('supportForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const department = document.getElementById('supportDepartment').value;
    const priority = document.getElementById('supportPriority').value;
    const message = document.getElementById('supportMessage').value;
    const mobile = document.getElementById('supportMobile').value;
    
    // Validate form
    if (!message || !mobile) {
        alert('Please fill in all required fields');
        return;
    }
    
    // Here you would typically send the data to your backend
    // For now, just show a success message and close the modal
    alert('Your support request has been submitted. We will get back to you soon.');
    closeSupportModal();
});
function openTrainingModal() {
    const modal = document.getElementById('trainingModal');
    if (!modal) return;
    
    // Show modal with fade-in effect
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.add('opacity-100');
        modal.querySelector('.flex > div').classList.add('scale-100');
    }, 10);
    
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

function closeTrainingModal() {
    const modal = document.getElementById('trainingModal');
    if (!modal) return;
    
    const modalContent = modal.querySelector('.flex > div');
    
    // Hide with animation
    modal.classList.remove('opacity-100');
    modalContent.classList.remove('scale-100');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto'; // Restore scrolling
    }, 300);
}

// Close modal when clicking outside
document.getElementById('trainingModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeTrainingModal();
    }
});

// Handle form submission
document.getElementById('trainingForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const mobile = document.getElementById('trainingMobile').value;
    
    // Validate form
    if (!mobile) {
        alert('Please enter your mobile number');
        return;
    }
    
    // Here you would typically send the data to your backend
    // For now, just show a success message and close the modal
    alert('Your training request has been submitted. We will get back to you soon.');
    closeTrainingModal();
});
function openFeedbackModal() {
    const modal = document.getElementById('feedbackModal');
    if (!modal) return;
    
    // Reset form
    document.getElementById('feedbackForm').reset();
    document.getElementById('feedbackRating').value = "0";
    const stars = document.querySelectorAll('.star');
    stars.forEach(star => {
        star.classList.remove('text-[#6633FF]');
        star.classList.add('text-gray-300');
    });
    
    // Show modal with fade-in effect
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.add('opacity-100');
        modal.querySelector('.flex > div').classList.add('scale-100');
    }, 10);
    
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

function closeFeedbackModal() {
    const modal = document.getElementById('feedbackModal');
    if (!modal) return;
    
    const modalContent = modal.querySelector('.flex > div');
    
    // Hide with animation
    modal.classList.remove('opacity-100');
    modalContent.classList.remove('scale-100');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto'; // Restore scrolling
    }, 300);
}

// Close modal when clicking outside
document.getElementById('feedbackModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeFeedbackModal();
    }
});

// Star rating functionality
document.addEventListener('DOMContentLoaded', function() {
    const stars = document.querySelectorAll('.star');
    const ratingInput = document.getElementById('feedbackRating');
    
    stars.forEach(star => {
        star.addEventListener('click', function() {
            const rating = this.getAttribute('data-rating');
            ratingInput.value = rating;
            
            // Update star colors
            stars.forEach(s => {
                const starRating = s.getAttribute('data-rating');
                if (starRating <= rating) {
                    s.classList.remove('text-gray-300');
                    s.classList.add('text-[#6633FF]');
                } else {
                    s.classList.remove('text-[#6633FF]');
                    s.classList.add('text-gray-300');
                }
            });
        });
        
        // Hover effects
        star.addEventListener('mouseenter', function() {
            const rating = this.getAttribute('data-rating');
            stars.forEach(s => {
                const starRating = s.getAttribute('data-rating');
                if (starRating <= rating) {
                    s.classList.add('text-[#6633FF]/80');
                }
            });
        });
        
        star.addEventListener('mouseleave', function() {
            const selectedRating = ratingInput.value;
            stars.forEach(s => {
                const starRating = s.getAttribute('data-rating');
                s.classList.remove('text-[#6633FF]/80');
                
                if (starRating <= selectedRating) {
                    s.classList.add('text-[#6633FF]');
                } else {
                    s.classList.add('text-gray-300');
                }
            });
        });
    });
});

// Handle form submission with AJAX
document.getElementById('feedbackForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const rating = document.getElementById('feedbackRating').value;
    const message = document.getElementById('feedbackMessage').value;
    const name = document.getElementById('feedbackName').value;
    
    // Validate form
    if (rating === "0") {
        alert('Please select a rating');
        return;
    }
    
    if (!message) {
        alert('Please enter your message');
        return;
    }
    
    if (!name) {
        alert('Please enter your name');
        return;
    }
    
    // Show loading state
    const submitButton = this.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';
    
    // Prepare data for AJAX submission
    const data = {
        rating: rating,
        message: message,
        name: name
    };
    
    // AJAX POST request
    fetch('/user/api/feedback/', {  // Make sure the URL matches your urls.py configuration
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            closeFeedbackModal();
            // Reset form
            document.getElementById('feedbackForm').reset();
            document.getElementById('feedbackRating').value = "0";
            const stars = document.querySelectorAll('.star');
            stars.forEach(star => {
                star.classList.remove('text-[#6633FF]');
                star.classList.add('text-gray-300');
            });
        } else {
            throw new Error(data.message || 'Something went wrong');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || 'There was a problem submitting your feedback. Please try again.');
    })
    .finally(() => {
        // Reset button state
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
    });
});

// Helper function to get CSRF token from cookies
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
function selectBox(boxId) {
    // Remove selected class from all boxes
    const allBoxes = document.querySelectorAll('[id$="Box"]');
    allBoxes.forEach(box => {
        box.classList.remove('bg-[rgb(230,228,232)]');
        box.classList.add('bg-white');
    });
    
    // Add selected class to clicked box
    const selectedBox = document.getElementById(boxId);
    selectedBox.classList.remove('bg-white');
    selectedBox.classList.add('bg-[rgb(230,228,232)]');
}