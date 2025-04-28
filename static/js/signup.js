AOS.init();
        // Form validation
        function validateForm(event) {
            event.preventDefault();
            let isValid = true;

            // Reset errors
            document.querySelectorAll('.form-error').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('input').forEach(el => el.classList.remove('input-error'));

            // Email validation
            const email = document.getElementById('email');
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email.value)) {
                showError('email', 'Please enter a valid email address');
                isValid = false;
            }

            // Mobile validation
            const mobile = document.getElementById('mobile');
            const mobileRegex = /^\+?[\d\s-]{10,}$/;
            if (!mobileRegex.test(mobile.value)) {
                showError('mobile', 'Please enter a valid mobile number');
                isValid = false;
            }

            // Password validation
            const password = document.getElementById('password');
            if (password.value.length < 8) {
                showError('password', 'Password must be at least 8 characters long');
                isValid = false;
            }

            // Confirm password validation
            const confirmPassword = document.getElementById('confirmPassword');
            if (password.value !== confirmPassword.value) {
                showError('confirmPassword', 'Passwords do not match');
                isValid = false;
            }

            if (isValid) {
                // Submit form
                document.getElementById('signupForm').submit();
            }
        }

        function showError(fieldId, message) {
            const errorDiv = document.getElementById(fieldId + 'Error');
            const input = document.getElementById(fieldId);
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
            input.classList.add('input-error');
        }