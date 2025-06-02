function closeWelcomeModal() {
    const welcomeModal = document.getElementById('welcomeModal');
    const formCard = document.querySelector('.form-card');
    
    if (welcomeModal && formCard) {
        welcomeModal.style.display = 'none';
        formCard.style.display = 'flex';
        // Save welcome modal state
        localStorage.setItem('welcomeModalClosed', 'true');
    }
}

// Check welcome modal state on page load
document.addEventListener('DOMContentLoaded', function() {
    const welcomeModal = document.getElementById('welcomeModal');
    const formCard = document.querySelector('.form-card');
    
    if (!welcomeModal || !formCard) {
        return;
    }
    
    const welcomeModalClosed = localStorage.getItem('welcomeModalClosed');
    if (welcomeModalClosed === 'true') {
        welcomeModal.style.display = 'none';
        formCard.style.display = 'flex';
    } else {
        formCard.style.display = 'none';
    }
    
    // Restore form data from localStorage
    restoreFormData();
    
    // Restore current step
    const savedStep = localStorage.getItem('currentFormStep');
    if (savedStep) {
        window.currentStep = parseInt(savedStep);
        updateFormDisplay();
    }
});

// Save form data to localStorage
function saveFormData() {
    const form = document.getElementById('registrationForm');
    if (!form) {
        return;
    }
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        if (!key.includes('file')) { // Don't save file inputs
            data[key] = value;
        }
    }
    
    localStorage.setItem('formData', JSON.stringify(data));
    // Save current step whenever form data changes
    if (typeof window.currentStep !== 'undefined') {
        localStorage.setItem('currentFormStep', window.currentStep.toString());
    }
}

// Restore form data from localStorage
function restoreFormData() {
    const form = document.getElementById('registrationForm');
    if (!form) {
        return;
    }
    
    // Restore current step first
    const savedStep = localStorage.getItem('currentFormStep');
    if (savedStep) {
        window.currentStep = parseInt(savedStep);
        updateFormDisplay(); // Show the correct step
    }
    
    const savedData = localStorage.getItem('formData');
    if (savedData) {
        const data = JSON.parse(savedData);
        
        for (let key in data) {
            const input = form.querySelector(`[name="${key}"]`); // Use querySelector to find by name attribute
            if (input) {
                // Handle different input types
                if (input.type === 'checkbox') {
                    input.checked = data[key] === 'true';
                } else if (input.type === 'radio') {
                    const radio = form.querySelector(`[name="${key}"][value="${data[key]}"]`);
                    if (radio) {
                        radio.checked = true;
                    }
                } else if (input.tagName === 'SELECT') {
                    // Trigger change event for select elements
                    input.value = data[key];
                    const event = new Event('change');
                    input.dispatchEvent(event);
                } else {
                    input.value = data[key];
                }
                
                // Trigger input event to handle any dependent validations
                const event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
            }
        }
    }
}

// Save form data when inputs change
const registrationForm = document.getElementById('registrationForm');
if (registrationForm) {
    registrationForm.addEventListener('input', function(e) {
        if (!e.target.matches('input[type="file"]')) { // Don't save file inputs
            saveFormData();
        }
    });

    // Also save form data when select elements change
    registrationForm.addEventListener('change', function(e) {
        if (e.target.tagName === 'SELECT') {
            saveFormData();
        }
    });

    // Clear localStorage on successful form submission
    registrationForm.addEventListener('submit', function() {
        localStorage.removeItem('formData');
        localStorage.removeItem('currentFormStep');
        localStorage.removeItem('welcomeModalClosed');
    });
}

const dobInput = document.getElementById('dob');
const dobError = document.getElementById('dob-error');

if (dobInput && dobError) {
    // Set max date to today
    const today = new Date();
    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() - 18);
    dobInput.max = maxDate.toISOString().split('T')[0];

    dobInput.addEventListener('change', function() {
        const dob = new Date(this.value);
        let age = today.getFullYear() - dob.getFullYear();
        const monthDiff = today.getMonth() - dob.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
            age--;
        }

        if (age < 18) {
            dobError.classList.remove('hidden');
            this.setCustomValidity('You must be at least 18 years old');
            this.classList.add('border-red-500');
            this.value = ''; // Clear the input
        } else {
            dobError.classList.add('hidden');
            this.setCustomValidity('');
            this.classList.remove('border-red-500');
        }
    });
}

