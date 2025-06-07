document.addEventListener('DOMContentLoaded', function() {
    // Buttons and modals
    const uploadAnalyticsBtn = document.getElementById('uploadAnalyticsBtn');
    const uploadEmptyBtn = document.getElementById('uploadEmptyBtn');
    const calculateMetricsBtn = document.getElementById('calculateMetricsBtn');
    const uploadModal = document.getElementById('uploadModal');
    const closeUploadModal = document.getElementById('closeUploadModal');
    const uploadModalOverlay = document.getElementById('uploadModalOverlay');
    const analysisModal = document.getElementById('analysisModal');
    const closeAnalysisModalBtn = document.getElementById('closeAnalysisModalBtn');
    const analysisModalOverlay = document.getElementById('analysisModalOverlay');
    const toggleDebugBtn = document.getElementById('toggleDebugBtn');
    const debugInfoContainer = document.getElementById('debugInfoContainer');
    
    // File upload elements
    const fileInput = document.getElementById('fileInput');
    const selectedFileName = document.getElementById('selectedFileName');
    const uploadForm = document.getElementById('uploadForm');
    const platformType = document.getElementById('platformType');
    const uploadButton = document.getElementById('uploadButton');
    const uploadButtonText = document.getElementById('uploadButtonText');
    const uploadSpinner = document.getElementById('uploadSpinner');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // Column mapping elements
    const advancedOptionsBtn = document.getElementById('advancedOptionsBtn');
    const advancedOptionsPanel = document.getElementById('advancedOptionsPanel');
    const columnMappingForm = document.getElementById('columnMappingForm');
    const columnMappingIssuesContainer = document.getElementById('columnMappingIssuesContainer');
    const columnMappingIssuesList = document.getElementById('columnMappingIssuesList');
    const modalColumnMappingIssues = document.getElementById('modalColumnMappingIssues');
    const modalColumnMappingIssuesList = document.getElementById('modalColumnMappingIssuesList');
    
    // Column mapping selects
    const salesAmountColumn = document.getElementById('salesAmountColumn');
    const orderDateColumn = document.getElementById('orderDateColumn');
    const productColumn = document.getElementById('productColumn');
    const locationColumn = document.getElementById('locationColumn');
    const quantityColumn = document.getElementById('quantityColumn');
    const transactionTypeColumn = document.getElementById('transactionTypeColumn');
    
    // Column mapping display elements
    const salesAmountMapping = document.getElementById('salesAmountMapping');
    const orderDateMapping = document.getElementById('orderDateMapping');
    const productNameMapping = document.getElementById('productNameMapping');
    const customerLocationMapping = document.getElementById('customerLocationMapping');
    const salesChannelMapping = document.getElementById('salesChannelMapping');
    const quantityMapping = document.getElementById('quantityMapping');
    
    // Dashboard content elements
    const noAnalysisMessage = document.getElementById('noAnalysisMessage');
    const analysisContent = document.getElementById('analysisContent');
    const dashboardSummaryCards = document.getElementById('dashboardSummaryCards');
    const dashboardTopProductsList = document.getElementById('dashboardTopProductsList');
    const dashboardTopRegionsList = document.getElementById('dashboardTopRegionsList');
    const platformSpecificResults = document.getElementById('platformSpecificResults');
    
    // Debug elements
    const requestStatus = document.getElementById('requestStatus');
    const rawResponseDebug = document.getElementById('rawResponseDebug');
    
    // Only initialize event listeners if elements exist
    if (toggleDebugBtn) {
        toggleDebugBtn.addEventListener('click', function() {
            debugInfoContainer.classList.toggle('hidden');
        });
    }
    
    // Open upload modal
    if (uploadAnalyticsBtn) {
        uploadAnalyticsBtn.addEventListener('click', function() {
            uploadModal.classList.remove('hidden');
        });
    }
    
    if (uploadEmptyBtn) {
        uploadEmptyBtn.addEventListener('click', function() {
            uploadModal.classList.remove('hidden');
        });
    }
    
    // Close upload modal
    if (closeUploadModal) {
        closeUploadModal.addEventListener('click', function() {
            uploadModal.classList.add('hidden');
        });
    }
    
    if (uploadModalOverlay) {
        uploadModalOverlay.addEventListener('click', function() {
            uploadModal.classList.add('hidden');
        });
    }
    
    // Close analysis modal
    if (closeAnalysisModalBtn) {
        closeAnalysisModalBtn.addEventListener('click', function() {
            analysisModal.classList.add('hidden');
        });
    }
    
    if (analysisModalOverlay) {
        analysisModalOverlay.addEventListener('click', function() {
            analysisModal.classList.add('hidden');
        });
    }
    
    // Update file name when selected
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                // Use the new handler function
                handleFileSelection(fileInput.files[0]);
            } else {
                selectedFileName.textContent = 'Choose file...';
                
                // Reset any previous upload status
                uploadStatus.innerHTML = '';
                uploadStatus.classList.add('hidden');
                
                // Reset column mapping issues
                columnMappingIssuesContainer.classList.add('hidden');
                columnMappingIssuesList.innerHTML = '';
            }
        });
    }
    
    // Function to handle file selection, including Excel file guidance
    function handleFileSelection(file) {
        if (!file) return;
        
        selectedFileName.textContent = file.name;
        
        // Reset any previous upload status
        uploadStatus.innerHTML = '';
        uploadStatus.classList.add('hidden');
        
        // Reset column mapping issues
        columnMappingIssuesContainer.classList.add('hidden');
        columnMappingIssuesList.innerHTML = '';
        
        // Reset column mapping dropdowns
        resetColumnMappingForm();
        
        // If it's an Excel file, add some helpful guidance
        if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
            showUploadStatus('Excel file detected. Ensure it has proper column headers in the first row for best results.', 'info');
            
            // Auto-show advanced options panel for Excel files
            if (advancedOptionsPanel) {
                advancedOptionsPanel.classList.remove('hidden');
            }
        }
        
        // Extract headers if it's a CSV file
        if (file.name.toLowerCase().endsWith('.csv')) {
            extractFileHeaders(file);
        }
    }
    
    // Toggle advanced options
    if (advancedOptionsBtn) {
        advancedOptionsBtn.addEventListener('click', function() {
            advancedOptionsPanel.classList.toggle('hidden');
        });
    }
    
    // Function to extract headers from CSV files
    function extractFileHeaders(file) {
        if (!file) return;
        
        // Update the UI to show file is being processed
        showUploadStatus('Processing file...', 'info');
        
        // Only process CSV files for header extraction
        if (file.name.toLowerCase().endsWith('.csv')) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                try {
                    const content = e.target.result;
                    const lines = content.split(/\r\n|\n|\r/);  // Handle different line endings
                    
                    if (lines.length > 0) {
                        // Try to detect the delimiter by examining the first few lines
                        let bestDelimiter = detectDelimiter(lines.slice(0, 5));
                        logger.info(`Detected delimiter: ${bestDelimiter}`);
                        
                        // Handle quoted cells with delimiters inside them
                        let headers = [];
                        const firstLine = lines[0].trim();
                        
                        // Parse CSV properly handling quoted strings
                        if (firstLine.includes('"')) {
                            // Use regex to handle quoted fields with delimiters inside
                            const regex = new RegExp(`"[^"]*"|[^"${bestDelimiter}]+`, 'g');
                            headers = [];
                            let matches = firstLine.match(regex) || [];
                            
                            for (let match of matches) {
                                // Remove quotes and trim
                                let header = match.replace(/^"(.*)"$/, '$1').trim();
                                if (header) headers.push(header);
                            }
                        } else {
                            // Simple split for non-quoted headers
                            headers = firstLine.split(bestDelimiter)
                                .map(header => header.trim())
                                .filter(header => header);
                        }
                        
                        // Clean headers - remove BOM marker, quotes, etc.
                        headers = headers.map(h => {
                            // Remove BOM mark if present
                            let clean = h.replace(/^\uFEFF/, '');
                            // Remove quotes and trim
                            clean = clean.replace(/^["'](.*)["']$/, '$1').trim();
                            return clean;
                        });
                        
                        console.log('Extracted headers:', headers);
                        
                        // Populate column mapping dropdowns with these headers
                        if (headers.length > 0) {
                            populateColumnMappingDropdowns(headers);
                            
                            // Show advanced options panel automatically if we have headers
                            if (advancedOptionsPanel) {
                                advancedOptionsPanel.classList.remove('hidden');
                            }
                            
                            // Set column mapping intelligently
                            intelligentColumnMapping(headers);
                            
                            // Update status
                            showUploadStatus(`Found ${headers.length} columns in the file. You can customize column mapping in Advanced Options.`, 'success');
                        } else {
                            showUploadStatus('Could not detect columns in CSV file. You may need to map columns manually after upload.', 'warning');
                        }
                    } else {
                        showUploadStatus('CSV file appears to be empty.', 'error');
                    }
                } catch (error) {
                    console.error('Error extracting headers:', error);
                    showUploadStatus('Error reading file headers. Try uploading anyway.', 'error');
                }
            };
            
            // Read just the beginning of the file to get headers
            try {
                const blob = file.slice(0, 8192);  // First 8KB should be enough for headers
                reader.readAsText(blob);
            } catch (error) {
                console.error('Error reading file slice:', error);
                showUploadStatus('Error reading file. Try a different file format.', 'error');
            }
        } else if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
            // For Excel files, we cannot easily extract headers without a library
            // Show a message that manual mapping will be available after initial processing
            showUploadStatus('Excel file detected. Column mapping will be available after initial processing.', 'info');
        }
    }
    
    // Function to detect the most likely delimiter in a CSV file
    function detectDelimiter(lines) {
        // Common delimiters to check
        const delimiters = [',', ';', '\t', '|', ':'];
        const scores = {};
        
        // Initialize scores
        delimiters.forEach(d => scores[d] = 0);
        
        // Analyze each line
        lines.forEach(line => {
            // Skip empty lines
            if (!line.trim()) return;
            
            // Check each delimiter
            delimiters.forEach(delimiter => {
                // Count occurrences
                const count = (line.match(new RegExp(delimiter === '\t' ? '\t' : delimiter, 'g')) || []).length;
                
                // Skip if no occurrences
                if (count === 0) return;
                
                // Check if all parts have roughly similar length (good sign of a delimiter)
                const parts = line.split(delimiter);
                
                // Check consistency of quoted strings
                const quoteBalance = (line.match(/"/g) || []).length % 2 === 0;
                
                // Add to score - higher points for more parts and balanced quotes
                scores[delimiter] += count * (quoteBalance ? 2 : 1) * parts.length;
            });
        });
        
        // Find the delimiter with the highest score
        let bestDelimiter = ',';  // Default to comma
        let highestScore = 0;
        
        Object.entries(scores).forEach(([delimiter, score]) => {
            if (score > highestScore) {
                highestScore = score;
                bestDelimiter = delimiter;
            }
        });
        
        return bestDelimiter;
    }
    
    // Function for intelligent column mapping
    function intelligentColumnMapping(columns) {
        console.log('Intelligent column mapping with columns:', columns);
        
        // Define keywords for each column type - comprehensive patterns
        const keywords = {
            sales_amount: [
                'sale', 'amount', 'revenue', 'price', 'total', 'value', 'gmv', 'income', 'earning',
                'turnover', 'payment', 'transaction', 'cost', 'subtotal', 'final', 'sum', 'money',
                'cash', 'paid', 'billing', 'receipt', 'trans', 'val', 'pay', 'inv', 'rs', 'inr',
                'rupee', 'rupees', '₹', '$', 'usd', 'eur', 'gbp', 'sales value', 'order value',
                'gross', 'net', 'profit', 'sales'
            ],
            order_date: [
                'date', 'time', 'order date', 'timestamp', 'created', 'ordered', 'purchase',
                'transaction', 'created_at', 'created_on', 'placed_at', 'placed_on', 'completed_at',
                'processed_at', 'checkout', 'confirm', 'sold', 'shipping_date', 'dt',
                'payment_date', 'processed', 'creation', 'order', 'calendar', 'day', 'month',
                'year', 'when', 'datetime'
            ],
            product_name: [
                'product', 'item', 'sku', 'name', 'title', 'description', 'goods', 'merchandise',
                'asin', 'model', 'brand', 'part', 'listing', 'variant', 'article', 'stock',
                'inventory', 'catalog', 'upc', 'ean', 'mpn', 'isbn', 'good', 'prod', 'id',
                'identifier', 'model', 'make', 'type', 'category', 'item name', 'product name',
                'product_name', 'product_title'
            ],
            customer_location: [
                'location', 'region', 'country', 'state', 'city', 'address', 'ship', 'destination',
                'delivery', 'postal', 'zip', 'pincode', 'territory', 'area', 'province', 'district',
                'county', 'town', 'place', 'billing', 'shipping', 'customer location', 'place', 
                'geo', 'location', 'loc', 'zone', 'pin', 'address'
            ],
            quantity: [
                'quantity', 'qty', 'units', 'count', 'pcs', 'pieces', 'number', 'volume', 'amount',
                'num', 'nos', 'item_count', 'unit_count', 'order_quantity', 'line_qty', 'ordered',
                'ct', 'cnt', 'qnty', 'qntty', 'quantity sold', 'ordered quantity'
            ],
            transaction_type: [
                'status', 'order status', 'order_status', 'transaction status', 'transaction_status',
                'transaction type', 'transaction_type', 'state', 'order state', 'order_state',
                'return status', 'return_status', 'delivery status', 'delivery_status',
                'shipment status', 'shipment_status', 'fulfillment status', 'fulfillment_status',
                'order type', 'order_type', 'payment status', 'payment_status', 'return', 'cancel',
                'refund', 'replace'
            ]
        };
        
        // Score each column for each type
        const scores = {
            sales_amount: {},
            order_date: {},
            product_name: {},
            customer_location: {},
            quantity: {},
            transaction_type: {}
        };
        
        // Score each column
        columns.forEach(column => {
            if (!column) return;
            
            const columnLower = column.toLowerCase();
            
            // For each category
            Object.keys(keywords).forEach(category => {
                let score = 0;
                
                // Check for exact matches
                if (keywords[category].includes(columnLower)) {
                    score += 10;
                }
                
                // Check for keyword presence
                keywords[category].forEach(keyword => {
                    // Full word match
                    const wordRegex = new RegExp(`\\b${keyword}\\b`, 'i');
                    if (wordRegex.test(columnLower)) {
                        score += 5;
                    } 
                    // Partial match
                    else if (columnLower.includes(keyword)) {
                        score += 2;
                    }
                    
                    // Handle compound words
                    if (columnLower.includes(`_${keyword}`) || 
                        columnLower.includes(`${keyword}_`) ||
                        columnLower.includes(`-${keyword}`) || 
                        columnLower.includes(`${keyword}-`)) {
                        score += 3;
                    }
                });
                
                // Additional heuristics
                
                // For dates
                if (category === 'order_date' && 
                    (/date|time|timestamp|dt/i.test(columnLower) || 
                    /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(columnLower.split(' ')[0]))) {
                    score += 3;
                }
                
                // For amounts
                if (category === 'sales_amount' && 
                    (/\$|€|£|¥|rs|inr|₹|usd|eur|gbp|price|cost|total/i.test(columnLower))) {
                    score += 3;
                }
                
                // For quantities
                if (category === 'quantity' && 
                    (/^qty$|^q$|^num$|^count$|^pcs$|^units$/i.test(columnLower) || 
                    /^no\._of/i.test(columnLower))) {
                    score += 4;
                }
                
                // Boost score for primary columns at beginning of compound words
                if ((category === 'product_name' && columnLower.startsWith('product')) ||
                    (category === 'sales_amount' && columnLower.startsWith('sales')) ||
                    (category === 'order_date' && columnLower.startsWith('order')) ||
                    (category === 'quantity' && columnLower.startsWith('qty'))) {
                    score += 3;
                }
                
                // Store score if positive
                if (score > 0) {
                    scores[category][column] = score;
                }
            });
        });
        
        console.log('Column mapping scores:', scores);
        
        // Get best match for each category
        const getBestMatch = (category) => {
            const categoryScores = scores[category];
            if (Object.keys(categoryScores).length === 0) return null;
            
            let bestMatch = null;
            let highestScore = 0;
            
            Object.entries(categoryScores).forEach(([column, score]) => {
                if (score > highestScore) {
                    highestScore = score;
                    bestMatch = column;
                }
            });
            
            return bestMatch;
        };
        
        // Set dropdown values based on best matches
        const salesAmountBest = getBestMatch('sales_amount');
        if (salesAmountBest && salesAmountColumn) {
            salesAmountColumn.value = salesAmountBest;
        }
        
        const orderDateBest = getBestMatch('order_date');
        if (orderDateBest && orderDateColumn) {
            orderDateColumn.value = orderDateBest;
        }
        
        const productNameBest = getBestMatch('product_name');
        if (productNameBest && productColumn) {
            productColumn.value = productNameBest;
        }
        
        const locationBest = getBestMatch('customer_location');
        if (locationBest && locationColumn) {
            locationColumn.value = locationBest;
        }
        
        const quantityBest = getBestMatch('quantity');
        if (quantityBest && quantityColumn) {
            quantityColumn.value = quantityBest;
        }
        
        const transactionTypeBest = getBestMatch('transaction_type');
        if (transactionTypeBest && transactionTypeColumn) {
            transactionTypeColumn.value = transactionTypeBest;
        }
        
        // Show success message with detection results
        const detectedColumns = [];
        if (salesAmountBest) detectedColumns.push(`Sales Amount: ${salesAmountBest}`);
        if (orderDateBest) detectedColumns.push(`Order Date: ${orderDateBest}`);
        if (productNameBest) detectedColumns.push(`Product: ${productNameBest}`);
        if (locationBest) detectedColumns.push(`Location: ${locationBest}`);
        if (quantityBest) detectedColumns.push(`Quantity: ${quantityBest}`);
        if (transactionTypeBest) detectedColumns.push(`Transaction Type: ${transactionTypeBest}`);
        
        if (detectedColumns.length > 0) {
            showUploadStatus(`Auto-detection complete! Detected: ${detectedColumns.join(', ')}`, 'success');
        } else {
            showUploadStatus('Could not confidently detect any columns. Please map them manually.', 'warning');
        }
    }
    
    // Function to populate column mapping dropdowns
    function populateColumnMappingDropdowns(availableColumns) {
        // Make sure all required elements exist
        if (!salesAmountColumn || !orderDateColumn || !productColumn || !locationColumn || !quantityColumn || !transactionTypeColumn) {
            console.error('One or more column mapping select elements not found');
            return;
        }
        
        console.log('Available columns for mapping:', availableColumns);
        
        // Clear existing options except the first one
        [salesAmountColumn, orderDateColumn, productColumn, locationColumn, quantityColumn, transactionTypeColumn].forEach(select => {
            while (select.options.length > 1) {
                select.remove(1);
            }
        });
        
        // Handle various array formats that might be received
        let columnsArray = availableColumns;
        
        // If availableColumns is an object with a tolist() method (sometimes serialized oddly)
        if (typeof availableColumns === 'object' && !Array.isArray(availableColumns) && availableColumns !== null) {
            // Try to convert to array
            try {
                columnsArray = Object.values(availableColumns);
            } catch (e) {
                console.error('Error converting columns to array:', e);
            }
        }
        
        // Ensure we have an array to work with
        if (!Array.isArray(columnsArray)) {
            console.error('Available columns is not an array:', availableColumns);
            columnsArray = [];
        }
        
        // Add available columns to each dropdown
        columnsArray.forEach(column => {
            if (column) {
                // Convert column to string (in case it's a number or other type)
                const columnStr = String(column).trim();
                if (columnStr) {
                    [salesAmountColumn, orderDateColumn, productColumn, locationColumn, quantityColumn, transactionTypeColumn].forEach(select => {
                        const option = document.createElement('option');
                        option.value = columnStr;
                        option.textContent = columnStr;
                        select.appendChild(option);
                    });
                }
            }
        });
        
        // Show the advanced options panel if we have columns
        if (columnsArray.length > 0 && advancedOptionsPanel) {
            advancedOptionsPanel.classList.remove('hidden');
            console.log('Advanced options panel shown with', columnsArray.length, 'columns');
        }
    }
    
    // Function to set current column mappings in the dropdowns
    function setCurrentColumnMappings(mapping) {
        if (!salesAmountColumn || !orderDateColumn || !productColumn || !locationColumn || !quantityColumn || !transactionTypeColumn) {
            console.error('One or more column mapping select elements not found');
            return;
        }
        
        try {
            // Helper function to find the best matching option for a value
            function findBestOptionMatch(selectElement, columnValue) {
                if (!columnValue || !selectElement) return null;
                
                const columnValueLower = columnValue.toLowerCase().trim();
                let bestMatch = null;
                let bestScore = 0;
                
                // Check all options
                for (let i = 0; i < selectElement.options.length; i++) {
                    const option = selectElement.options[i];
                    if (!option.value) continue; // Skip empty value (Auto-detect)
                    
                    const optionValueLower = option.value.toLowerCase().trim();
                    
                    // Different matching strategies with different scores
                    let score = 0;
                    
                    // Exact match (case-insensitive)
                    if (optionValueLower === columnValueLower) {
                        score = 100;
                    }
                    // Option contains column value entirely
                    else if (optionValueLower.includes(columnValueLower)) {
                        score = 75;
                    }
                    // Column value contains option value entirely
                    else if (columnValueLower.includes(optionValueLower)) {
                        score = 50;
                    }
                    // Partial word match
                    else {
                        // Split into words and check for matches
                        const optionWords = optionValueLower.split(/[_\s-]/);
                        const columnWords = columnValueLower.split(/[_\s-]/);
                        
                        // Count matching words
                        const matchingWords = optionWords.filter(word => 
                            columnWords.some(colWord => colWord.includes(word) || word.includes(colWord))
                        ).length;
                        
                        if (matchingWords > 0) {
                            // Score based on percentage of matching words
                            score = 25 + (matchingWords / Math.max(optionWords.length, columnWords.length)) * 25;
                        }
                    }
                    
                    // Update best match if this score is higher
                    if (score > bestScore) {
                        bestScore = score;
                        bestMatch = option.value;
                    }
                }
                
                console.log(`Best match for "${columnValue}": "${bestMatch}" (score: ${bestScore})`);
                return bestScore >= 25 ? bestMatch : null; // Only return if score is reasonable
            }
            
            // Set each mapping field
            const mappings = [
                { column: salesAmountColumn, value: mapping.sales_amount },
                { column: orderDateColumn, value: mapping.order_date },
                { column: productColumn, value: mapping.product_name },
                { column: locationColumn, value: mapping.customer_location },
                { column: quantityColumn, value: mapping.quantity },
                { column: transactionTypeColumn, value: mapping.transaction_type }
            ];
            
            // Track if any mapping was set
            let anyMappingSet = false;
            
            mappings.forEach(item => {
                if (item.value) {
                    // First try exact match
                    if (item.column.querySelector(`option[value="${item.value}"]`)) {
                        item.column.value = item.value;
                        anyMappingSet = true;
                } else {
                        // Try to find best match
                        const bestMatch = findBestOptionMatch(item.column, item.value);
                        if (bestMatch) {
                            item.column.value = bestMatch;
                            anyMappingSet = true;
                        }
                }
            }
        });
            
            // Show advanced options if any mapping was set
            if (anyMappingSet && advancedOptionsPanel) {
                advancedOptionsPanel.classList.remove('hidden');
            }
            
        } catch (error) {
            console.error('Error setting column mappings:', error);
        }
    }
    
    // Function to get manual column mappings from form
    function getManualColumnMappings() {
        const mappings = {};
        
        if (salesAmountColumn && salesAmountColumn.value) mappings.sales_amount = salesAmountColumn.value;
        if (orderDateColumn && orderDateColumn.value) mappings.order_date = orderDateColumn.value;
        if (productColumn && productColumn.value) mappings.product_name = productColumn.value;
        if (locationColumn && locationColumn.value) mappings.customer_location = locationColumn.value;
        if (quantityColumn && quantityColumn.value) mappings.quantity = quantityColumn.value;
        if (transactionTypeColumn && transactionTypeColumn.value) mappings.transaction_type = transactionTypeColumn.value;
        
        return mappings;
    }
    
    // Function to reset column mapping form
    function resetColumnMappingForm() {
        if (!salesAmountColumn || !orderDateColumn || !productColumn || !locationColumn || !quantityColumn || !transactionTypeColumn) {
                return;
            }
            
        [salesAmountColumn, orderDateColumn, productColumn, locationColumn, quantityColumn, transactionTypeColumn].forEach(select => {
            select.value = '';
            
            // Clear options except the first one
            while (select.options.length > 1) {
                select.remove(1);
            }
        });
    }
    
    // Function to show upload status message
    function showUploadStatus(message, type) {
        if (!uploadStatus) return;
        
        let bgColor = 'bg-blue-50 text-blue-700 border-blue-200'; // info style
        if (type === 'error') {
            bgColor = 'bg-red-50 text-red-700 border-red-200';
        } else if (type === 'success') {
            bgColor = 'bg-green-50 text-green-700 border-green-200';
        } else if (type === 'warning') {
            bgColor = 'bg-yellow-50 text-yellow-700 border-yellow-200';
        }
        
        uploadStatus.innerHTML = `<div class="${bgColor} border p-2 rounded-md text-sm">${message}</div>`;
        uploadStatus.classList.remove('hidden');
    }
    
    // Function to display column mapping issues
    function displayColumnMappingIssues(issues) {
        if (!columnMappingIssuesList || !modalColumnMappingIssuesList) return;
        
        columnMappingIssuesList.innerHTML = '';
        if (modalColumnMappingIssuesList) {
            modalColumnMappingIssuesList.innerHTML = '';
        }
        
        // Check if we're dealing with an Excel file with unnamed columns
        const hasUnnamedColumnsIssue = issues.some(issue => 
            issue.includes('unnamed columns') || 
            issue.includes('header row') || 
            issue.includes('merged cells')
        );
        
        // Add special Excel file guidance if needed
        if (hasUnnamedColumnsIssue) {
            const excelTipElement = document.createElement('div');
            excelTipElement.className = 'mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md';
            excelTipElement.innerHTML = `
                <p class="text-xs font-medium text-blue-700">Excel File Tips:</p>
                <ul class="text-xs text-blue-600 list-disc pl-5 mt-1">
                    <li>Make sure your first row contains column headers</li>
                    <li>Avoid merged cells in your header row</li>
                    <li>Remove any blank rows at the top of your file</li>
                    <li>Use the Advanced Options below to manually map columns</li>
                </ul>
            `;
            columnMappingIssuesContainer.appendChild(excelTipElement);
            
            // Auto-show advanced options when dealing with Excel file issues
            if (advancedOptionsPanel) {
                advancedOptionsPanel.classList.remove('hidden');
            }
        }
        
        issues.forEach(issue => {
            // Add to upload form
            const li = document.createElement('li');
            li.textContent = issue;
            columnMappingIssuesList.appendChild(li);
            
            // Add to modal
            if (modalColumnMappingIssuesList) {
                const modalLi = document.createElement('li');
                modalLi.textContent = issue;
                modalColumnMappingIssuesList.appendChild(modalLi);
            }
        });
        
        columnMappingIssuesContainer.classList.remove('hidden');
        if (modalColumnMappingIssues) {
            modalColumnMappingIssues.classList.remove('hidden');
        }
    }
    
    // Function to display analysis results in the modal
    function displayAnalysisResults(data) {
        // Display reliability warning if this is a small dataset
        if (data.analysis && data.analysis.summary && data.analysis.summary.reliability === "low") {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'mb-4 p-3 bg-orange-50 border border-orange-200 rounded-md';
            warningDiv.innerHTML = `
                <h5 class="text-sm font-medium text-orange-800 mb-2">Small Dataset Warning</h5>
                <p class="text-xs text-orange-700">
                    This analysis is based on a very small dataset (${data.analysis.summary.row_count} records).
                    Results may not be statistically significant or may not represent your actual business performance.
                    Consider uploading more data for better insights.
                </p>
            `;
            
            // Insert at the beginning of analysis content
            const analysisContent = document.getElementById('analysisContent');
            if (analysisContent) {
                analysisContent.prepend(warningDiv);
            }
        }
        
        // Display column mappings
        if (data.column_mapping) {
            // Clear previous content
            if (salesAmountMapping) salesAmountMapping.textContent = data.column_mapping.sales_amount || 'Not detected';
            if (orderDateMapping) orderDateMapping.textContent = data.column_mapping.order_date || 'Not detected';
            if (productNameMapping) productNameMapping.textContent = data.column_mapping.product_name || 'Not detected';
            if (customerLocationMapping) customerLocationMapping.textContent = data.column_mapping.customer_location || 'Not detected';
            if (salesChannelMapping) salesChannelMapping.textContent = data.column_mapping.sales_channel || 'Not detected';
            if (quantityMapping) quantityMapping.textContent = data.column_mapping.quantity || 'Not detected';
            if (document.getElementById('transactionTypeMapping')) document.getElementById('transactionTypeMapping').textContent = data.column_mapping.transaction_type || 'Not detected';
            
            // Add confidence indicators if available
            if (data.column_mapping._confidence) {
                updateMappingWithConfidence(data.column_mapping, data.column_mapping._confidence);
            }
        }
    }
    
    // Function to update mapping display with confidence indicators
    function updateMappingWithConfidence(mapping, confidence) {
        const mappingElements = {
            'sales_amount': salesAmountMapping,
            'order_date': orderDateMapping,
            'product_name': productNameMapping,
            'customer_location': customerLocationMapping,
            'sales_channel': salesChannelMapping,
            'quantity': quantityMapping,
            'transaction_type': document.getElementById('transactionTypeMapping')
        };
        
        // Update each mapping display with confidence indicators
        for (const [key, element] of Object.entries(mappingElements)) {
            if (!element || !mapping[key]) continue;
            
            const score = confidence[key] || 0;
            let indicator = '';
            let colorClass = '';
            
            if (score >= 0.8) {
                indicator = '✓';
                colorClass = 'text-green-500';
            } else if (score >= 0.6) {
                indicator = '⚠';
                colorClass = 'text-yellow-500';
                } else {
                indicator = '⚠';
                colorClass = 'text-orange-500';
            }
            
            // Create HTML for the mapping display
            element.innerHTML = `
                <span class="font-medium">${mapping[key]}</span>
                <span class="ml-1 ${colorClass} text-xs">${indicator}</span>
            `;
        }
    }
    
    // Function to update the dashboard with new analysis data
    function updateDashboard(analysisData) {
        if (!analysisData) return;
        
        // Make sure required elements exist
        if (!noAnalysisMessage || !analysisContent) return;
        
        // Show the analysis content and hide the empty state
        noAnalysisMessage.classList.add('hidden');
        analysisContent.classList.remove('hidden');
        
        // Update summary cards
        if (dashboardSummaryCards) {
            updateSummaryCards(analysisData.summary);
        }
        
        // Track which visualizations have data
        const visualizationsWithData = [];
        
        // Try to update sales trend chart
        const hasSalesTrend = analysisData.time_series && 
                             analysisData.time_series.labels && 
                             analysisData.time_series.data && 
                             analysisData.time_series.labels.length > 0 && 
                             typeof Chart !== 'undefined';
        
        // Try to update sales channel chart
        const hasSalesChannels = analysisData.sales_channels && 
                                analysisData.sales_channels.length > 0 && 
                                typeof Chart !== 'undefined';
        
        // Try to update top products list
        const hasTopProducts = analysisData.top_products && 
                              analysisData.top_products.length > 0 && 
                              dashboardTopProductsList;
        
        // Try to update top regions list
        const hasTopRegions = analysisData.top_regions && 
                             analysisData.top_regions.length > 0 && 
                             dashboardTopRegionsList;
                             
        // Check for transaction types data
        const hasTransactionTypes = analysisData.transaction_types && 
                                  analysisData.transaction_types.length > 0 && 
                                  typeof Chart !== 'undefined';
        
        // Get references to all containers
        const salesTrendContainer = document.getElementById('salesTrendContainer');
        const salesChannelContainer = document.getElementById('salesChannelContainer');
        const topProductsContainer = document.getElementById('topProductsContainer');
        const topRegionsContainer = document.getElementById('topRegionsContainer');
        const fallbackChartContainer = document.getElementById('fallbackChartContainer');
        const fallbackListContainer = document.getElementById('fallbackListContainer');
        const dataQualityContainer = document.getElementById('dataQualityContainer');
        
        // Hide all containers initially
        if (salesTrendContainer) salesTrendContainer.classList.add('hidden');
        if (salesChannelContainer) salesChannelContainer.classList.add('hidden');
        if (topProductsContainer) topProductsContainer.classList.add('hidden');
        if (topRegionsContainer) topRegionsContainer.classList.add('hidden');
        if (fallbackChartContainer) fallbackChartContainer.classList.add('hidden');
        if (fallbackListContainer) fallbackListContainer.classList.add('hidden');
        if (dataQualityContainer) dataQualityContainer.classList.add('hidden');
        
        // Update sales trend chart if data exists
        if (hasSalesTrend) {
            if (salesTrendContainer) salesTrendContainer.classList.remove('hidden');
            updateSalesTrendChart(analysisData.time_series);
            visualizationsWithData.push('salesTrend');
        }
        
        // Update sales channel chart if data exists
        if (hasSalesChannels) {
            if (salesChannelContainer) salesChannelContainer.classList.remove('hidden');
            updateSalesChannelChart(analysisData.sales_channels);
            visualizationsWithData.push('salesChannels');
        }
        
        // Update top products list if data exists
        if (hasTopProducts) {
            if (topProductsContainer) topProductsContainer.classList.remove('hidden');
            updateTopProductsList(analysisData.top_products);
            visualizationsWithData.push('topProducts');
        }
        
        // Update top regions list if data exists
        if (hasTopRegions) {
            if (topRegionsContainer) topRegionsContainer.classList.remove('hidden');
            updateTopRegionsList(analysisData.top_regions);
            visualizationsWithData.push('topRegions');
        }
        
        // Create fallback visualizations if needed
        if (!hasSalesTrend && !hasSalesChannels) {
            // If neither chart has data, check for alternative data to display
            let fallbackChartCreated = false;
            
            // First check if we have transaction_types to display
            if (hasTransactionTypes) {
                if (fallbackChartContainer) {
                    fallbackChartContainer.classList.remove('hidden');
                    createTransactionTypesChart(analysisData.transaction_types);
                    fallbackChartCreated = true;
                }
            }
            // Then try with summary data
            else if (analysisData.summary && Object.keys(analysisData.summary).length > 0) {
                if (fallbackChartContainer) {
                    fallbackChartContainer.classList.remove('hidden');
                    createSummaryFallbackChart(analysisData.summary);
                    fallbackChartCreated = true;
                }
            }
            
            // If even fallback chart can't be created, show data quality info
            if (!fallbackChartCreated && dataQualityContainer) {
                dataQualityContainer.classList.remove('hidden');
                updateDataQualityInfo(analysisData);
            }
        }
        
        // Create fallback list if needed
        if (!hasTopProducts && !hasTopRegions) {
            // If neither list has data, look for alternative data to display
            let fallbackListCreated = false;
            
            // Try with platform specific data
            if (analysisData.platform_specific && Object.keys(analysisData.platform_specific).length > 0) {
                if (fallbackListContainer) {
                    fallbackListContainer.classList.remove('hidden');
                    createPlatformSpecificList(analysisData.platform_specific);
                    fallbackListCreated = true;
                }
            }
            // Or try with column mapping info
            else if (analysisData.summary && analysisData.summary.column_mapping) {
                if (fallbackListContainer) {
                    fallbackListContainer.classList.remove('hidden');
                    createColumnMappingList(analysisData.summary.column_mapping);
                    fallbackListCreated = true;
                }
            }
            
            // If no fallback list could be created, show data quality info
            if (!fallbackListCreated && !dataQualityContainer.classList.contains('hidden') && dataQualityContainer) {
                dataQualityContainer.classList.remove('hidden');
                updateDataQualityInfo(analysisData);
            }
        }
        
        // Update platform-specific results if available
        if (analysisData.platform_specific && Object.keys(analysisData.platform_specific).length > 0 && platformSpecificResults) {
            updatePlatformSpecificResults(analysisData.platform_specific);
        }
    }
    
    // Function to create transaction types chart
    function createTransactionTypesChart(transactionTypes) {
        const ctx = document.getElementById('fallbackChart').getContext('2d');
        const fallbackChartTitle = document.getElementById('fallbackChartTitle');
        
        // Destroy existing chart if it exists
        if (window.fallbackChart) {
            window.fallbackChart.destroy();
        }
        
        // Set the chart title
        if (fallbackChartTitle) {
            fallbackChartTitle.textContent = 'Transaction Types';
        }
        
        // Prepare data for chart
        const labels = transactionTypes.map(type => type.name);
        const data = transactionTypes.map(type => type.count);
        const backgroundColors = [
            'rgba(123, 61, 243, 0.8)',  // Primary purple
            'rgba(255, 99, 132, 0.7)',  // Red
            'rgba(54, 162, 235, 0.7)',  // Blue
            'rgba(255, 206, 86, 0.7)',  // Yellow
            'rgba(75, 192, 192, 0.7)'   // Green
        ];
        
        // Create new chart
        window.fallbackChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    borderWidth: 1,
                    borderColor: 'rgba(255, 255, 255, 0.8)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 10,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const percentage = Math.round((context.raw / data.reduce((a, b) => a + b, 0)) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Helper function to create a summary fallback chart
    function createSummaryFallbackChart(summaryData) {
        const ctx = document.getElementById('fallbackChart').getContext('2d');
        const fallbackChartTitle = document.getElementById('fallbackChartTitle');
        
        // Destroy existing chart if it exists
        if (window.fallbackChart) {
            window.fallbackChart.destroy();
        }
        
        // Set the chart title
        if (fallbackChartTitle) {
            fallbackChartTitle.textContent = 'Sales Data Overview';
        }
        
        // Extract data for the fallback chart
        const labels = [];
        const data = [];
        
        // Try to find numeric data points to visualize
        const keysToCatch = [
            'total_sales', 'average_sale', 'total_transactions', 
            'average_order_size', 'total_products', 'top5_products_pct'
        ];
        
        for (const key of keysToCatch) {
            if (summaryData[key] !== undefined && !isNaN(summaryData[key])) {
                // Format the label to be more readable
                const formattedLabel = key
                    .split('_')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');
                
                labels.push(formattedLabel);
                data.push(summaryData[key]);
            }
        }
        
        // If we don't have enough data, try to add more points
        if (labels.length < 3 && summaryData.reliability) {
            labels.push('Data Quality');
            data.push(summaryData.reliability === 'high' ? 100 : 
                      summaryData.reliability === 'medium' ? 50 : 20);
        }
        
        // Create the fallback chart
        if (labels.length > 0) {
            window.fallbackChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Sales Data',
                        data: data,
                        backgroundColor: [
                            'rgba(123, 61, 243, 0.8)',
                            'rgba(123, 61, 243, 0.6)',
                            'rgba(123, 61, 243, 0.4)',
                            'rgba(123, 61, 243, 0.2)',
                            'rgba(123, 61, 243, 0.1)'
                        ],
                        borderColor: 'rgba(123, 61, 243, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw;
                                    if (context.label.includes('Sales') || context.label.includes('Average')) {
                                        return formatCurrency(value);
                                    } else if (context.label.includes('Pct') || context.label.includes('Quality')) {
                                        return `${value}%`;
                                    } else {
                                        return formatNumber(value);
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    // Simplify display based on magnitude
                                    if (value > 1000) {
                                        return formatCurrencyShort(value);
                                    } else {
                                        return value;
                                    }
                                }
                            }
                        }
                    }
                }
            });
        } else {
            // If no data at all, show an empty state
            window.fallbackChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data Available'],
                    datasets: [{
                        label: 'No Data',
                        data: [0],
                        backgroundColor: 'rgba(123, 61, 243, 0.1)',
                        borderColor: 'rgba(123, 61, 243, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1
                        }
                    }
                }
            });
        }
    }
    
    // Helper function to create a platform-specific list
    function createPlatformSpecificList(platformData) {
        const fallbackList = document.getElementById('fallbackList');
        const fallbackListTitle = document.getElementById('fallbackListTitle');
        
        if (!fallbackList || !fallbackListTitle) return;
        
        // Clear previous content
        fallbackList.innerHTML = '';
        
        // Set the title based on data
        let platformType = 'Platform';
        if (platformData._detected_format) {
            platformType = platformData._detected_format.charAt(0).toUpperCase() + platformData._detected_format.slice(1);
        }
        fallbackListTitle.textContent = `${platformType} Metrics`;
        
        // Create list items from platform data
        Object.entries(platformData).forEach(([key, value]) => {
            // Skip metadata keys
            if (key.startsWith('_') || key === 'error') return;
            
            // Format the key for display
            const formattedKey = key
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            // Format value based on key name
            let formattedValue = value;
            if (typeof value === 'number') {
                if (key.includes('rate') || key.includes('percentage')) {
                    formattedValue = `${value.toFixed(1)}%`;
                } else if (key.includes('sales') || key.includes('revenue') || key.includes('fee')) {
                    formattedValue = formatCurrency(value);
                } else {
                    formattedValue = formatNumber(value);
                }
            }
            
            // Create the list item
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between';
            item.innerHTML = `
                <div class="text-sm text-gray-600">${formattedKey}</div>
                <div class="text-sm font-medium text-gray-700">${formattedValue}</div>
            `;
            
            fallbackList.appendChild(item);
        });
        
        // If no items were added, show a message
        if (fallbackList.children.length === 0) {
            fallbackList.innerHTML = `
                <div class="text-sm text-gray-500 text-center py-2">
                    No platform-specific data available
                </div>
            `;
        }
    }
    
    // Helper function to create a column mapping list
    function createColumnMappingList(columnMapping) {
        const fallbackList = document.getElementById('fallbackList');
        const fallbackListTitle = document.getElementById('fallbackListTitle');
        
        if (!fallbackList || !fallbackListTitle) return;
        
        // Clear previous content
        fallbackList.innerHTML = '';
        
        // Set the title
        fallbackListTitle.textContent = 'Detected Columns';
        
        // Create list items from column mapping
        Object.entries(columnMapping).forEach(([key, value]) => {
            // Skip metadata keys
            if (key.startsWith('_') || !value) return;
            
            // Format the key for display
            const formattedKey = key
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            // Create the list item
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between';
            item.innerHTML = `
                <div class="text-sm text-gray-600">${formattedKey}</div>
                <div class="text-sm font-medium text-gray-700 truncate max-w-[200px]">${value}</div>
            `;
            
            fallbackList.appendChild(item);
        });
        
        // If no items were added, show a message
        if (fallbackList.children.length === 0) {
            fallbackList.innerHTML = `
                <div class="text-sm text-gray-500 text-center py-2">
                    No column mapping information available
                </div>
            `;
        }
    }
    
    // Helper function to update data quality information
    function updateDataQualityInfo(analysisData) {
        const dataQualityContent = document.getElementById('dataQualityContent');
        if (!dataQualityContent) return;
        
        // Clear previous content
        dataQualityContent.innerHTML = '';
        
        // Create content based on analysis data
        let content = '';
        
        // Data reliability
        if (analysisData.summary && analysisData.summary.reliability) {
            const reliabilityClass = 
                analysisData.summary.reliability === 'high' ? 'text-green-600' :
                analysisData.summary.reliability === 'medium' ? 'text-yellow-600' : 'text-orange-600';
            
            content += `
                <div class="mb-3">
                    <div class="font-medium mb-1">Data Reliability:</div>
                    <div class="${reliabilityClass} font-medium">
                        ${analysisData.summary.reliability.charAt(0).toUpperCase() + analysisData.summary.reliability.slice(1)}
                    </div>
                </div>
            `;
        }
        
        // Row and column count
        if (analysisData.summary && analysisData.summary.row_count !== undefined) {
            content += `
                <div class="mb-3">
                    <div class="font-medium mb-1">Dataset Size:</div>
                    <div>${formatNumber(analysisData.summary.row_count)} rows × ${analysisData.summary.column_count || 'unknown'} columns</div>
                </div>
            `;
        }
        
        // Column mapping issues
        if (analysisData.summary && analysisData.summary.column_mapping_issues && analysisData.summary.column_mapping_issues.length > 0) {
            content += `
                <div class="mb-3">
                    <div class="font-medium mb-1">Column Mapping Issues:</div>
                    <ul class="list-disc pl-5 text-xs text-orange-600 space-y-1">
            `;
            
            analysisData.summary.column_mapping_issues.forEach(issue => {
                content += `<li>${issue}</li>`;
            });
            
            content += `
                    </ul>
                </div>
            `;
        }
        
        // Recommendations
        content += `
            <div>
                <div class="font-medium mb-1">Recommendations:</div>
                <ul class="list-disc pl-5 text-xs space-y-1">
        `;
        
        // Add appropriate recommendations based on data quality
        if (analysisData.summary && analysisData.summary.row_count < 10) {
            content += `<li>Upload more data for better analysis (minimum 10 rows recommended)</li>`;
        }
        
        if (analysisData.summary && analysisData.summary.column_mapping_issues) {
            content += `<li>Improve column names in your source file for better detection</li>`;
            content += `<li>Use manual column mapping for better results</li>`;
        }
        
        content += `
                </ul>
            </div>
        `;
        
        dataQualityContent.innerHTML = content;
    }
    
    // Helper functions for updating specific dashboard sections
    function updateSummaryCards(summaryData) {
        if (!summaryData) return;
        
        dashboardSummaryCards.innerHTML = '';
        
        // Add reliability warning for small datasets
        if (summaryData.reliability === "low") {
            const reliabilityWarning = document.createElement('div');
            reliabilityWarning.className = 'bg-orange-50 rounded-lg shadow p-4 border border-orange-200 col-span-2 sm:col-span-3 md:col-span-4';
            reliabilityWarning.innerHTML = `
                <div class="flex items-start">
                    <div class="text-orange-500 mr-3">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-orange-800">Small Dataset Warning</div>
                        <div class="text-xs text-orange-700 mt-1">
                            This analysis is based on a very small dataset (fewer than 5 records).
                            Results may not be statistically significant. Consider uploading more data for better insights.
                        </div>
                    </div>
                </div>
            `;
            dashboardSummaryCards.appendChild(reliabilityWarning);
        }
        
        // Create cards for key metrics
        const metrics = [];
        
        // Only add metrics that actually have data
        if (summaryData.total_sales !== undefined) {
            metrics.push({ label: 'Total Sales', value: formatCurrency(summaryData.total_sales), icon: 'cash' });
        }
        
        // Removed total_transactions metric as requested
        
        if (summaryData.average_sales !== undefined) {
            metrics.push({ label: 'Avg. Sale', value: formatCurrency(summaryData.average_sales), icon: 'chart-bar' });
        }
        
        // Add growth metric if available
        if (summaryData.sales_growth && summaryData.sales_growth.rate !== undefined) {
            metrics.push({
                label: 'Growth Rate',
                value: `${summaryData.sales_growth.rate > 0 ? '+' : ''}${summaryData.sales_growth.rate.toFixed(1)}%`,
                icon: 'trending-up',
                color: summaryData.sales_growth.rate >= 0 ? 'text-green-500' : 'text-red-500'
            });
        }
        
        // Add return rate if available
        if (summaryData.return_rate !== undefined) {
            metrics.push({
                label: 'Return Rate',
                value: `${summaryData.return_rate.toFixed(1)}%`,
                icon: 'refresh',
                color: summaryData.return_rate > 10 ? 'text-red-500' : 
                       summaryData.return_rate > 5 ? 'text-orange-500' : 'text-green-500'
            });
        }
        
        // Add cancellation rate if available
        if (summaryData.cancellation_rate !== undefined) {
            metrics.push({
                label: 'Cancel Rate',
                value: `${summaryData.cancellation_rate.toFixed(1)}%`,
                icon: 'x-circle',
                color: summaryData.cancellation_rate > 10 ? 'text-red-500' : 
                       summaryData.cancellation_rate > 5 ? 'text-orange-500' : 'text-green-500'
            });
        }
        
        // Add total return amount if available
        if (summaryData.total_return_amount !== undefined) {
            metrics.push({
                label: 'Return Amount',
                value: formatCurrency(summaryData.total_return_amount),
                icon: 'arrow-left',
                color: 'text-orange-500'
            });
        }
        
        // Add total replacements if available
        if (summaryData.total_replacements !== undefined) {
            metrics.push({
                label: 'Replacements',
                value: formatNumber(summaryData.total_replacements),
                icon: 'refresh',
                color: 'text-blue-500'
            });
        }
        
        // Add any additional metrics that are available
        if (summaryData.total_products) {
            metrics.push({ label: 'Products', value: formatNumber(summaryData.total_products), icon: 'cube' });
        }
        
        if (summaryData.total_regions) {
            metrics.push({ label: 'Regions', value: formatNumber(summaryData.total_regions), icon: 'globe' });
        }
        
        // Create and append the cards
        metrics.forEach(metric => {
            const card = document.createElement('div');
            card.className = 'bg-white rounded-lg shadow p-4 border border-gray-100';
            card.innerHTML = `
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-xs text-gray-500">${metric.label}</div>
                        <div class="text-lg font-semibold mt-1 ${metric.color || 'text-gray-800'}">${metric.value}</div>
                    </div>
                    <div class="text-gray-400">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                </div>
            </div>
        `;
            dashboardSummaryCards.appendChild(card);
        });
        
        // If there are column mapping issues, add a warning card
        if (summaryData.column_mapping_issues && summaryData.column_mapping_issues.length > 0) {
            const warningCard = document.createElement('div');
            warningCard.className = 'bg-yellow-50 rounded-lg shadow p-4 border border-yellow-200 col-span-2';
            warningCard.innerHTML = `
                <div class="flex items-start">
                    <div class="text-yellow-500 mr-3">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-yellow-800">Column mapping issues detected</div>
                        <div class="text-xs text-yellow-700 mt-1">Some columns could not be properly identified. Analysis may be limited.</div>
                    </div>
                </div>
            `;
            dashboardSummaryCards.appendChild(warningCard);
        }
    }

    function updateSalesTrendChart(timeSeriesData) {
        const ctx = document.getElementById('dashboardSalesTrendChart').getContext('2d');
        
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }
        
        // Destroy existing chart if it exists
        if (window.salesTrendChart) {
            window.salesTrendChart.destroy();
        }
        
        // Handle very small datasets (fewer than 3 data points)
        if (timeSeriesData.labels.length < 3) {
            // Create a very simple display for limited data
            const placeholderData = {
                labels: timeSeriesData.labels.length > 0 ? timeSeriesData.labels : ['No Data'],
                datasets: [{
                    label: 'Sales',
                    data: timeSeriesData.data.length > 0 ? timeSeriesData.data : [0],
                    backgroundColor: 'rgba(123, 61, 243, 0.1)',
                    borderColor: 'rgba(123, 61, 243, 1)',
                    borderWidth: 2,
                    tension: 0,
                    fill: true
                }]
            };
            
            // Create chart with limited data message
            window.salesTrendChart = new Chart(ctx, {
                type: 'bar',  // Use bar chart for few data points
                data: placeholderData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return formatCurrency(context.raw);
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: 'Limited Data Available',
                            color: '#666',
                            font: {
                                size: 12
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatCurrencyShort(value);
                                }
                            }
                        }
                    }
                }
            });
            return;
        }
        
        // Create new chart for normal datasets
        window.salesTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeSeriesData.labels,
                datasets: [{
                    label: 'Sales',
                    data: timeSeriesData.data,
                    backgroundColor: 'rgba(123, 61, 243, 0.1)',
                    borderColor: 'rgba(123, 61, 243, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return formatCurrency(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    }
                }
            }
        });
    }

    function updateTopProductsList(productsData) {
        dashboardTopProductsList.innerHTML = '';
        
        // Create list items for top products
        productsData.slice(0, 5).forEach((product, index) => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between';
            
            const percentage = (product.value / productsData[0].value) * 100;
            
            item.innerHTML = `
                <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-700 mr-2">${index + 1}.</div>
                    <div class="text-sm text-gray-600 truncate max-w-[150px]">${product.name}</div>
                </div>
                <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-700 mr-2">${formatCurrency(product.value)}</div>
                    <div class="w-20 bg-gray-200 rounded-full h-2">
                        <div class="bg-[#7B3DF3] h-2 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
            
            dashboardTopProductsList.appendChild(item);
        });
    }

    function updateTopRegionsList(regionsData) {
        dashboardTopRegionsList.innerHTML = '';
        
        // Create list items for top regions
        regionsData.slice(0, 5).forEach((region, index) => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between';
            
            const percentage = (region.value / regionsData[0].value) * 100;
            
            item.innerHTML = `
                <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-700 mr-2">${index + 1}.</div>
                    <div class="text-sm text-gray-600 truncate max-w-[150px]">${region.name}</div>
                </div>
                <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-700 mr-2">${formatCurrency(region.value)}</div>
                    <div class="w-20 bg-gray-200 rounded-full h-2">
                        <div class="bg-[#7B3DF3] h-2 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
            
            dashboardTopRegionsList.appendChild(item);
        });
    }

    function updateSalesChannelChart(channelsData) {
        const ctx = document.getElementById('dashboardSalesChannelChart').getContext('2d');
        
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }
        
        // Destroy existing chart if it exists
        if (window.salesChannelChart) {
            window.salesChannelChart.destroy();
        }
        
        // Prepare data for chart
        const labels = channelsData.map(channel => channel.name);
        const data = channelsData.map(channel => channel.value);
        const backgroundColors = [
            'rgba(123, 61, 243, 0.8)',
            'rgba(123, 61, 243, 0.6)',
            'rgba(123, 61, 243, 0.4)',
            'rgba(123, 61, 243, 0.2)',
            'rgba(123, 61, 243, 0.1)'
        ];
        
        // Create new chart
        window.salesChannelChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 10,
                            font: {
                                size: 10
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = formatCurrency(context.raw);
                                const percentage = Math.round((context.raw / data.reduce((a, b) => a + b, 0)) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    function updatePlatformSpecificResults(platformData) {
        platformSpecificResults.innerHTML = '';
        platformSpecificResults.classList.remove('hidden');
        
        // Create header
        const header = document.createElement('div');
        header.className = 'flex items-center justify-between mb-4';
        header.innerHTML = `
            <h3 class="text-lg font-semibold text-gray-800">Platform-Specific Insights</h3>
        `;
        platformSpecificResults.appendChild(header);
        
        // Create grid for platform metrics
        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4';
        
        // Add each metric as a card
        Object.entries(platformData).forEach(([key, value]) => {
            // Skip error entries and metadata keys
            if (key === 'error' || key.startsWith('_')) return;
            
            // Format the key for display
            const formattedKey = key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
            
            // Format the value based on its type
            let formattedValue = value;
            if (typeof value === 'number') {
                // Format as percentage if the key suggests it
                if (key.includes('rate') || key.includes('percentage')) {
                    formattedValue = `${value.toFixed(1)}%`;
                } 
                // Format as currency if it looks like a monetary value
                else if (key.includes('sales') || key.includes('revenue') || key.includes('fee')) {
                    formattedValue = formatCurrency(value);
                }
                // Format as number otherwise
                else {
                    formattedValue = formatNumber(value);
                }
            }
            
            const card = document.createElement('div');
            card.className = 'bg-white rounded-lg shadow p-4 border border-gray-100';
            card.innerHTML = `
                <div class="text-xs text-gray-500">${formattedKey}</div>
                <div class="text-lg font-semibold mt-1 text-gray-800">${formattedValue}</div>
            `;
            
            grid.appendChild(card);
        });
        
        platformSpecificResults.appendChild(grid);
    }

    // Utility functions for formatting
    function formatCurrency(value) {
        if (value === undefined || value === null) return 'N/A';
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value);
    }

    function formatCurrencyShort(value) {
        if (value === undefined || value === null) return 'N/A';
        if (value >= 10000000) return '₹' + (value / 10000000).toFixed(1) + 'Cr';
        if (value >= 100000) return '₹' + (value / 100000).toFixed(1) + 'L';
        if (value >= 1000) return '₹' + (value / 1000).toFixed(1) + 'K';
        return '₹' + value.toFixed(0);
    }

    function formatNumber(value) {
        if (value === undefined || value === null) return 'N/A';
        return new Intl.NumberFormat('en-IN').format(value);
    }
    
    // ... existing code ...
    
    // Event listeners
    if (uploadAnalyticsBtn) {
        uploadAnalyticsBtn.addEventListener('click', function() {
            uploadModal.classList.remove('hidden');
        });
    }
    
    // Add event listener for auto-detect button
    const autoDetectBtn = document.getElementById('autoDetectBtn');
    if (autoDetectBtn) {
        autoDetectBtn.addEventListener('click', function() {
            const availableColumns = [];
            
            // Get all available column options
            if (salesAmountColumn) {
                for (let i = 1; i < salesAmountColumn.options.length; i++) {
                    availableColumns.push(salesAmountColumn.options[i].value);
                }
            }
            
            if (availableColumns.length > 0) {
                // Show the column mapping is being processed
                showUploadStatus('Auto-detecting columns...', 'info');
                
                // Use the intelligent column mapping
                intelligentColumnMapping(availableColumns);
            } else {
                showUploadStatus('No columns available for auto-detection. Please upload a file first.', 'error');
            }
        });
    }
    
    // Handle form submission
    if (uploadButton) {
        uploadButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (!fileInput.files.length) {
                showUploadStatus('Please select a file first.', 'error');
            return;
        }
        
            // Show loading state
            uploadButtonText.textContent = 'Analyzing...';
            uploadSpinner.classList.remove('hidden');
            uploadButton.disabled = true;
            
            // Prepare form data
            const formData = new FormData(uploadForm);
            
            // Add manual column mappings if provided
            const manualMappings = getManualColumnMappings();
            if (Object.keys(manualMappings).length > 0) {
                formData.append('manual_column_mapping', JSON.stringify(manualMappings));
            }
            
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
                if (requestStatus) {
                    requestStatus.textContent = 'Success: File uploaded and analyzed';
                }
                if (rawResponseDebug) {
                    rawResponseDebug.textContent = JSON.stringify(data, null, 2);
                }
                
                // Reset upload button state
                uploadButtonText.textContent = 'Upload & Analyze';
                uploadSpinner.classList.add('hidden');
                uploadButton.disabled = false;
                
                if (data.success) {
                    // Show success message
                    showUploadStatus('Analysis completed successfully!', 'success');
                    
                    // Check for column mapping issues
                    if (data.column_mapping_issues && data.column_mapping_issues.length > 0) {
                        displayColumnMappingIssues(data.column_mapping_issues);
                    }
                    
                    // Update column mapping form with available columns
                    if (data.available_columns && data.available_columns.length > 0) {
                        populateColumnMappingDropdowns(data.available_columns);
                        
                        // Set current mappings if available
                        if (data.column_mapping) {
                            setCurrentColumnMappings(data.column_mapping);
                        }
                    }
                    
                    // Display the results
                    displayAnalysisResults(data);
                    
                    // Close the upload modal after a short delay
                    setTimeout(() => {
                        uploadModal.classList.add('hidden');
                        
                        // Show analysis modal if there are results
                        if (data.analysis && analysisModal) {
                            analysisModal.classList.remove('hidden');
                        }
                        
                        // Update the dashboard with the new analysis
                        updateDashboard(data.analysis);
                    }, 1000);
                } else {
                    // Show error message
                    showUploadStatus(`Error: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (requestStatus) {
                    requestStatus.textContent = `Error: ${error.message}`;
                }
                if (rawResponseDebug) {
                    rawResponseDebug.textContent = error.toString();
                }
                
                // Reset upload button state
                uploadButtonText.textContent = 'Upload & Analyze';
                uploadSpinner.classList.add('hidden');
                uploadButton.disabled = false;
                
                // Show error message
                showUploadStatus(`Error: ${error.message}`, 'error');
            });
        });
    }

    // Function to calculate and display sales metrics
    function calculateSalesMetrics(file, columnMapping = null, platformType = null) {
        // Create form data for API request
        const formData = new FormData();
        
        // Handle Meesho platform specially (requires two files)
        if (platformType === 'meesho') {
            // Check if we have two files for Meesho
            if (!Array.isArray(file) || file.length !== 2) {
                showUploadStatus('Meesho analysis requires both sales and returns files.', 'error');
                return;
            }
            
            // Add the files to formData
            formData.append('sales_file', file[0]);
            formData.append('returns_file', file[1]);
            formData.append('platform_type', 'meesho');
            
            showUploadStatus('Processing Meesho sales and returns files...', 'info');
        } else {
            // Standard single-file handling for other platforms
            formData.append('file', file);
            
            // Add platform type if provided
            if (platformType) {
                formData.append('platform_type', platformType);
            }
        }
        
        // Add column mapping if provided
        if (columnMapping) {
            formData.append('manual_column_mapping', JSON.stringify(columnMapping));
        }
        
        // Show loading state
        showUploadStatus('Calculating sales metrics...', 'info');
        
        // Make API request
        fetch('/business_analytics/api/metrics/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Failed to calculate metrics');
                });
            }
            return response.json();
        })
        .then(metrics => {
            console.log('📊 Received metrics:', metrics);
            
            // Display the metrics - API now returns metrics object directly
            displaySalesMetrics(metrics);
            
            // Update debug info
            if (rawResponseDebug) {
                rawResponseDebug.textContent = JSON.stringify(metrics, null, 2);
            }
            
            // Update request status
            if (requestStatus) {
                requestStatus.innerHTML = '<span class="text-green-600">✓ Metrics calculation successful</span>';
            }
            
            // Show the analysis content
            if (document.getElementById('analysisContent')) {
                document.getElementById('analysisContent').classList.remove('hidden');
            }
            if (document.getElementById('noAnalysisMessage')) {
                document.getElementById('noAnalysisMessage').classList.add('hidden');
            }
            
            // Update time series chart if available
            if (metrics.time_series && typeof createConsolidatedTimeSeriesChart === 'function') {
                createConsolidatedTimeSeriesChart(metrics);
            }
            
            // Create high returns products list if available
            if (metrics.high_return_products && metrics.high_return_products.length > 0 && 
                typeof createHighReturnsProductsList === 'function') {
                createHighReturnsProductsList(metrics, metrics.high_return_products);
            }
            
            // Show the debug information container
            if (debugInfoContainer) {
                debugInfoContainer.classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('Error calculating metrics:', error);
            showUploadStatus('Error: ' + error.message, 'error');
            
            // Update request status
            if (requestStatus) {
                requestStatus.innerHTML = '<span class="text-red-600">✗ Error: ' + error.message + '</span>';
            }
        });
    }

    // Function to display calculated sales metrics
    function displaySalesMetrics(metrics) {
        console.log('📊 Displaying metrics:', metrics);
        
        // Create or get metrics container
        let metricsContainer = document.getElementById('salesMetricsContainer');
        if (!metricsContainer) {
            // Create container if it doesn't exist
            metricsContainer = document.createElement('div');
            metricsContainer.id = 'salesMetricsContainer';
            metricsContainer.className = 'bg-white rounded-[20px] shadow-[0_4px_16px_0_rgba(123,61,243,0.07)] p-4 sm:p-7 border border-[#F0EFFF] mt-6';
            
            // Add a title
            const title = document.createElement('h2');
            title.className = 'font-bold text-base sm:text-lg text-[#232323] mb-4';
            title.style.fontFamily = "'Montserrat', sans-serif";
            title.textContent = 'Sales Metrics Analysis';
            metricsContainer.appendChild(title);
            
            // Create metrics grid
            const metricsGrid = document.createElement('div');
            metricsGrid.id = 'metricsGrid';
            metricsGrid.className = 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4';
            metricsContainer.appendChild(metricsGrid);
            
            // Add container to the page
            document.querySelector('.w-full.sm\\:py-6.md\\:py-2').appendChild(metricsContainer);
        }
        
        // Get the metrics grid
        const metricsGrid = document.getElementById('metricsGrid');
        metricsGrid.innerHTML = '';
        
        // Define ONLY the 8 required metrics cards
        const metricCards = [
            { key: 'total_sales', label: 'Total Sales', format: formatCurrency },
            { key: 'average_sales', label: 'Average Sales', format: formatCurrency },
            { key: 'return_rate', label: 'Return Rate', format: value => value + '%' },
            { key: 'cancellation_rate', label: 'Cancellation Rate', format: value => value + '%' },
            { key: 'total_return_amount', label: 'Total Return Amount', format: formatCurrency },
            { key: 'total_replacements', label: 'Total Replacements', format: formatNumber },
            { key: 'total_regions', label: 'Total Unique Regions', format: formatNumber },
            { key: 'total_products', label: 'Total Products', format: formatNumber }
        ];
        
        // Create metric cards
        metricCards.forEach(card => {
            const metricCard = document.createElement('div');
            
            // Add special highlight for high cancellation rate
            if (card.key === 'cancellation_rate' && metrics[card.key] > 15) {
                metricCard.className = 'bg-red-50 p-4 rounded-lg border border-red-200';
                
                // Add warning tooltip
                const warningIcon = document.createElement('div');
                warningIcon.className = 'text-red-500 text-xs flex items-center mb-1';
                warningIcon.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>High cancellation rate detected!</span>
                `;
                metricCard.appendChild(warningIcon);
            } else if (card.key === 'return_rate' && metrics[card.key] > 15) {
                metricCard.className = 'bg-orange-50 p-4 rounded-lg border border-orange-200';
                
                // Add warning tooltip
                const warningIcon = document.createElement('div');
                warningIcon.className = 'text-orange-500 text-xs flex items-center mb-1';
                warningIcon.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>High return rate detected!</span>
                `;
                metricCard.appendChild(warningIcon);
            } else {
                metricCard.className = 'bg-gray-50 p-4 rounded-lg border border-gray-100';
            }
            
            const metricLabel = document.createElement('div');
            metricLabel.className = 'text-sm text-gray-600 mb-1';
            metricLabel.textContent = card.label;
            
            const metricValue = document.createElement('div');
            
            // Add special coloring based on metric type
            if (card.key === 'return_rate' || card.key === 'cancellation_rate') {
                const value = metrics[card.key] != null ? metrics[card.key] : 0;
                if (value > 15) {
                    metricValue.className = 'text-lg font-bold text-red-600';
                } else if (value > 10) {
                    metricValue.className = 'text-lg font-bold text-orange-600';
                } else {
                    metricValue.className = 'text-lg font-bold text-green-600';
                }
            } else {
                metricValue.className = 'text-lg font-bold text-gray-800';
            }
            
            // Ensure we have a value (default to 0 if not present or null)
            const value = metrics[card.key] != null ? metrics[card.key] : 0;
            metricValue.textContent = card.format(value);
            
            metricCard.appendChild(metricLabel);
            metricCard.appendChild(metricValue);
            metricsGrid.appendChild(metricCard);
        });
        
        // Show success message
        showUploadStatus('Sales metrics calculated successfully', 'success');
        
        // Show returns vs cancellations chart if data is available
        if (metrics.return_rate !== undefined && metrics.cancellation_rate !== undefined) {
            const returnsVsCancellationsContainer = document.getElementById('returnsVsCancellationsContainer');
            if (returnsVsCancellationsContainer) {
                returnsVsCancellationsContainer.classList.remove('hidden');
                // Call the enhanced chart function from enhanced_charts.js
                if (typeof createReturnsVsCancellationsChart === 'function') {
                    createReturnsVsCancellationsChart(metrics);
                } else {
                    console.error('createReturnsVsCancellationsChart function not found');
                }
            }
        }
        
        // Show top products chart/list if available
        if (metrics.top_products && metrics.top_products.length > 0) {
            const topProductsContainer = document.getElementById('topProductsContainer');
            if (topProductsContainer) {
                topProductsContainer.classList.remove('hidden');
                // Use the dashboardTopProductsList container
                const topProductsList = document.getElementById('dashboardTopProductsList');
                if (topProductsList) {
                    topProductsList.innerHTML = '';
                    if (typeof createTopProductsChart === 'function') {
                        createTopProductsChart(metrics, metrics.top_products);
                    } else {
                        // Fallback to basic list rendering
                        updateTopProductsList(metrics.top_products);
                    }
                }
            }
        }
        
        // Show bottom products list if available
        if (metrics.bottom_products && metrics.bottom_products.length > 0) {
            const bottomProductsContainer = document.getElementById('bottomProductsContainer');
            if (bottomProductsContainer) {
                bottomProductsContainer.classList.remove('hidden');
                // Use the dashboardBottomProductsList container
                const bottomProductsList = document.getElementById('dashboardBottomProductsList');
                if (bottomProductsList) {
                    bottomProductsList.innerHTML = '';
                    if (typeof createBottomProductsList === 'function') {
                        createBottomProductsList(metrics, metrics.bottom_products);
                    }
                }
            }
        }
        
        // Show top regions list if available
        if (metrics.top_regions && metrics.top_regions.length > 0) {
            const topRegionsContainer = document.getElementById('topRegionsContainer');
            if (topRegionsContainer) {
                topRegionsContainer.classList.remove('hidden');
                // Use the dashboardTopRegionsList container
                const topRegionsList = document.getElementById('dashboardTopRegionsList');
                if (topRegionsList) {
                    topRegionsList.innerHTML = '';
                    updateTopRegionsList(metrics.top_regions);
                }
            }
        }
        
        // Show bottom regions list if available
        if (metrics.bottom_regions && metrics.bottom_regions.length > 0) {
            const bottomRegionsContainer = document.getElementById('bottomRegionsContainer');
            if (bottomRegionsContainer) {
                bottomRegionsContainer.classList.remove('hidden');
                // Use the dashboardBottomRegionsList container
                const bottomRegionsList = document.getElementById('dashboardBottomRegionsList');
                if (bottomRegionsList) {
                    bottomRegionsList.innerHTML = '';
                    // Similar implementation to top regions
                    metrics.bottom_regions.slice(0, 5).forEach((region, index) => {
                        const item = document.createElement('div');
                        item.className = 'flex items-center justify-between';
                        
                        const percentage = metrics.bottom_regions[0].value > 0 
                            ? (region.value / metrics.bottom_regions[0].value) * 100 
                            : 0;
                        
                        item.innerHTML = `
                            <div class="flex items-center">
                                <div class="text-sm font-medium text-gray-700 mr-2">${index + 1}.</div>
                                <div class="text-sm text-gray-600 truncate max-w-[150px]">${region.name}</div>
                            </div>
                            <div class="flex items-center">
                                <div class="text-sm font-medium text-gray-700 mr-2">${formatCurrency(region.value)}</div>
                                <div class="w-20 bg-gray-200 rounded-full h-2">
                                    <div class="bg-[#7B3DF3] h-2 rounded-full" style="width: ${percentage}%"></div>
                                </div>
                            </div>
                        `;
                        
                        bottomRegionsList.appendChild(item);
                    });
                }
            }
        }
        
        // Show products with high returns/cancellations if available
        if (metrics.high_return_products && metrics.high_return_products.length > 0) {
            const highReturnsContainer = document.getElementById('highReturnsContainer');
            if (highReturnsContainer) {
                highReturnsContainer.classList.remove('hidden');
                // Use the highReturnsList container
                const highReturnsList = document.getElementById('highReturnsList');
                if (highReturnsList) {
                    highReturnsList.innerHTML = '';
                    metrics.high_return_products.slice(0, 5).forEach((product, index) => {
                        const item = document.createElement('div');
                        item.className = 'flex items-center justify-between';
                        
                        // Calculate percentage based on rate type
                        const rate = product.return_rate !== undefined ? product.return_rate : product.cancellation_rate;
                        const rateType = product.return_rate !== undefined ? 'return' : 'cancellation';
                        
                        // Determine color based on rate
                        const colorClass = rate > 15 ? 'text-red-500' : 
                                           rate > 10 ? 'text-orange-500' : 'text-yellow-500';
                        
                        item.innerHTML = `
                            <div class="flex items-center">
                                <div class="text-sm font-medium text-gray-700 mr-2">${index + 1}.</div>
                                <div class="text-sm text-gray-600 truncate max-w-[150px]">${product.name}</div>
                            </div>
                            <div class="flex items-center">
                                <div class="text-sm font-medium ${colorClass} mr-2">${rate.toFixed(1)}% ${rateType}</div>
                            </div>
                        `;
                        
                        highReturnsList.appendChild(item);
                    });
                }
            }
        }
        
        // Show the analysis content
        document.getElementById('analysisContent').classList.remove('hidden');
        document.getElementById('noAnalysisMessage').classList.add('hidden');
    }
    
    /**
     * Creates a chart showing returns vs cancellations
     */
    function createReturnsVsCancellationsChart(metrics) {
        console.log('📊 Creating returns vs cancellations chart');
        
        const container = document.getElementById('returnsVsCancellationsContainer');
        if (!container) return;
        
        // Show the container
        container.classList.remove('hidden');
        
        // Get the canvas
        const canvas = document.getElementById('returnsVsCancellationsChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }
        
        // Destroy existing chart if it exists
        if (window.returnsVsCancellationsChart) {
            window.returnsVsCancellationsChart.destroy();
        }
        
        // Create data for the chart
        const data = {
            labels: ['Returns', 'Cancellations', 'Normal Orders'],
            datasets: [{
                data: [
                    metrics.return_rate || 0,
                    metrics.cancellation_rate || 0,
                    100 - ((metrics.return_rate || 0) + (metrics.cancellation_rate || 0))
                ],
                backgroundColor: [
                    'rgba(255, 159, 64, 0.7)',  // orange for returns
                    'rgba(255, 99, 132, 0.7)',   // red for cancellations
                    'rgba(75, 192, 192, 0.7)'    // green for normal orders
                ],
                borderColor: [
                    'rgb(255, 159, 64)',
                    'rgb(255, 99, 132)',
                    'rgb(75, 192, 192)'
                ],
                borderWidth: 1
            }]
        };
        
        // Create the chart
        window.returnsVsCancellationsChart = new Chart(ctx, {
            type: 'pie',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // ... existing code ...

    // Function to display column mapping information - no longer used since we only return metrics now
    function displayColumnMappingInfo(columnMapping) {
        // This function is intentionally left empty as we're only returning metrics now
    }

    // Handle the Calculate Metrics button click
    if (calculateMetricsBtn) {
        calculateMetricsBtn.addEventListener('click', function() {
            // Get the currently selected platform type
            const platformType = document.getElementById('platformType')?.value || '';
            
            // Check if this is Meesho platform (requires special handling)
            if (platformType.toLowerCase() === 'meesho') {
                // Show Meesho-specific upload modal
                showMeeshoUploadModal();
            } else {
                // Open the standard upload modal (reuse the same modal)
                uploadModal.classList.remove('hidden');
                
                // Update the upload button to handle metrics calculation
                if (uploadButton) {
                    // Store the original click handler
                    const originalHandler = uploadButton.onclick;
                    
                    // Change the button text
                    uploadButtonText.textContent = 'Calculate Metrics';
                    
                    // Override the click handler
                    uploadButton.onclick = function(e) {
                        e.preventDefault();
                        
                        if (!fileInput.files.length) {
                            showUploadStatus('Please select a file first.', 'error');
                            return;
                        }
                        
                        // Show loading state
                        uploadButtonText.textContent = 'Calculating...';
                        uploadSpinner.classList.remove('hidden');
                        uploadButton.disabled = true;
                        
                        // Get manual column mappings if provided
                        const manualMappings = getManualColumnMappings();
                        
                        // Get the platform type
                        const platformType = document.getElementById('platformType')?.value || '';
                        
                        // Call the metrics calculation function
                        calculateSalesMetrics(
                            fileInput.files[0],
                            Object.keys(manualMappings).length > 0 ? manualMappings : null,
                            platformType
                        );
                        
                        // Reset button state after a delay
                        setTimeout(() => {
                            uploadButtonText.textContent = 'Calculate Metrics';
                            uploadSpinner.classList.add('hidden');
                            uploadButton.disabled = false;
                            
                            // Close the upload modal
                            uploadModal.classList.add('hidden');
                        }, 1000);
                    };
                    
                    // Add a cleanup function to reset the button when the modal is closed
                    const resetButton = function() {
                        uploadButtonText.textContent = 'Upload & Analyze';
                        uploadButton.onclick = originalHandler;
                    };
                    
                    // Add event listeners to reset when modal is closed
                    closeUploadModal.addEventListener('click', resetButton, { once: true });
                    uploadModalOverlay.addEventListener('click', resetButton, { once: true });
                }
            }
        });
    }

    // Function to show the Meesho-specific upload modal
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
                                <p class="font-medium">Both files are required for Meesho analysis.</p>
                                <p>The system will merge the data and analyze them together.</p>
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
            
            // Get elements from the new modal
            const closeMeeshoModal = document.getElementById('closeMeeshoModal');
            const meeshoModalOverlay = document.getElementById('meeshoModalOverlay');
            const salesFileInput = document.getElementById('salesFileInput');
            const returnsFileInput = document.getElementById('returnsFileInput');
            const selectedSalesFileName = document.getElementById('selectedSalesFileName');
            const selectedReturnsFileName = document.getElementById('selectedReturnsFileName');
            const meeshoCalculateButton = document.getElementById('meeshoCalculateButton');
            const meeshoButtonText = document.getElementById('meeshoButtonText');
            const meeshoSpinner = document.getElementById('meeshoSpinner');
            const meeshoUploadStatus = document.getElementById('meeshoUploadStatus');
            
            // Add event listeners
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
            meeshoCalculateButton.addEventListener('click', function() {
                // Validate that both files are selected
                if (!salesFileInput.files.length || !returnsFileInput.files.length) {
                    // Show status message
                    meeshoUploadStatus.textContent = 'Please upload both sales and returns files.';
                    meeshoUploadStatus.className = 'mb-2 p-2 text-xs bg-red-50 text-red-600 rounded-md';
                    meeshoUploadStatus.classList.remove('hidden');
                    return;
                }
                
                // Show loading state
                meeshoButtonText.textContent = 'Processing...';
                meeshoSpinner.classList.remove('hidden');
                meeshoCalculateButton.disabled = true;
                
                // Create array of files
                const files = [salesFileInput.files[0], returnsFileInput.files[0]];
                
                // Call the metrics calculation function with both files and Meesho platform type
                calculateSalesMetrics(files, null, 'meesho');
                
                // Reset button state and close modal after a delay
                setTimeout(() => {
                    meeshoButtonText.textContent = 'Calculate Metrics';
                    meeshoSpinner.classList.add('hidden');
                    meeshoCalculateButton.disabled = false;
                    meeshoModal.classList.add('hidden');
                }, 1000);
            });
        }
        
        // Show the Meesho modal
        meeshoModal.classList.remove('hidden');
    }

    // Function to show upload status messages
    function showMeeshoUploadStatus(message, type) {
        const statusElement = document.getElementById('meeshoUploadStatus');
        if (statusElement) {
            statusElement.textContent = message;
            
            // Set appropriate styling based on message type
            if (type === 'error') {
                statusElement.className = 'mb-2 p-2 text-xs bg-red-50 text-red-600 rounded-md';
            } else if (type === 'success') {
                statusElement.className = 'mb-2 p-2 text-xs bg-green-50 text-green-600 rounded-md';
            } else {
                statusElement.className = 'mb-2 p-2 text-xs bg-blue-50 text-blue-600 rounded-md';
            }
            
            statusElement.classList.remove('hidden');
        }
    }
});
