let selectedProduct = null;
                let pdfBlobUrl = null;
                
                // Add this at the start of your script
                window.onerror = function(msg, url, lineNo, columnNo, error) {
                    console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo + '\nColumn: ' + columnNo + '\nError object: ' + JSON.stringify(error));
                    return false;
                };
                
                function searchProducts(query) {
                    const suggestionsDiv = document.getElementById('product-suggestions');
                    
                    if (query.length < 2) {
                        suggestionsDiv.classList.add('hidden');
                        suggestionsDiv.innerHTML = '';
                        return;
                    }

                    // Make an AJAX call to the backend to get product suggestions
                    fetch(`/product_card/api/products/`)
                        .then(response => response.json())
                        .then(data => {
                            suggestionsDiv.innerHTML = '';
                            
                            if (data.length === 0) {
                                const div = document.createElement('div');
                                div.className = 'p-2 text-gray-500';
                                div.textContent = 'No products found';
                                suggestionsDiv.appendChild(div);
                            } else {
                                data.forEach(product => {
                                    const div = document.createElement('div');
                                    div.className = 'p-2 hover:bg-gray-100 cursor-pointer';
                                    div.textContent = product.product_title;
                                    div.dataset.productId = product.product_id;
                                    div.onclick = () => selectProduct(product.product_id);
                                    suggestionsDiv.appendChild(div);
                                });
                            }
                            
                            suggestionsDiv.classList.remove('hidden');
                        })
                        .catch(error => {
                            console.error('Error searching products:', error);
                        });
                }

                function selectProduct(productId) {
                    selectedProduct = productId;
                    // Make AJAX call to get product details
                    fetch(`/product_card/api/products/${productId}/`)
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('product-search').value = data.product_title;
                            document.getElementById('hsn').value = data.product_hsc_code || '';
                            document.getElementById('rate').value = data.product_price;
                            selectedProduct = data; // Store the entire product data
                            document.getElementById('gst').value = data.product_gst_percentage || 0;
                        });
                }

                function updateTotal() {
                    const quantity = parseFloat(document.getElementById('quantity').value) || 0;
                    const rate = parseFloat(document.getElementById('rate').value) || 0;
                    const total = (quantity * rate).toFixed(2);
                    return total;
                }

                function addProduct() {
                    if (!selectedProduct) {
                        alert('Please select a product first');
                        return;
                    }
                    
                    const product = document.getElementById('product-search').value;
                    const hsn = document.getElementById('hsn').value;
                    const rate = parseFloat(document.getElementById('rate').value) || 0;
                    const quantity = parseFloat(document.getElementById('quantity').value) || 0;
                    const unit = document.getElementById('unit').value;
                    const gstPercentage = parseFloat(selectedProduct.product_gst_percentage) || 0;
                    const total = updateTotal();

                    if (!product || !rate || !quantity) {
                        alert('Please fill in all required fields');
                        return;
                    }

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="p-2" data-field="name">${product}</td>
                        <td class="p-2" data-field="hsn">${hsn}</td>
                        <td class="p-2" data-field="rate">${rate.toFixed(2)}</td>
                        <td class="p-2" data-field="quantity">${quantity}</td>
                        <td class="p-2" data-field="unit">${unit}</td>
                        <td class="p-2" data-field="total">${total}</td>
                        <td class="p-2" data-field="gst_percentage">${gstPercentage}%</td>
                        <td class="p-2">
                            <button onclick="this.closest('tr').remove()" class="text-red-500">Remove</button>
                        </td>
                    `;

                    document.getElementById('products-table').appendChild(tr);

                    // Reset form
                    document.getElementById('product-search').value = '';
                    document.getElementById('hsn').value = '';
                    document.getElementById('rate').value = '';
                    document.getElementById('quantity').value = '';
                    document.getElementById('unit').value = '';
                    selectedProduct = null;
                }

                // Update the getCookie function to be more robust
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

                // Add this function to get CSRF token from the hidden input
                function getCSRFToken() {
                    // First try to get from hidden input
                    const tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
                    if (tokenInput) {
                        return tokenInput.value;
                    }
                    // Fallback to cookie
                    return getCookie('csrftoken');
                }

                function generateAndDownloadPDF() {
                    try {
                        // Get form data
                    const companyId = document.getElementById('company').value;
                    const billType = document.getElementById('billType').value;
                    
                    // Get billing details
                    const billingDetails = {
                        name: document.querySelector('input[placeholder="Bill To Name"]').value,
                            gstin: document.querySelector('input[placeholder="Enter GSTIN"]').value,
                        mobile: document.querySelector('input[placeholder="Mobile"]').value,
                        email: document.querySelector('input[type="email"]').value,
                            address: document.querySelector('textarea[placeholder="Address"]').value || 
                                    document.querySelector('input[placeholder="Address"]').value,
                            state: document.querySelector('select[name="state"]').value,
                            pincode: document.querySelector('input[placeholder="Pincode"]').value
                        };

                        // Debug log to check values
                        console.log('Collected Billing Details:', billingDetails);

                        // Validate billing details
                        const missingFields = [];
                        Object.entries(billingDetails).forEach(([key, value]) => {
                            if (!value || value.trim() === '') {
                                missingFields.push(key);
                            }
                        });

                        if (missingFields.length > 0) {
                            alert(`Please fill in all required billing details: ${missingFields.join(', ')}`);
                        return;
                    }

                        // Get products from the table with GST percentage
                    const products = [];
                    const rows = document.querySelectorAll('#products-table tr');
                    
                        rows.forEach(row => {
                            const cells = row.cells;
                            if (cells && cells.length >= 8) {
                                const product = {
                                    name: cells[0].textContent.trim(),
                                    hsn: cells[1].textContent.trim(),
                                    rate: parseFloat(cells[2].textContent.replace(/[^\d.-]/g, '')) || 0,
                                    quantity: parseInt(cells[3].textContent.trim()) || 0,
                                    unit_type: cells[4].textContent.trim(),
                                    total: parseFloat(cells[5].textContent.replace(/[^\d.-]/g, '')) || 0,
                                    gst_percentage: parseFloat(cells[6].textContent.replace('%', '')) || 0
                                };

                                if (product.name && product.rate && product.quantity) {
                                    products.push(product);
                                }
                            }
                        });

                        if (products.length === 0) {
                        alert('Please add at least one product');
                        return;
                    }

                        // Get shipping details
                        const useShippingAddress = document.getElementById('sameAsBilling')?.checked || false;
                        const shippingDetails = {
                            use_billing_address: useShippingAddress,
                            address: useShippingAddress ? billingDetails.address : 
                                    (document.getElementById('shippingAddress')?.value || billingDetails.address),
                            pincode: document.getElementById('shippingPincode')?.value || ''
                        };

                        // Prepare request data
                        const requestData = {
                            company_id: companyId,
                            bill_type: billType,
                            billing_details: billingDetails,
                            shipping_details: shippingDetails,
                            products: products
                        };

                        console.log('Request Data:', requestData);

                        // Get CSRF token
                    const csrftoken = getCSRFToken();
                    
                    // Show loading state
                        const generateButton = document.querySelector('button[onclick*="generateAndDownloadPDF"]');
                        if (generateButton) {
                    generateButton.textContent = 'Generating...';
                    generateButton.disabled = true;
                        }

                    // Make the API call
                    fetch('/invoicing/create-invoice/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrftoken,
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-Generate-PDF': 'true'
                        },
                            body: JSON.stringify(requestData)
                    })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(data => {
                                throw new Error(data.error || 'Failed to generate PDF');
                            });
                        }
                        return response.blob();
                    })
                    .then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `invoice_${new Date().getTime()}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert(error.message || 'Failed to generate PDF. Please try again.');
                    })
                    .finally(() => {
                            if (generateButton) {
                                generateButton.textContent = 'Generate and Download PDF';
                        generateButton.disabled = false;
                            }
                        });

                    } catch (error) {
                        console.error('Error in generateAndDownloadPDF:', error);
                        alert('An error occurred while generating the PDF. Please check the console for details.');
                    }
                }

                // Add this helper function to debug form values
                function debugFormValues() {
                    const billingFields = {
                        'Bill To Name': document.querySelector('input[placeholder="Bill To Name"]')?.value,
                        'GSTIN': document.querySelector('input[placeholder="Enter GSTIN"]')?.value,
                        'Mobile': document.querySelector('input[placeholder="Mobile"]')?.value,
                        'Email': document.querySelector('input[type="email"]')?.value,
                        'Address': document.querySelector('textarea[placeholder="Address"]')?.value || 
                                  document.querySelector('input[placeholder="Address"]')?.value,
                        'State': document.querySelector('select[name="state"]')?.value
                    };
                    console.log('Form Field Values:', billingFields);
                }

                // Call this function when the generate PDF button is clicked
                document.querySelector('button[onclick*="generateAndDownloadPDF"]')?.addEventListener('click', debugFormValues);

                function showInvoiceForm() {
                    const companySelect = document.getElementById('company');
                    const billType = document.getElementById('billType');

                    if (!companySelect.value) {
                        alert('Please select a company first');
                        return;
                    }

                    if (!billType.value) {
                        alert('Please select a billing type first');
                        return;
                    }

                    document.getElementById('invoiceForm').classList.remove('hidden');

                // Close suggestions when clicking outside
                document.addEventListener('click', function(e) {
                    if (!e.target.closest('#product-search')) {
                        document.getElementById('product-suggestions').classList.add('hidden');
                    }
                });

                // Initialize Chosen plugin
                $(document).ready(function() {
                    $.js = function (el) {
                        return $('[data-js=' + el + ']')
                    };

                    function initializeChosen() {
                        $(".chosen-select").chosen({
                            disable_search_threshold: 10,
                            inherit_select_classes: true,
                            width: '100%'
                        }).on('chosen:showing_dropdown', function (evt, params) {
                            $(this).parent().addClass('is-active');
                            $.js('custom-scroll').find(".chosen-results").niceScroll({
                                cursorcolor: "rgba(0,0,0,0.2)",
                                cursorwidth: "4px",
                                background: "#f3f4f6",
                                cursorborder: "none",
                                cursorborderradius: "2px",
                                cursoropacitymin: 1,
                            });
                        }).on('chosen:hiding_dropdown', function (evt, params) {
                            $(this).parent().removeClass('is-active');
                        });
                    }

                    // Initialize on page load
                    initializeChosen();

                    // Update the state value in the form data when generating PDF
                    function updateStateValue() {
                        const stateSelect = document.querySelector('select[name="state"]');
                        const chosenSelect = $('.chosen-select');
                        if (stateSelect && chosenSelect.length) {
                            stateSelect.value = chosenSelect.val();
                        }
                    }

                    // Add to your existing form submission logic
                    document.getElementById('generatePDFBtn').addEventListener('click', function() {
                        updateStateValue();
                        // ... rest of your PDF generation code
                    });
                });

                // Add event listener for shipping address toggle
                document.getElementById('sameAsBilling').addEventListener('change', function() {
                    const shippingSection = document.getElementById('shippingAddressSection');
                    if (this.checked) {
                        shippingSection.classList.add('hidden');
                    } else {
                        shippingSection.classList.remove('hidden');
                    }
                });
                }