// Function to toggle required attribute based on visibility
function toggleRequiredFields() {
    const corporateReferences = document.getElementById('corporateReferences');
    if (!corporateReferences) {
        return;
    }
    
    const inputs = corporateReferences.getElementsByClassName('corporate-input');
    
    // Check if the corporate references section is hidden
    const isHidden = corporateReferences.classList.contains('hidden');
    
    // Toggle required attribute for all inputs
    for(let input of inputs) {
        input.required = !isHidden;
    }
}

// Run on page load
document.addEventListener('DOMContentLoaded', toggleRequiredFields);

// Run whenever the hidden class is toggled
const corporateReferences = document.getElementById('corporateReferences');
if (corporateReferences) {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === "class") {
                toggleRequiredFields();
            }
        });
    });

    observer.observe(corporateReferences, {
        attributes: true
    });
}

// Email validation
const email1Input = document.getElementById('family_ref1_email');
const email2Input = document.getElementById('family_ref2_email');
const emailError = document.getElementById('email-error');

if (email1Input && email2Input && emailError) {
    function validateEmails() {
        const email1 = email1Input.value.toLowerCase();
        const email2 = email2Input.value.toLowerCase();
        
        if (email1 && email2 && email1 === email2) {
            emailError.classList.remove('hidden');
            email2Input.setCustomValidity('Email addresses must be different');
        } else {
            emailError.classList.add('hidden');
            email2Input.setCustomValidity('');
        }
    }

    email1Input.addEventListener('input', validateEmails);
    email2Input.addEventListener('input', validateEmails);
}

// Update the currentStep variable initialization to use localStorage
let currentStep = parseInt(localStorage.getItem('currentFormStep')) || 1;
const totalSteps = 6;

const nextBtn = document.getElementById('nextBtn');
if (nextBtn) {
    nextBtn.addEventListener('click', () => {
        if (validateCurrentStep()) {
            if (currentStep < totalSteps) {
                currentStep++;
                localStorage.setItem('currentFormStep', currentStep.toString());
                updateFormDisplay();
            } else {
                const form = document.getElementById('registrationForm');
                if (form) {
                    form.submit();
                }
            }
        }
    });
}

const prevBtn = document.getElementById('prevBtn');
if (prevBtn) {
    prevBtn.addEventListener('click', () => {
        if (currentStep > 1) {
            currentStep--;
            localStorage.setItem('currentFormStep', currentStep.toString());
            updateFormDisplay();
        }
    });
}

const experienceType = document.getElementById('experienceType');
if (experienceType) {
    experienceType.addEventListener('change', (e) => {
        const corporateRefs = document.getElementById('corporateReferences');
        const experienceDocs = document.getElementById('experienceDocs');
        if (corporateRefs && experienceDocs) {
            if (e.target.value === 'experienced') {
                corporateRefs.classList.remove('hidden');
                experienceDocs.classList.remove('hidden');
            } else {
                corporateRefs.classList.add('hidden');
                experienceDocs.classList.add('hidden');
            }
        }
    });
}

function updateFormDisplay() {
    document.querySelectorAll('.form-step').forEach(step => step.classList.remove('active'));
    const currentStepElement = document.getElementById(`step${currentStep}`);
    if (currentStepElement) {
        currentStepElement.classList.add('active');
    }
    
    document.querySelectorAll('.step-indicator').forEach((indicator, index) => {
        if (index + 1 === currentStep) {
            indicator.classList.add('active');
        } else {
            indicator.classList.remove('active');
        }
    });

    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (prevBtn) {
        prevBtn.style.display = currentStep === 1 ? 'none' : 'block';
    }
    if (nextBtn) {
        nextBtn.textContent = currentStep === totalSteps ? 'Submit' : 'Next';
    }
}

