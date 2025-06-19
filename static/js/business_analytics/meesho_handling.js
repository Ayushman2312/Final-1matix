/**
 * Meesho Sales Data Analysis - Dual File Upload Handler
 * 
 * This module handles the specialized dual file upload requirement for Meesho platform:
 * - Sales Data File
 * - Returns/Cancellations Data File
 */

// Main initialization function
document.addEventListener('DOMContentLoaded', function() {
    console.log('Meesho handling module loaded');
    
    // Initialize Meesho button if it exists
    const calculateMetricsBtn = document.getElementById('calculateMetricsBtn');
    if (calculateMetricsBtn) {
        calculateMetricsBtn.addEventListener('click', function() {
            // Get the currently selected platform type
            const platformType = document.getElementById('platformType')?.value || '';
            
            // Check if this is Meesho platform
            if (platformType.toLowerCase() === 'meesho') {
                // Show the Meesho-specific upload modal
                showMeeshoUploadModal();
            }
        });
    }
});

/**
 * Shows the Meesho-specific upload modal for dual file upload
 */
function showMeeshoUploadModal() {
    // Check if the Meesho modal already exists
    let meeshoModal = document.getElementById('meeshoUploadModal');
    
    // Create the Meesho modal if it doesn't exist
    if (!meeshoModal) {
        meeshoModal = document.createElement('div');
        meeshoModal.id = 'meeshoUploadModal';
        meeshoModal.className = 'fixed inset-0 z-50 flex items-center justify-center';
        meeshoModal.innerHTML = `
            <div class="absolute inset-0 bg-black bg-opacity-50" id="meeshoUploadModalOverlay"></div>
            <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 relative z-10 overflow-hidden max-h-[85vh] overflow-y-auto">
                <!-- Modal Header -->
                <div class="bg-[#7B3DF3] py-1.5 px-4 flex justify-between items-center">
                    <h3 class="text-white text-sm font-bold">Meesho Analysis - Upload Files</h3>
                    <button id="closeMeeshoModal" class="text-white hover:text-gray-200 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                
                <!-- Modal Content -->
                <div class="p-4">
                    <div class="mb-3">
                        <p class="text-xs text-gray-600 mb-2">Please upload two files – (1) Sales Data, and (2) Sales Return/Cancellation Data.</p>
                        <div class="bg-yellow-50 p-2 rounded-md text-xs text-yellow-700 mb-2">
                            <p class="font-medium">Important file requirements:</p>
                            <ul class="list-disc ml-4 mt-1 space-y-1">
                                <li>Both files should have identical column structures</li>
                                <li>The Returns file must include an additional <span class="font-medium">'cancel_return_date'</span> column</li>
                                <li>The system will merge both datasets for comprehensive analysis</li>
                            </ul>
                        </div>
                        <div class="bg-blue-50 p-2 rounded-md text-xs text-blue-700 mt-2">
                            <p class="font-medium">File Format Example:</p>
                            <p class="mt-1">Sales file: order_id, product, price, quantity, etc.</p>
                            <p>Returns file: order_id, product, price, quantity, <span class="underline">cancel_return_date</span>, etc.</p>
                        </div>
                    </div>
                    
                    <form id="meeshoUploadForm" enctype="multipart/form-data">
                        <!-- Add CSRF token -->
                        <input type="hidden" name="csrfmiddlewaretoken" value="${document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''}">
                        
                        <!-- Sales File Input -->
                        <div class="mb-3">
                            <label for="salesFileInput" class="block text-xs font-medium text-gray-700 mb-1">Sales Data File</label>
                            <div class="flex items-center space-x-2">
                                <input type="file" id="salesFileInput" name="sales_file" class="hidden" accept=".csv,.xlsx,.xls">
                                <label for="salesFileInput" class="cursor-pointer bg-white border border-gray-300 rounded-md py-1 px-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#7B3DF3] focus:border-[#7B3DF3] flex-grow flex items-center justify-between">
                                    <span id="selectedSalesFileName">Choose sales file...</span>
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                                    </svg>
                                </label>
                            </div>
                        </div>
                        
                        <!-- Returns File Input -->
                        <div class="mb-3">
                            <label for="returnsFileInput" class="block text-xs font-medium text-gray-700 mb-1">Returns/Cancellations Data File</label>
                            <div class="flex items-center space-x-2">
                                <input type="file" id="returnsFileInput" name="returns_file" class="hidden" accept=".csv,.xlsx,.xls">
                                <label for="returnsFileInput" class="cursor-pointer bg-white border border-gray-300 rounded-md py-1 px-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#7B3DF3] focus:border-[#7B3DF3] flex-grow flex items-center justify-between">
                                    <span id="selectedReturnsFileName">Choose returns file...</span>
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                                    </svg>
                                </label>
                            </div>
                        </div>
                        
                        <div id="meeshoUploadStatus" class="hidden mb-2"></div>
                        
                        <div class="flex items-center justify-between">
                            <button type="button" id="meeshoCalculateButton" class="bg-[#7B3DF3] py-1 px-3 text-white text-xs font-medium rounded-md hover:bg-[#6931D3] focus:outline-none focus:ring-2 focus:ring-[#7B3DF3] focus:ring-opacity-50 transition-colors flex items-center">
                                <span id="meeshoButtonText">Calculate Metrics</span>
                                <span id="meeshoSpinner" class="hidden ml-1 animate-spin">↻</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        // Add the modal to the document
        document.body.appendChild(meeshoModal);
        
        // Initialize event listeners
        initMeeshoModalListeners();
    } else {
        // Just show the modal if it already exists
        meeshoModal.classList.remove('hidden');
    }
}

/**
 * Initializes event listeners for the Meesho modal
 */
function initMeeshoModalListeners() {
    // Get elements from the modal
    const meeshoModal = document.getElementById('meeshoUploadModal');
    const closeMeeshoModal = document.getElementById('closeMeeshoModal');
    const meeshoModalOverlay = document.getElementById('meeshoUploadModalOverlay');
    const salesFileInput = document.getElementById('salesFileInput');
    const returnsFileInput = document.getElementById('returnsFileInput');
    const selectedSalesFileName = document.getElementById('selectedSalesFileName');
    const selectedReturnsFileName = document.getElementById('selectedReturnsFileName');
    const meeshoCalculateButton = document.getElementById('meeshoCalculateButton');
    
    // Add event listeners for closing the modal
    if (closeMeeshoModal) {
        closeMeeshoModal.addEventListener('click', () => {
            meeshoModal.classList.add('hidden');
        });
    }
    
    if (meeshoModalOverlay) {
        meeshoModalOverlay.addEventListener('click', () => {
            meeshoModal.classList.add('hidden');
        });
    }
    
    // Update file name displays when files are selected
    if (salesFileInput) {
        salesFileInput.addEventListener('change', function() {
            if (this.files.length) {
                if (selectedSalesFileName) {
                    selectedSalesFileName.textContent = this.files[0].name;
                }
                console.log(`Selected sales file: ${this.files[0].name}`);
            } else {
                if (selectedSalesFileName) {
                    selectedSalesFileName.textContent = 'Choose sales file...';
                }
                console.log('No sales file selected');
            }
        });
    } else {
        console.warn('⚠️ salesFileInput element not found');
    }
    
    if (returnsFileInput) {
        returnsFileInput.addEventListener('change', function() {
            if (this.files.length) {
                if (selectedReturnsFileName) {
                    selectedReturnsFileName.textContent = this.files[0].name;
                }
                console.log(`Selected returns file: ${this.files[0].name}`);
            } else {
                if (selectedReturnsFileName) {
                    selectedReturnsFileName.textContent = 'Choose returns file...';
                }
                console.log('No returns file selected');
            }
        });
    } else {
        console.warn('⚠️ returnsFileInput element not found');
    }
    
    // Handle calculate button click
    if (meeshoCalculateButton) {
        meeshoCalculateButton.addEventListener('click', submitMeeshoFiles);
    } else {
        console.warn('⚠️ meeshoCalculateButton element not found');
    }
    
    // Also check for alternative IDs that might be used in the dashboard
    const altSalesFileInput = document.getElementById('meeshoSalesFileInput');
    const altReturnsFileInput = document.getElementById('meeshoReturnsFileInput');
    const altMeeshoUploadButton = document.getElementById('meeshoUploadButton');
    
    if (altSalesFileInput) {
        console.log('Found alternative sales file input (meeshoSalesFileInput)');
        const altSalesFileName = document.getElementById('meeshoSalesFileName');
        
        altSalesFileInput.addEventListener('change', function() {
            if (this.files.length) {
                if (altSalesFileName) {
                    altSalesFileName.textContent = this.files[0].name;
                }
                console.log(`Selected sales file (alt): ${this.files[0].name}`);
            }
        });
    }
    
    if (altReturnsFileInput) {
        console.log('Found alternative returns file input (meeshoReturnsFileInput)');
        const altReturnsFileName = document.getElementById('meeshoReturnsFileName');
        
        altReturnsFileInput.addEventListener('change', function() {
            if (this.files.length) {
                if (altReturnsFileName) {
                    altReturnsFileName.textContent = this.files[0].name;
                }
                console.log(`Selected returns file (alt): ${this.files[0].name}`);
            }
        });
    }
    
    if (altMeeshoUploadButton) {
        console.log('Found alternative upload button (meeshoUploadButton)');
        altMeeshoUploadButton.addEventListener('click', function() {
            console.log('Alternative upload button clicked, calling submitMeeshoFiles');
            submitMeeshoFiles();
        });
    }
}

/**
 * Validates and submits the Meesho files for analysis
 */
function submitMeeshoFiles() {
    // Get required elements - try both direct and global access
    const salesFileInput = document.getElementById('salesFileInput') || window.salesFileInput;
    const returnsFileInput = document.getElementById('returnsFileInput') || window.returnsFileInput;
    
    // If we still don't have the file inputs, try other IDs that might be used
    const altSalesFileInput = document.getElementById('meeshoSalesFileInput');
    const altReturnsFileInput = document.getElementById('meeshoReturnsFileInput');
    
    // Use the first available file inputs
    const finalSalesInput = salesFileInput || altSalesFileInput;
    const finalReturnsInput = returnsFileInput || altReturnsFileInput;
    
    // Get UI elements
    const meeshoUploadStatus = document.getElementById('meeshoUploadStatus');
    const meeshoButtonText = document.getElementById('meeshoButtonText');
    const meeshoSpinner = document.getElementById('meeshoSpinner');
    const meeshoCalculateButton = document.getElementById('meeshoCalculateButton') || 
                                 document.getElementById('meeshoUploadButton');
    const meeshoModal = document.getElementById('meeshoUploadModal');
    
    console.log('🟢 Meesho file submission initiated');
    
    // Validate that we have file input elements
    if (!finalSalesInput || !finalReturnsInput) {
        console.error('❌ Could not find file input elements');
        showMeeshoUploadStatus('System error: Could not find file input elements', 'error');
        return;
    }
    
    // Validate that both files are selected
    if (!finalSalesInput.files.length && !finalReturnsInput.files.length) {
        console.error('❌ Both sales and returns files are missing');
        showMeeshoUploadStatus('Please upload both sales and returns files.', 'error');
        return;
    } else if (!finalSalesInput.files.length) {
        console.error('❌ Sales file is missing');
        showMeeshoUploadStatus('Please upload the Sales Data file.', 'error');
        return;
    } else if (!finalReturnsInput.files.length) {
        console.error('❌ Returns file is missing');
        showMeeshoUploadStatus('Please upload the Returns/Cancellations Data file.', 'error');
        return;
    }
    
    // Validate file types
    const salesFile = finalSalesInput.files[0];
    const returnsFile = finalReturnsInput.files[0];
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    
    const salesExt = salesFile.name.substring(salesFile.name.lastIndexOf('.')).toLowerCase();
    const returnsExt = returnsFile.name.substring(returnsFile.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(salesExt) || !validExtensions.includes(returnsExt)) {
        console.error(`❌ Invalid file format: Sales=${salesExt}, Returns=${returnsExt}`);
        showMeeshoUploadStatus('Please upload valid CSV or Excel files only.', 'error');
        return;
    }
    
    // Log file information
    console.log(`📤 Uploading Meesho files:
    - Sales file: ${salesFile.name} (${formatFileSize(salesFile.size)})
    - Returns file: ${returnsFile.name} (${formatFileSize(returnsFile.size)})`);
    
    // Show loading state
    if (meeshoButtonText) meeshoButtonText.textContent = 'Processing...';
    if (meeshoSpinner) meeshoSpinner.classList.remove('hidden');
    if (meeshoCalculateButton) meeshoCalculateButton.disabled = true;
    showMeeshoUploadStatus('Uploading files and calculating metrics...', 'info');
    
    // Create form data for API request
    const formData = new FormData();
    
    // Add files with correct names that match the backend expectations
    formData.append('sales_file', salesFile);
    formData.append('returns_file', returnsFile);
    formData.append('platform_type', 'meesho'); // Keep 'meesho' for request identification, backend will use None
    
    // Add CSRF token if available
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        console.log('📤 Adding CSRF token to request');
        formData.append('csrfmiddlewaretoken', csrfToken);
    } else {
        console.warn('⚠️ No CSRF token found');
    }
    
    console.log('📤 Sending API request to /business_analytics/api/metrics/');
    
    // Debug form data
    for (let pair of formData.entries()) {
        console.log(`📤 FormData: ${pair[0]}: ${pair[1] instanceof File ? pair[1].name : pair[1]}`);
    }
    
    // Make API request
    fetch('/business_analytics/api/metrics/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log(`📥 Received response: Status ${response.status}`);
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    // Try to parse as JSON
                    const err = JSON.parse(text);
                    console.error('❌ Error response:', err);
                    throw new Error(err.error || 'Failed to calculate metrics');
                } catch (jsonError) {
                    // If not JSON, return the text directly
                    console.error('❌ Error response (text):', text);
                    throw new Error(text || 'Failed to calculate metrics');
                }
            });
        }
        return response.json();
    })
    .then(metrics => {
        console.log('✅ Metrics calculation successful:', metrics);
        
        // Display the metrics
        if (typeof displaySalesMetrics === 'function') {
            displaySalesMetrics(metrics);
            
            // After displaying metrics, ensure charts are rendered
            setTimeout(() => {
                console.log('🔄 Triggering chart rendering for Meesho data...');
                
                // Extract the metrics object properly - could be in metrics.analysis or directly in metrics
                const metricsData = metrics.analysis || metrics;
                
                // Use the dedicated helper function if available
                if (typeof window.renderAllChartsForMeesho === 'function') {
                    console.log('📊 Using renderAllChartsForMeesho helper function');
                    window.renderAllChartsForMeesho(metricsData);
                } else {
                    // Fallback to manual chart rendering
                    console.log('⚠️ renderAllChartsForMeesho not available, using manual rendering');
                    
                    // Store metrics data globally for charts to access
                    window.lastAnalysisData = metricsData;
                    
                    // Show chart containers
                    const chartContainers = [
                        'returnsVsCancellationsContainer',
                        'topProductsContainer',
                        'topRegionsContainer',
                        'salesChannelContainer',
                        'salesTrendContainer'
                    ];
                    
                    // Make all chart containers visible
                    chartContainers.forEach(containerId => {
                        const container = document.getElementById(containerId);
                        if (container) {
                            console.log(`📊 Making ${containerId} visible`);
                            container.classList.remove('hidden');
                        }
                    });
                    
                    // Trigger returns vs cancellations chart
                    if (typeof createReturnsVsCancellationsChart === 'function' && 
                        document.getElementById('returnsVsCancellationsChart')) {
                        console.log('📊 Creating returns vs cancellations chart');
                        createReturnsVsCancellationsChart(window.lastAnalysisData);
                    }
                    
                    // Trigger top products chart/list
                    if (window.lastAnalysisData.top_products && 
                        window.lastAnalysisData.top_products.length > 0) {
                        if (typeof createTopProductsChart === 'function') {
                            console.log('📊 Creating top products visualization');
                            createTopProductsChart(window.lastAnalysisData, window.lastAnalysisData.top_products);
                        }
                    }
                    
                    // Trigger top regions chart/list
                    if (window.lastAnalysisData.top_regions && 
                        window.lastAnalysisData.top_regions.length > 0) {
                        if (typeof createTopSellingStatesChart === 'function') {
                            console.log('📊 Creating top regions visualization');
                            createTopSellingStatesChart(window.lastAnalysisData, window.lastAnalysisData.top_regions);
                        }
                    }
                    
                    // Trigger sales channels chart if available
                    if (window.lastAnalysisData.sales_channels && 
                        window.lastAnalysisData.sales_channels.length > 0) {
                        if (typeof updateSalesChannelChart === 'function') {
                            console.log('📊 Creating sales channels chart');
                            updateSalesChannelChart(window.lastAnalysisData.sales_channels);
                        }
                    }
                    
                    // Trigger time series chart if available
                    if (window.lastAnalysisData.time_series && 
                        window.lastAnalysisData.time_series.labels &&
                        window.lastAnalysisData.time_series.labels.length > 0) {
                        if (typeof updateSalesTrendChart === 'function') {
                            console.log('📊 Creating sales trend chart');
                            updateSalesTrendChart(window.lastAnalysisData.time_series);
                        }
                    }
                    
                    // Force chart redraw by triggering window resize event
                    setTimeout(() => {
                        console.log('📊 Triggering window resize to redraw charts');
                        window.dispatchEvent(new Event('resize'));
                    }, 100);
                }
                
                console.log('✅ Chart rendering complete');
            }, 500); // Small delay to ensure DOM is ready
        } else {
            console.warn('⚠️ displaySalesMetrics function not found');
        }
        
        // Show success message
        showMeeshoUploadStatus('Analysis completed successfully!', 'success');
        
        // Hide loading state
        if (meeshoButtonText) meeshoButtonText.textContent = 'Calculate Metrics';
        if (meeshoSpinner) meeshoSpinner.classList.add('hidden');
        if (meeshoCalculateButton) meeshoCalculateButton.disabled = false;
        
        // Close the modal after a small delay
        if (meeshoModal) {
            setTimeout(() => {
                meeshoModal.classList.add('hidden');
            }, 1500);
        }
    })
    .catch(error => {
        console.error('❌ Error:', error);
        
        // Show error message
        showMeeshoUploadStatus(`Error: ${error.message}`, 'error');
        
        // Reset button state
        if (meeshoButtonText) meeshoButtonText.textContent = 'Calculate Metrics';
        if (meeshoSpinner) meeshoSpinner.classList.add('hidden');
        if (meeshoCalculateButton) meeshoCalculateButton.disabled = false;
    });
}

/**
 * Formats file size to a human-readable string
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
}

/**
 * Displays upload status messages
 * @param {string} message - Status message to display
 * @param {string} type - Message type (success, error, info)
 */
function showMeeshoUploadStatus(message, type) {
    const statusDiv = document.getElementById('meeshoUploadStatus');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = 'mb-2 py-1 px-2 rounded text-xs';
    statusDiv.classList.remove('hidden');
    
    if (type === 'error') statusDiv.classList.add('bg-red-100', 'text-red-700');
    else if (type === 'success') statusDiv.classList.add('bg-green-100', 'text-green-700');
    else statusDiv.classList.add('bg-blue-100', 'text-blue-700');
}

/**
 * Updates debug information on the UI
 * @param {string} status - Status message
 * @param {Object} data - Debug data to display
 */
function updateDebugInfo(status, data) {
    const debugStatus = document.getElementById('meeshoDebugStatus');
    const debugData = document.getElementById('meeshoDebugData');
    
    if (debugStatus) debugStatus.textContent = status;
    if (debugData) debugData.textContent = JSON.stringify(data, null, 2);
}

// Establish compatibility with the dashboard's functions
document.addEventListener('DOMContentLoaded', function() {
    // Connect with dashboard's Meesho handling functions if they exist
    if (typeof window.handleMeeshoUpload === 'function') {
        console.log('🔗 Connected with dashboard Meesho handler');
        
        // Override the original function to call the dashboard's handler
        window.originalSubmitMeeshoFiles = submitMeeshoFiles;
        
        // Create a new version that can integrate with the dashboard handler
        window.submitMeeshoFiles = function() {
            // Get required elements
            const salesFileInput = document.getElementById('salesFileInput');
            const returnsFileInput = document.getElementById('returnsFileInput');
            const meeshoUploadStatus = document.getElementById('meeshoUploadStatus');
            const meeshoButtonText = document.getElementById('meeshoButtonText');
            const meeshoSpinner = document.getElementById('meeshoSpinner');
            const meeshoCalculateButton = document.getElementById('meeshoCalculateButton');
            const meeshoModal = document.getElementById('meeshoUploadModal');
            
            console.log('🟢 Meesho file submission initiated');
            
            // Basic validation
            if (!salesFileInput || !returnsFileInput) {
                console.error('❌ File input elements not found');
                if (meeshoUploadStatus) {
                    showMeeshoUploadStatus('System error: File input elements not found', 'error');
                } else {
                    alert('System error: File input elements not found');
                }
                return;
            }
            
            // Validate that both files are selected
            if (!salesFileInput.files.length && !returnsFileInput.files.length) {
                console.error('❌ Both sales and returns files are missing');
                showMeeshoUploadStatus('Please upload both sales and returns files.', 'error');
                return;
            } else if (!salesFileInput.files.length) {
                console.error('❌ Sales file is missing');
                showMeeshoUploadStatus('Please upload the Sales Data file.', 'error');
                return;
            } else if (!returnsFileInput.files.length) {
                console.error('❌ Returns file is missing');
                showMeeshoUploadStatus('Please upload the Returns/Cancellations Data file.', 'error');
                return;
            }
            
            // Show loading state
            if (meeshoButtonText) meeshoButtonText.textContent = 'Processing...';
            if (meeshoSpinner) meeshoSpinner.classList.remove('hidden');
            if (meeshoCalculateButton) meeshoCalculateButton.disabled = true;
            showMeeshoUploadStatus('Uploading files and calculating metrics...', 'info');
            
            // Create form data for API request
            const formData = new FormData();
            formData.append('sales_file', salesFileInput.files[0]);
            formData.append('returns_file', returnsFileInput.files[0]);
            formData.append('platform_type', 'meesho');
            
            // Use the dashboard's handler if available
            try {
                window.handleMeeshoUpload(formData);
                console.log('✅ Using dashboard Meesho handler');
                
                // Show success message
                showMeeshoUploadStatus('Files submitted for analysis...', 'success');
                
                // Hide loading state after a short delay
                setTimeout(() => {
                    if (meeshoButtonText) meeshoButtonText.textContent = 'Calculate Metrics';
                    if (meeshoSpinner) meeshoSpinner.classList.add('hidden');
                    if (meeshoCalculateButton) meeshoCalculateButton.disabled = false;
                    
                    // Close the modal after processing
                    if (meeshoModal) meeshoModal.classList.add('hidden');
                }, 1500);
                
            } catch (error) {
                console.error('❌ Error using dashboard handler:', error);
                
                // Fall back to original function
                console.log('⚠️ Falling back to original implementation');
                window.originalSubmitMeeshoFiles();
            }
        };
    } else {
        console.log('ℹ️ Dashboard Meesho handler not found, using standalone implementation');
    }
});

// Export functions for use in other modules
window.meeshoHandler = {
    showMeeshoUploadModal,
    submitMeeshoFiles,
    showMeeshoUploadStatus
}; 