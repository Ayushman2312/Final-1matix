// document.getElementById('sendOtp').addEventListener('click', function () {
//     const email = document.getElementById('email').value;
//     if (!email) {
//         alert('Please enter an email address');
//         return;
//     }

//     // Show loading state
//     const sendOtpButton = document.getElementById('sendOtp');
//     sendOtpButton.disabled = true;
//     sendOtpButton.textContent = 'Sending...';

//     fetch('/agents/send_otp/', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//         },
//         body: JSON.stringify({ email: email }),
//         credentials: 'same-origin'
//     })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === 'success') {
//                 document.getElementById('successMessage').textContent = data.message;
//                 document.getElementById('successMessage').classList.remove('hidden');
//                 document.getElementById('errorMessage').classList.add('hidden');
//                 document.getElementById('otpSection').classList.remove('hidden');
//             } else {
//                 throw new Error(data.error || 'Failed to send OTP');
//             }
//         })
//         .catch(error => {
//             document.getElementById('errorMessage').textContent = error.message;
//             document.getElementById('errorMessage').classList.remove('hidden');
//             document.getElementById('successMessage').classList.add('hidden');
//         })
//         .finally(() => {
//             // Reset button state
//             sendOtpButton.disabled = false;
//             sendOtpButton.textContent = 'Send OTP';
//         });
// });

// document.getElementById('verifyOtp').addEventListener('click', function () {
//     const otp = document.getElementById('otp').value;
//     if (!otp) {
//         alert('Please enter OTP');
//         return;
//     }

//     fetch('/agents/verify_otp/', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
//         },
//         body: JSON.stringify({ otp: otp }),
//         credentials: 'same-origin'
//     })
//         .then(response => response.json())
//         .then(data => {
//             if (data.status === 'success') {
//                 document.getElementById('successMessage').textContent = data.message;
//                 document.getElementById('successMessage').classList.remove('hidden');
//                 document.getElementById('errorMessage').classList.add('hidden');
//                 document.getElementById('passwordSection').classList.remove('hidden');
//             } else {
//                 throw new Error(data.error || 'Invalid OTP');
//             }
//         })
//         .catch(error => {
//             document.getElementById('errorMessage').textContent = error.message;
//             document.getElementById('errorMessage').classList.remove('hidden');
//             document.getElementById('successMessage').classList.add('hidden');
//         });
// });

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

    fetch('/agents/login/', {
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

    fetch("/agents/login/", {
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