function validateCurrentStep() {
    const currentStepElement = document.getElementById(`step${currentStep}`);
    if (!currentStepElement) {
        return false;
    }
    
    const requiredFields = currentStepElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value) {
            isValid = false;
            field.classList.add('border-red-500');
            // Add error message below field
            const errorMsg = document.createElement('p');
            errorMsg.className = 'text-red-500 text-sm mt-1';
            errorMsg.textContent = 'This field is required';
            field.parentNode.appendChild(errorMsg);
        } else {
            field.classList.remove('border-red-500');
            // Remove any existing error messages
            const existingError = field.parentNode.querySelector('.text-red-500');
            if (existingError) {
                existingError.remove();
            }
        }
    });

    if (currentStep === 1) {
        const password = document.getElementById('password');
        const confirmPassword = document.getElementById('confirmPassword');
        
        if (password && confirmPassword) {
            if (password.value !== confirmPassword.value) {
                isValid = false;
                confirmPassword.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Passwords do not match';
                confirmPassword.parentNode.appendChild(errorMsg);
            }

            if (password.pattern && !password.value.match(password.pattern)) {
                isValid = false;
                password.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Password must contain at least 8 characters, including letters, numbers, and special characters';
                password.parentNode.appendChild(errorMsg);
            }
        }
    }

    if (currentStep === 2) {
        const dob = document.getElementById('dob');
        const pan = document.getElementById('pan');
        const aadhaar = document.getElementById('aadhaar');

        if (dob && dob.value) {
            const dobDate = new Date(dob.value);
            const today = new Date();
            let age = today.getFullYear() - dobDate.getFullYear();
            const monthDiff = today.getMonth() - dobDate.getMonth();
            
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dobDate.getDate())) {
                age--;
            }

            if (age < 18) {
                isValid = false;
                dob.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'You must be at least 18 years old';
                dob.parentNode.appendChild(errorMsg);
            }
        }

        // PAN validation - 10 characters, alphanumeric
        if (pan && pan.value) {
            const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
            if (!panRegex.test(pan.value)) {
                isValid = false;
                pan.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Invalid PAN number format';
                pan.parentNode.appendChild(errorMsg);
            }
        }

        // Aadhaar validation - 12 digits
        if (aadhaar && aadhaar.value) {
            const aadhaarRegex = /^\d{12}$/;
            if (!aadhaarRegex.test(aadhaar.value)) {
                isValid = false;
                aadhaar.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Aadhaar number must be 12 digits';
                aadhaar.parentNode.appendChild(errorMsg);
            }
        }
    }

    if (currentStep === 3) {
        // Bank IFSC validation - 11 characters, alphanumeric format
        const ifsc = document.getElementById('ifsc');
        if (ifsc && ifsc.value) {
            const ifscRegex = /^[A-Z]{4}0[A-Z0-9]{6}$/;
            if (!ifscRegex.test(ifsc.value)) {
                isValid = false;
                ifsc.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Invalid IFSC code format';
                ifsc.parentNode.appendChild(errorMsg);
            }
        }

        // Bank Account Number validation - 9 to 18 digits
        const accountNumber = document.getElementById('account_number'); 
        if (accountNumber && accountNumber.value) {
            const accountRegex = /^\d{9,18}$/;
            if (!accountRegex.test(accountNumber.value)) {
                isValid = false;
                accountNumber.classList.add('border-red-500');
                const errorMsg = document.createElement('p');
                errorMsg.className = 'text-red-500 text-sm mt-1';
                errorMsg.textContent = 'Account number must be between 9 and 18 digits';
                accountNumber.parentNode.appendChild(errorMsg);
            }
        }
    }

    if (!isValid) {
        // Scroll to first error
        const firstError = currentStepElement.querySelector('.border-red-500');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    return isValid;
}

// Initialize the form with email and passcode from URL parameters
window.addEventListener('load', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const emailInput = document.getElementById('email');
    const passcodeInput = document.getElementById('passcode');
    
    if (emailInput) {
        emailInput.value = urlParams.get('email') || '';
    }
    if (passcodeInput) {
        passcodeInput.value = urlParams.get('passcode') || '';
    }
});

// Add form submission handler
const registrationFormSubmit = document.getElementById('registrationForm');
if (registrationFormSubmit) {
    registrationFormSubmit.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        try {
            const formData = new FormData(this);
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }
            
            const response = await fetch('/employee/register/{{ employee_passcode }}/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken.value
                }
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                // Clear form data from localStorage
                localStorage.removeItem('formData');
                localStorage.removeItem('currentFormStep');
                localStorage.removeItem('welcomeModalClosed');
                
                // Show success modal using SweetAlert2
                await Swal.fire({
                    icon: 'success',
                    title: 'Registration Successful!',
                    text: `${data.message}\nYour passcode is: ${data.passcode}`,
                    confirmButtonColor: '#10B981',
                    timer: 3000,
                    timerProgressBar: true
                });
                
                // Redirect after modal is closed
                window.location.href = '/';
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Registration Failed',
                    text: data.message || 'Please try again.',
                    confirmButtonColor: '#EF4444'
                });
            }
        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'An error occurred during registration. Please try again.',
                confirmButtonColor: '#EF4444'
            });
        }
    });
}