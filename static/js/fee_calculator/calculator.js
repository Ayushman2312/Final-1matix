// Function to get CSRF token from cookie
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

function calculateFees(event) {
    event.preventDefault();
    
    // Reset all values to 0 before new calculation
    resetCalculatorValues();
    
    // Get form element and create FormData
    const form = document.getElementById('calculatorForm');
    const formData = new FormData(form);
    
    // Get the CSRF token directly from the form's input field
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]').value;
    
    console.log("CSRF Token:", csrfToken);
    
    // Ensure the CSRF token is in the FormData as well
    // This is the most reliable approach for Django
    if (!formData.has('csrfmiddlewaretoken')) {
        formData.append('csrfmiddlewaretoken', csrfToken);
    }
    
    // Convert FormData to URL-encoded string for better compatibility
    const urlEncodedData = new URLSearchParams(formData).toString();
    
    // Prepare fetch options with proper headers for form submission
    const options = {
        method: 'POST',
        body: urlEncodedData,
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        credentials: 'same-origin',
        mode: 'same-origin',
        cache: 'no-store'
    };

    fetch('/fee_calculator/', options)
    .then(response => {
        if (!response.ok) {
            console.error("Response not OK:", response.status, response.statusText);
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(response => {
        console.log('Raw response:', response);
        
        if (!response.data || !response.data.programs) {
            throw new Error('Invalid response format');
        }

        // Show results section
        document.getElementById('results').style.display = 'grid';

        const { programs } = response.data;
        const gstAmount = response.data.gst_amount;

        // Update each fulfillment method
        const methodMappings = {
            'EASY_SHIP': 'easyShip',
            'FBA': 'fba',
            'SELLER_FLEX': 'sellerFlex'
        };

        Object.entries(methodMappings).forEach(([backendKey, frontendPrefix]) => {
            const programData = programs[backendKey];
            console.log(`Processing ${backendKey}:`, programData);
            
            if (programData) {
                // Update locations data
                if (programData.locations) {
                    // Set of locations depends on program type
                    let programLocations;
                    if (backendKey === 'FBA') {
                        programLocations = ['regional', 'national'];
                    } else { // EASY_SHIP or SELLER_FLEX
                        programLocations = ['flat'];
                    }
                    
                    programLocations.forEach(zone => {
                        const zoneData = programData.locations[zone];
                        console.log(`${backendKey} ${zone} data:`, zoneData);
                        
                        if (zoneData) {
                            const capitalizedZone = zone.charAt(0).toUpperCase() + zone.slice(1);
                            
                            // Update shipping fee
                            const shippingElement = document.getElementById(`${frontendPrefix}${capitalizedZone}Fee`);
                            if (shippingElement) {
                                const shippingFee = Number(zoneData.shipping_fee || 0);
                                console.log(`Setting ${frontendPrefix}${capitalizedZone}Fee:`, shippingFee);
                                shippingElement.textContent = `₹${shippingFee.toFixed(2)}`;
                            }

                            // Update profit
                            const profitElement = document.getElementById(`${frontendPrefix}${capitalizedZone}Profit`);
                            if (profitElement) {
                                const profit = Number(zoneData.net_amount || 0);
                                console.log(`Setting ${frontendPrefix}${capitalizedZone}Profit:`, profit);
                                profitElement.textContent = `₹${profit.toFixed(2)}`;
                                profitElement.classList.remove('text-red-600', 'text-emerald-600');
                                profitElement.classList.add(profit < 0 ? 'text-red-600' : 'text-emerald-600');
                            }
                        }
                    });

                    // No longer need average values with the new structure
                }

                // Update fees
                const fees = {
                    'ClosingFee': programData.closing_fee || 0,
                    'ReferralFee': programData.referral_fee || 0,
                    'GstFee': gstAmount || 0
                };

                Object.entries(fees).forEach(([key, value]) => {
                    const element = document.getElementById(`${frontendPrefix}${key}`);
                    if (element) {
                        const fee = Number(value);
                        console.log(`Setting ${frontendPrefix}${key}:`, fee);
                        element.textContent = `₹${fee.toFixed(2)}`;
                    }
                });
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to calculate fees. Please try again.',
            confirmButtonColor: '#3085d6'
        });
    });
}

// Add this new function to reset all values
function resetCalculatorValues() {
    const methodPrefixes = ['easyShip', 'fba', 'sellerFlex'];
    const feeTypes = ['ClosingFee', 'GstFee', 'ReferralFee'];
    
    // Reset values for each program
    methodPrefixes.forEach(prefix => {
        // Reset fee values
        feeTypes.forEach(fee => {
            const element = document.getElementById(`${prefix}${fee}`);
            if (element) element.textContent = '₹0.00';
        });
        
        // Reset shipping and profit values based on program type
        if (prefix === 'fba') {
            ['Regional', 'National'].forEach(zone => {
                const feeElement = document.getElementById(`${prefix}${zone}Fee`);
                const profitElement = document.getElementById(`${prefix}${zone}Profit`);
                
                if (feeElement) feeElement.textContent = '₹0.00';
                if (profitElement) {
                    profitElement.textContent = '₹0.00';
                    profitElement.classList.remove('text-red-600', 'text-emerald-600');
                }
            });
        } else {
            // Easy Ship and Seller Flex have only flat fee
            const feeElement = document.getElementById(`${prefix}FlatFee`);
            const profitElement = document.getElementById(`${prefix}FlatProfit`);
            
            if (feeElement) feeElement.textContent = '₹0.00';
            if (profitElement) {
                profitElement.textContent = '₹0.00';
                profitElement.classList.remove('text-red-600', 'text-emerald-600');
            }
        }
    });
}

// Initialize by hiding results section and adding cache-control meta tag
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('results').style.display = 'none';
});