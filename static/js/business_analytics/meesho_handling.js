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
            <div class="absolute inset-0 bg-black bg-opacity-50" id="meeshoModalOverlay"></div>
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
                        <!-- Sales File Input -->
                        <div class="mb-3">
                            <label for="salesFileInput" class="block text-xs font-medium text-gray-700 mb-1">Sales Data File</label>
                            <div class="flex items-center space-x-2">
                                <input type="file" id="salesFileInput" name="salesFile" class="hidden" accept=".csv,.xlsx,.xls">
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
                                <input type="file" id="returnsFileInput" name="returnsFile" class="hidden" accept=".csv,.xlsx,.xls">
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
                            <button type="button" id="meeshoCalculateButton" class="bg-[#7B3DF3] py-1 px-3 text-white text-xs font-medium rounded-md hover:bg-[#6931D3] focus:outline-none focus:ring-2 focus:ring-[#7B3DF3] focus:ring-opacity-50 transition-colors">
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
    const meeshoModalOverlay = document.getElementById('meeshoModalOverlay');
    const salesFileInput = document.getElementById('salesFileInput');
    const returnsFileInput = document.getElementById('returnsFileInput');
    const selectedSalesFileName = document.getElementById('selectedSalesFileName');
    const selectedReturnsFileName = document.getElementById('selectedReturnsFileName');
    const meeshoCalculateButton = document.getElementById('meeshoCalculateButton');
    
    // Add event listeners for closing the modal
    closeMeeshoModal.addEventListener('click', () => {
        meeshoModal.classList.add('hidden');
    });
    
    meeshoModalOverlay.addEventListener('click', () => {
        meeshoModal.classList.add('hidden');
    });
    
    // Update file name displays when files are selected
    salesFileInput.addEventListener('change', function() {
        if (this.files.length) {
            selectedSalesFileName.textContent = this.files[0].name;
        } else {
            selectedSalesFileName.textContent = 'Choose sales file...';
        }
    });
    
    returnsFileInput.addEventListener('change', function() {
        if (this.files.length) {
            selectedReturnsFileName.textContent = this.files[0].name;
        } else {
            selectedReturnsFileName.textContent = 'Choose returns file...';
        }
    });
    
    // Handle calculate button click
    meeshoCalculateButton.addEventListener('click', submitMeeshoFiles);
}

/**
 * Validates and submits the Meesho files for analysis
 */
function submitMeeshoFiles() {
    // Get required elements
    const salesFileInput = document.getElementById('salesFileInput');
    const returnsFileInput = document.getElementById('returnsFileInput');
    const meeshoUploadStatus = document.getElementById('meeshoUploadStatus');
    const meeshoButtonText = document.getElementById('meeshoButtonText');
    const meeshoSpinner = document.getElementById('meeshoSpinner');
    const meeshoCalculateButton = document.getElementById('meeshoCalculateButton');
    const meeshoModal = document.getElementById('meeshoUploadModal');
    
    console.log('🟢 Meesho file submission initiated');
    
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
    
    // Validate file types
    const salesFile = salesFileInput.files[0];
    const returnsFile = returnsFileInput.files[0];
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
    meeshoButtonText.textContent = 'Processing...';
    meeshoSpinner.classList.remove('hidden');
    meeshoCalculateButton.disabled = true;
    showMeeshoUploadStatus('Uploading files and calculating metrics...', 'info');
    
    // Create form data for API request
    const formData = new FormData();
    formData.append('sales_file', salesFile);
    formData.append('returns_file', returnsFile);
    formData.append('platform_type', 'meesho');
    
    console.log('📤 Sending API request to /business_analytics/api/metrics/');
    
    // Make API request
    fetch('/business_analytics/api/metrics/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        console.log(`📥 Received response: Status ${response.status}`);
        if (!response.ok) {
            return response.json().then(err => {
                console.error('❌ Error response:', err);
                throw new Error(err.error || 'Failed to calculate metrics');
            });
        }
        return response.json();
    })
    .then(metrics => {
        console.log('✅ Metrics calculation successful:', metrics);
        
        // Display the metrics
        displaySalesMetrics(metrics);
        
        // Show success message
        showMeeshoUploadStatus('Analysis completed successfully!', 'success');
        
        // Hide loading state
        meeshoButtonText.textContent = 'Calculate Metrics';
        meeshoSpinner.classList.add('hidden');
        meeshoCalculateButton.disabled = false;
        
        // Close the modal after a small delay
        setTimeout(() => {
            meeshoModal.classList.add('hidden');
        }, 1500);
    })
    .catch(error => {
        console.error('❌ Error:', error);
        
        // Show error message
        showMeeshoUploadStatus(`Error: ${error.message}`, 'error');
        
        // Reset button state
        meeshoButtonText.textContent = 'Calculate Metrics';
        meeshoSpinner.classList.add('hidden');
        meeshoCalculateButton.disabled = false;
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