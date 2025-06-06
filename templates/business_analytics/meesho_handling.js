// Meesho-specific elements and handlers
document.addEventListener('DOMContentLoaded', function() {
    // Meesho-specific elements
    const standardFileUpload = document.getElementById('standardFileUpload');
    const meeshoFileUpload = document.getElementById('meeshoFileUpload');
    const salesFileInput = document.getElementById('salesFileInput');
    const returnsFileInput = document.getElementById('returnsFileInput');
    const selectedSalesFileName = document.getElementById('selectedSalesFileName');
    const selectedReturnsFileName = document.getElementById('selectedReturnsFileName');
    const platformType = document.getElementById('platformType');
    const uploadButton = document.getElementById('uploadButton');
    const uploadButtonText = document.getElementById('uploadButtonText');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadForm = document.getElementById('uploadForm');
    
    // Add Meesho file upload section to the form if it doesn't exist yet
    if (!document.getElementById('meeshoFileUpload')) {
        // Find the standard file upload section
        const standardUpload = document.getElementById('standardFileUpload');
        if (standardUpload) {
            // Create the Meesho file upload section
            const meeshoUploadHtml = `
                <div id="meeshoFileUpload" class="hidden mb-2">
                    <div class="bg-purple-50 p-2 rounded-md mb-2 border border-purple-100">
                        <p class="text-xs text-purple-700 font-medium mb-1">Meesho Data Upload</p>
                        <p class="text-xs text-purple-600">Please upload both sales data and returns data files. Both will be merged for comprehensive analysis.</p>
                    </div>
                    
                    <!-- Sales data file upload -->
                    <div class="mb-2">
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
                    
                    <!-- Returns data file upload -->
                    <div>
                        <label for="returnsFileInput" class="block text-xs font-medium text-gray-700 mb-1">Returns Data File <span class="text-gray-500 font-normal">(with cancel_return_date column)</span></label>
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
                </div>
            `;
            
            // Insert the Meesho upload section after the standard upload section
            standardUpload.insertAdjacentHTML('afterend', meeshoUploadHtml);
        }
    }
    
    // Toggle Meesho-specific UI when platform type changes
    if (platformType) {
        platformType.addEventListener('change', function() {
            const meeshoFileUpload = document.getElementById('meeshoFileUpload');
            const standardFileUpload = document.getElementById('standardFileUpload');
            
            if (this.value === 'meesho') {
                if (standardFileUpload) standardFileUpload.classList.add('hidden');
                if (meeshoFileUpload) meeshoFileUpload.classList.remove('hidden');
                
                // Update the upload button text
                if (uploadButtonText) uploadButtonText.textContent = 'Upload Both Files & Analyze';
                
                // Show Meesho-specific info
                showUploadStatus('Meesho platform selected. Please upload both sales data and returns data files for comprehensive analysis.', 'info');
            } else {
                if (standardFileUpload) standardFileUpload.classList.remove('hidden');
                if (meeshoFileUpload) meeshoFileUpload.classList.add('hidden');
                
                // Reset the upload button text
                if (uploadButtonText) uploadButtonText.textContent = 'Upload & Analyze';
                
                // Clear any Meesho-specific info
                if (uploadStatus && uploadStatus.innerText && uploadStatus.innerText.includes('Meesho platform selected')) {
                    uploadStatus.classList.add('hidden');
                }
            }
        });
    }
    
    // Attach event handlers for Meesho file inputs
    function setupMeeshoInputHandlers() {
        const salesFileInput = document.getElementById('salesFileInput');
        const returnsFileInput = document.getElementById('returnsFileInput');
        
        if (salesFileInput) {
            salesFileInput.addEventListener('change', function() {
                const selectedSalesFileName = document.getElementById('selectedSalesFileName');
                if (salesFileInput.files.length > 0 && selectedSalesFileName) {
                    selectedSalesFileName.textContent = salesFileInput.files[0].name;
                    
                    // Check if both files are selected
                    checkMeeshoFilesStatus();
                    
                    // Extract headers if it's a CSV file
                    if (salesFileInput.files[0].name.toLowerCase().endsWith('.csv') && typeof extractFileHeaders === 'function') {
                        extractFileHeaders(salesFileInput.files[0], 'sales');
                    }
                } else if (selectedSalesFileName) {
                    selectedSalesFileName.textContent = 'Choose sales file...';
                }
            });
        }
        
        if (returnsFileInput) {
            returnsFileInput.addEventListener('change', function() {
                const selectedReturnsFileName = document.getElementById('selectedReturnsFileName');
                if (returnsFileInput.files.length > 0 && selectedReturnsFileName) {
                    selectedReturnsFileName.textContent = returnsFileInput.files[0].name;
                    
                    // Check if both files are selected
                    checkMeeshoFilesStatus();
                    
                    // Extract headers if it's a CSV file
                    if (returnsFileInput.files[0].name.toLowerCase().endsWith('.csv') && typeof extractFileHeaders === 'function') {
                        extractFileHeaders(returnsFileInput.files[0], 'returns');
                    }
                } else if (selectedReturnsFileName) {
                    selectedReturnsFileName.textContent = 'Choose returns file...';
                }
            });
        }
    }
    
    // Function to check if both Meesho files are selected
    function checkMeeshoFilesStatus() {
        const salesFileInput = document.getElementById('salesFileInput');
        const returnsFileInput = document.getElementById('returnsFileInput');
        const uploadButton = document.getElementById('uploadButton');
        
        if (!salesFileInput || !returnsFileInput) return;
        
        if (salesFileInput.files.length > 0 && returnsFileInput.files.length > 0) {
            showUploadStatus('Both sales and returns files selected. Ready to analyze!', 'success');
            
            // Enable the upload button if it was disabled
            if (uploadButton && uploadButton.disabled) {
                uploadButton.disabled = false;
            }
        } else if (salesFileInput.files.length > 0) {
            showUploadStatus('Sales file selected. Please also select a returns file.', 'info');
        } else if (returnsFileInput.files.length > 0) {
            showUploadStatus('Returns file selected. Please also select a sales file.', 'info');
        }
    }
    
    // Check for cancel_return_date column in returns file (helper function)
    function checkReturnDateColumn(headers) {
        return headers.some(h => 
            h.toLowerCase().includes('cancel_return_date') || 
            h.toLowerCase().includes('return_date') || 
            h.toLowerCase().includes('cancellation_date'));
    }
    
    // Modify the original upload form submit handler
    const originalUploadButtonClick = uploadButton ? uploadButton.onclick : null;
    
    if (uploadButton) {
        uploadButton.addEventListener('click', function(e) {
            const platformType = document.getElementById('platformType');
            const isMeesho = platformType && platformType.value === 'meesho';
            
            if (!isMeesho) {
                // For non-Meesho platforms, use the original handler
                if (originalUploadButtonClick) {
                    return; // Let the original handler run
                }
            } else {
                // For Meesho, handle it specially
                e.preventDefault();
                
                const salesFileInput = document.getElementById('salesFileInput');
                const returnsFileInput = document.getElementById('returnsFileInput');
                const uploadButtonText = document.getElementById('uploadButtonText');
                const uploadSpinner = document.getElementById('uploadSpinner');
                
                // Check if both files are selected
                if (!salesFileInput.files.length || !returnsFileInput.files.length) {
                    showUploadStatus('Please select both sales and returns files for Meesho analysis.', 'error');
                    return;
                }
                
                // Show loading state
                if (uploadButtonText) uploadButtonText.textContent = 'Merging & Analyzing...';
                if (uploadSpinner) uploadSpinner.classList.remove('hidden');
                uploadButton.disabled = true;
                
                // Prepare form data
                const formData = new FormData(uploadForm);
                
                // Add manual column mappings if provided
                if (typeof getManualColumnMappings === 'function') {
                    const manualMappings = getManualColumnMappings();
                    if (Object.keys(manualMappings).length > 0) {
                        formData.append('manual_column_mapping', JSON.stringify(manualMappings));
                    }
                }
                
                // Add flag for Meesho merge operation
                formData.append('merge_meesho_files', 'true');
                
                // Send the request to the correct endpoint
                fetch('/business_analytics/api/upload/', {
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Update debug info
                    const requestStatus = document.getElementById('requestStatus');
                    const rawResponseDebug = document.getElementById('rawResponseDebug');
                    
                    if (requestStatus) {
                        requestStatus.textContent = 'Success: Files merged and analyzed';
                    }
                    if (rawResponseDebug) {
                        rawResponseDebug.textContent = JSON.stringify(data, null, 2);
                    }
                    
                    // Reset upload button state
                    if (uploadButtonText) uploadButtonText.textContent = 'Upload Both Files & Analyze';
                    if (uploadSpinner) uploadSpinner.classList.add('hidden');
                    uploadButton.disabled = false;
                    
                    if (data.success) {
                        // Show success message
                        showUploadStatus('Files merged and analysis completed successfully!', 'success');
                        
                        // Check for column mapping issues
                        if (data.column_mapping_issues && data.column_mapping_issues.length > 0 && typeof displayColumnMappingIssues === 'function') {
                            displayColumnMappingIssues(data.column_mapping_issues);
                        }
                        
                        // Update column mapping form with available columns
                        if (data.available_columns && data.available_columns.length > 0 && typeof populateColumnMappingDropdowns === 'function') {
                            populateColumnMappingDropdowns(data.available_columns);
                            
                            // Set current mappings if available
                            if (data.column_mapping && typeof setCurrentColumnMappings === 'function') {
                                setCurrentColumnMappings(data.column_mapping);
                            }
                        }
                        
                        // Display the results
                        if (typeof displayAnalysisResults === 'function') {
                            displayAnalysisResults(data);
                        }
                        
                        // Close the upload modal after a short delay
                        setTimeout(() => {
                            const uploadModal = document.getElementById('uploadModal');
                            const analysisModal = document.getElementById('analysisModal');
                            
                            if (uploadModal) uploadModal.classList.add('hidden');
                            
                            // Show analysis modal if there are results
                            if (data.analysis && analysisModal) {
                                analysisModal.classList.remove('hidden');
                            }
                            
                            // Update the dashboard with the new analysis
                            if (typeof updateDashboard === 'function') {
                                updateDashboard(data.analysis);
                            }
                        }, 1000);
                    } else {
                        // Show error message
                        showUploadStatus(`Error: ${data.error}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const requestStatus = document.getElementById('requestStatus');
                    const rawResponseDebug = document.getElementById('rawResponseDebug');
                    
                    if (requestStatus) {
                        requestStatus.textContent = `Error: ${error.message}`;
                    }
                    if (rawResponseDebug) {
                        rawResponseDebug.textContent = error.toString();
                    }
                    
                    // Reset upload button state
                    if (uploadButtonText) uploadButtonText.textContent = 'Upload Both Files & Analyze';
                    if (uploadSpinner) uploadSpinner.classList.add('hidden');
                    uploadButton.disabled = false;
                    
                    // Show error message
                    showUploadStatus(`Error: ${error.message}`, 'error');
                });
            }
        }, true); // Use capturing to run before the original handler
    }
    
    // Set up the Meesho input handlers
    setupMeeshoInputHandlers();
}); 