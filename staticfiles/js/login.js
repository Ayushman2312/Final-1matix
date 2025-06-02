function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function sendEmailOTP() {
    const email = document.getElementById('email').value;
    fetch('/masteradmin/signup/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: new URLSearchParams({
            'action': 'send_email_otp',
            'email': email
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('emailStep').classList.add('hidden');
            document.getElementById('emailOTPStep').classList.remove('hidden');
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        showError('An error occurred. Please try again.');
        console.error('Error:', error);
    });
    document.getElementById('emailStep').classList.add('hidden');
    document.getElementById('emailOTPStep').classList.remove('hidden');
}

function verifyEmailOTP() {
    const emailOTP = document.getElementById('emailOTP').value;
    fetch('/masteradmin/signup/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: new URLSearchParams({
            'action': 'verify_email_otp',
            'email_otp': emailOTP
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('emailOTPStep').classList.add('hidden');
            document.getElementById('mobileStep').classList.remove('hidden');
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        showError('An error occurred. Please try again.');
        console.error('Error:', error);
    });
}

function sendMobileOTP() {
    const mobile = document.getElementById('mobile').value;
    // Add AJAX call to send mobile OTP
    document.getElementById('mobileStep').classList.add('hidden');
    document.getElementById('mobileOTPStep').classList.remove('hidden');
}

function verifyMobileOTP() {
    const mobileOTP = document.getElementById('mobileOTP').value;
    // Add AJAX call to verify mobile OTP
    document.getElementById('mobileOTPStep').classList.add('hidden');
    document.getElementById('passwordStep').classList.remove('hidden');
}

function submitLogin() {
    const password = document.getElementById('password').value;
    // Add AJAX call to verify password and complete login
    // On success, redirect to dashboard
}
AOS.init({
    duration: 1000,
    once: true
});
function submitSignup() {
    const password = document.getElementById('password').value;
    fetch('/masteradmin/signup/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: new URLSearchParams({
            'action': 'signup',
            'password': password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            window.location.href = data.redirect;
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        showError('An error occurred. Please try again.');
        console.error('Error:', error);
    });
}
