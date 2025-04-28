document.addEventListener('DOMContentLoaded', function() {
    const emailForm = document.getElementById('emailForm');
    const otpForm = document.getElementById('otpForm');
    const passwordForm = document.getElementById('passwordForm');
    const errorMessage = document.getElementById('errorMessage');

    // Handle email form submission
    emailForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const email = document.getElementById('email').value;
        
        try {
            const response = await fetch('/customersupport/send_otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: JSON.stringify({ email: email }),
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                emailForm.classList.add('hidden');
                otpForm.classList.remove('hidden');
                errorMessage.classList.add('hidden');
            } else {
                errorMessage.textContent = data.error;
                errorMessage.classList.remove('hidden');
            }
        } catch (error) {
            errorMessage.textContent = 'An error occurred. Please try again.';
            errorMessage.classList.remove('hidden');
        }
    });

    // Handle OTP form submission
    otpForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const otp = document.getElementById('otp').value;
        
        try {
            const response = await fetch('/customersupport/verify_otp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ otp: otp })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                otpForm.classList.add('hidden');
                passwordForm.classList.remove('hidden');
                errorMessage.classList.add('hidden');
            } else {
                errorMessage.textContent = data.error;
                errorMessage.classList.remove('hidden');
            }
        } catch (error) {
            errorMessage.textContent = 'An error occurred. Please try again.';
            errorMessage.classList.remove('hidden');
        }
    });

    // Handle password form submission
    passwordForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch('/customersupport/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    email: email,
                    password: password 
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                window.location.href = data.redirect_url;
            } else {
                errorMessage.textContent = data.error;
                errorMessage.classList.remove('hidden');
            }
        } catch (error) {
            errorMessage.textContent = 'An error occurred. Please try again.';
            errorMessage.classList.remove('hidden');
        }
    });
});

function toggleRememberMe() {
    const checkbox = document.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
}

document.getElementById('sendOtp').addEventListener('click', function () {
    const email = document.getElementById('email').value;
    if (!email) {
        alert('Please enter an email address');
        return;
    }

    // Show loading state
    const sendOtpButton = document.getElementById('sendOtp');
    sendOtpButton.disabled = true;
    sendOtpButton.textContent = 'Sending...';

    // Get CSRF token from cookie
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

    const csrfToken = getCookie('csrftoken');

    fetch('/customersupport/send_otp/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({ email: email }),
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to send OTP');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('successMessage').textContent = data.message;
                document.getElementById('successMessage').classList.remove('hidden');
                document.getElementById('errorMessage').classList.add('hidden');
                document.getElementById('otpSection').classList.remove('hidden');
            } else {
                throw new Error(data.error || 'Failed to send OTP');
            }
        })
        .catch(error => {
            document.getElementById('errorMessage').textContent = error.message;
            document.getElementById('errorMessage').classList.remove('hidden');
            document.getElementById('successMessage').classList.add('hidden');
        })
        .finally(() => {
            // Reset button state
            sendOtpButton.disabled = false;
            sendOtpButton.textContent = 'Send OTP';
        });
});

document.getElementById('verifyOtp').addEventListener('click', function () {
    const otp = document.getElementById('otp').value;
    if (!otp) {
        alert('Please enter OTP');
        return;
    }

    fetch('/customersupport/verify_otp/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ otp: otp }),
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('successMessage').textContent = data.message;
                document.getElementById('successMessage').classList.remove('hidden');
                document.getElementById('errorMessage').classList.add('hidden');
                document.getElementById('passwordSection').classList.remove('hidden');
            } else {
                throw new Error(data.error || 'Invalid OTP');
            }
        })
        .catch(error => {
            document.getElementById('errorMessage').textContent = error.message;
            document.getElementById('errorMessage').classList.remove('hidden');
            document.getElementById('successMessage').classList.add('hidden');
        });
});

document.getElementById('loginForm').addEventListener('submit', function (event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (!email || !password) {
        alert('Please enter both email and password');
        return;
    }

    // Get CSRF token from cookie
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

    fetch('/customersupport/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value // Use the cookie value instead of form field
        },
        body: JSON.stringify({ email: email, password: password }),
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = data.redirect_url;
            } else {
                throw new Error(data.error || 'Login failed');
            }
        })
        .catch(error => {
            document.getElementById('errorMessage').textContent = error.message;
            document.getElementById('errorMessage').classList.remove('hidden');
            document.getElementById('successMessage').classList.add('hidden');
        });
});
document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    fetch("/customersupport/login/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ email: email, password: password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            sessionStorage.setItem('email', email);  // Store agent email in sessionStorage
            window.location.href = data.redirect_url;
        } else {
            document.getElementById('errorMessage').textContent = data.error;
            document.getElementById('errorMessage').classList.remove('hidden');
        }
    })
    .catch(error => console.error("Login error:", error));
});

