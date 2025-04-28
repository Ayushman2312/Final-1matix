
// Add this at the start of the file
        // Force reload on page load to clear cache
        window.onload = function() {
            if (!window.location.hash) {
                window.location = window.location + '#loaded';
                window.location.reload(true);
            }
        }

        function calculateFees(event) {
            event.preventDefault();
            
            // Reset all values to 0 before new calculation
            resetCalculatorValues();
            
            const formData = new FormData(document.getElementById('calculatorForm'));

            fetch('/fee_calculator/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                cache: 'no-store' // Prevent caching of the request
            })
            .then(response => response.json())
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
                            ['local', 'regional', 'national'].forEach(zone => {
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

                            // Update average values
                            if (programData.locations.average) {
                                const avgData = programData.locations.average;
                                
                                const avgFeeElement = document.getElementById(`${frontendPrefix}AverageFee`);
                                if (avgFeeElement) {
                                    const avgFee = Number(avgData.shipping_fee || 0);
                                    avgFeeElement.textContent = `₹${avgFee.toFixed(2)}`;
                                }

                                const avgProfitElement = document.getElementById(`${frontendPrefix}AverageProfit`);
                                if (avgProfitElement) {
                                    const avgProfit = Number(avgData.net_amount || 0);
                                    avgProfitElement.textContent = `₹${avgProfit.toFixed(2)}`;
                                    avgProfitElement.classList.remove('text-red-600', 'text-emerald-600');
                                    avgProfitElement.classList.add(avgProfit < 0 ? 'text-red-600' : 'text-emerald-600');
                                }
                            }
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
            const zones = ['Local', 'Regional', 'National', 'Average'];
            const fees = ['ClosingFee', 'GstFee', 'ReferralFee'];

            methodPrefixes.forEach(prefix => {
                // Reset zone values
                zones.forEach(zone => {
                    const feeElement = document.getElementById(`${prefix}${zone}Fee`);
                    const profitElement = document.getElementById(`${prefix}${zone}Profit`);
                    
                    if (feeElement) feeElement.textContent = '₹0.00';
                    if (profitElement) {
                        profitElement.textContent = '₹0.00';
                        profitElement.classList.remove('text-red-600', 'text-emerald-600');
                    }
                });

                // Reset fee values
                fees.forEach(fee => {
                    const element = document.getElementById(`${prefix}${fee}`);
                    if (element) element.textContent = '₹0.00';
                });
            });
        }

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

        // Initialize by hiding results section and adding cache-control meta tag
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('results').style.display = 'none';
        });