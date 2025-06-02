const professionalLink = document.getElementById('registeredProfessionalsLink');
                                const professionalModal = document.getElementById('professionalAccessModal');
                                const modalContent = professionalModal.querySelector('.transform');
                                const mobileNumberStep = document.getElementById('mobileNumberStep');
                                const passcodeStep = document.getElementById('passcodeStep');
                                
                                professionalLink.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    professionalModal.classList.remove('hidden');
                                    setTimeout(() => {
                                        professionalModal.classList.remove('opacity-0');
                                        modalContent.classList.remove('opacity-0', 'scale-95');
                                        modalContent.classList.add('opacity-100', 'scale-100');
                                    }, 50);
                                });
                                
                                function closeProfessionalModal() {
                                    modalContent.classList.remove('opacity-100', 'scale-100');
                                    modalContent.classList.add('opacity-0', 'scale-95');
                                    professionalModal.classList.add('opacity-0');
                                    setTimeout(() => {
                                        professionalModal.classList.add('hidden');
                                        // Reset form
                                        mobileNumberStep.classList.remove('hidden');
                                        passcodeStep.classList.add('hidden');
                                        document.getElementById('combinedInput').value = '';
                                        document.getElementById('passcode').value = '';
                                    }, 300);
                                }
                                
                                async function validateProfessional() {
                                    const combinedInput = document.getElementById('combinedInput').value.trim();
                                    
                                    // Validate input format
                                    const mobilePattern = /^\d{10}/;  // Check if starts with 10 digits
                                    if (!mobilePattern.test(combinedInput)) {
                                        alert('Please enter a valid 10-digit mobile number followed by your security code');
                                        return;
                                    }
                                    
                                    if (combinedInput.length <= 10) {
                                        alert('Please enter your security code after the mobile number');
                                        return;
                                    }
                                    
                                    try {
                                        const response = await fetch('/api/verify-professional/', {
                                            method: 'POST',
                                            headers: {
                                                'Content-Type': 'application/json',
                                                'X-Requested-With': 'XMLHttpRequest'
                                            },
                                            body: JSON.stringify({
                                                combined_input: combinedInput
                                            })
                                        });

                                        if (!response.ok) {
                                            throw new Error(`HTTP error! status: ${response.status}`);
                                        }

                                        const data = await response.json();

                                        if (data.success) {
                                            mobileNumberStep.classList.add('hidden');
                                            passcodeStep.classList.remove('hidden');
                                        } else {
                                            alert(data.error || 'Invalid mobile number or security code');
                                        }
                                    } catch (error) {
                                        console.error('Error details:', error);
                                        alert('An error occurred. Please check your input and try again.');
                                    }
                                }
                                
                                function backToMobileStep() {
                                    passcodeStep.classList.add('hidden');
                                    mobileNumberStep.classList.remove('hidden');
                                }
                                
                                async function verifyPasscode() {
                                    const combinedInput = document.getElementById('combinedInput').value.trim();
                                    const passcode = document.getElementById('passcode').value.trim();
                                    
                                    if (!passcode) {
                                        alert('Please enter your passcode');
                                        return;
                                    }
                                    
                                    try {
                                        const response = await fetch('/api/verify-passcode/', {
                                            method: 'POST',
                                            headers: {
                                                'Content-Type': 'application/json',
                                                'X-Requested-With': 'XMLHttpRequest'
                                            },
                                            body: JSON.stringify({
                                                passcode: passcode
                                            })
                                        });

                                        if (!response.ok) {
                                            throw new Error(`HTTP error! status: ${response.status}`);
                                        }

                                        const data = await response.json();

                                        if (data.success) {
                                            window.location.href = data.redirectUrl;
                                        } else {
                                            alert(data.error || 'Invalid passcode');
                                        }
                                    } catch (error) {
                                        console.error('Error details:', error);
                                        alert('An error occurred. Please check your passcode and try again.');
                                    }
                                }