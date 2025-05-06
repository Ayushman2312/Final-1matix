// Trends Chart Rendering and Google AI Integration

// Create global variables to check if functions are loaded
window.trendsChartsLoaded = false;
window.isTrendsChartsLoaded = function() {
    return window.trendsChartsLoaded === true && typeof window.renderCharts === 'function';
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded - initializing trends charts');
    
    // Global variables
    let trendsData = null;
    let dataAlreadyFetched = false;
    let lastFetchedKeyword = '';
    let timeChart = null;
    let stateChart = null;
    let cityChart = null;
    let currentTimeUnit = 'month'; // Default time unit
    
    // Make key variables available globally
    window.currentTimeUnit = currentTimeUnit;
    window.trendsData = trendsData;
    window.lastFetchedKeyword = lastFetchedKeyword;
    window.timeChart = timeChart;
    
    const googleApiConfigured = window.googleApiConfigured || false;
    
    // Debug logging
    console.log('Trends charts JS loaded');
    console.log('Google API configured:', googleApiConfigured);
    
    // Enhanced safe JSON parse function
    function safeJSONParse(text) {
        if (!text) return null;
        
        try {
            // Try standard parsing first
            return JSON.parse(text);
        } catch (error) {
            console.warn('Standard JSON parse failed:', error.message);
            
            // Try to fix common JSON issues
            try {
                // Remove any leading/trailing non-JSON text
                let cleanText = text;
                
                // If the text doesn't start with { or [, find the first occurrence
                if (!cleanText.trim().startsWith('{') && !cleanText.trim().startsWith('[')) {
                    const firstBrace = cleanText.indexOf('{');
                    const firstBracket = cleanText.indexOf('[');
                    
                    if (firstBrace >= 0 && (firstBracket < 0 || firstBrace < firstBracket)) {
                        cleanText = cleanText.substring(firstBrace);
                    } else if (firstBracket >= 0) {
                        cleanText = cleanText.substring(firstBracket);
                    }
                }
                
                // If the text doesn't end with } or ], find the last occurrence
                if (!cleanText.trim().endsWith('}') && !cleanText.trim().endsWith(']')) {
                    const lastBrace = cleanText.lastIndexOf('}');
                    const lastBracket = cleanText.lastIndexOf(']');
                    
                    if (lastBrace >= 0 && (lastBracket < 0 || lastBrace > lastBracket)) {
                        cleanText = cleanText.substring(0, lastBrace + 1);
                    } else if (lastBracket >= 0) {
                        cleanText = cleanText.substring(0, lastBracket + 1);
                    }
                }
                
                // Fix common issues with quotes and commas
                cleanText = cleanText
                    // Fix missing quotes around property names
                    .replace(/([{,]\s*)([a-zA-Z0-9_]+)(\s*:)/g, '$1"$2"$3')
                    // Fix trailing commas in objects
                    .replace(/,\s*}/g, '}')
                    // Fix trailing commas in arrays
                    .replace(/,\s*\]/g, ']')
                    // Fix missing commas between array elements
                    .replace(/\}\s*\{/g, '},{')
                    // Fix missing commas between object properties
                    .replace(/"\s*\n\s*"/g, '",\n"')
                    // Fix unescaped quotes in strings
                    .replace(/"([^"]*)"([^"]*)"([^"]*)"/g, function(match, p1, p2, p3) {
                        return '"' + p1 + '\\"' + p2 + '\\"' + p3 + '"';
                    });
                
                // Try parsing the cleaned text
                return JSON.parse(cleanText);
            } catch (cleanError) {
                console.error('Failed to clean and parse JSON:', cleanError.message);
                
                // Create a minimal valid response as fallback
                return {
                    status: 'error',
                    error: 'JSON parse error: ' + error.message,
                    data: {
                        time_series: []
                    }
                };
            }
        }
    }
    
    // Make the safe JSON parse function globally available
    window.safeJSONParse = safeJSONParse;
    
    // Elements
    const keywordInput = document.getElementById('keywordInput') || document.getElementById('id_keyword');
    const analysisOption = document.getElementById('analysisOption');
    const trendsForm = document.getElementById('trendsForm');
    const inlineLoader = document.getElementById('inlineLoader');
    const resultsContainer = document.getElementById('resultsContainer');
    const headerTitle = document.getElementById('headerTitle');
    const aiInsightsButton = document.getElementById('aiInsightsButton');
    
    // Initialize chart control elements
    const viewByYearBtn = document.getElementById('viewByYear');
    const viewByQuarterBtn = document.getElementById('viewByQuarter');
    const viewByMonthBtn = document.getElementById('viewByMonth');
    const showSeasonalPatternBtn = document.getElementById('showSeasonalPattern');
    const allTimeBtn = document.getElementById('allTimeBtn');
    
    // Check if elements are found
    console.log('Elements found:', {
        keywordInput: !!keywordInput,
        analysisOption: !!analysisOption,
        trendsForm: !!trendsForm,
        inlineLoader: !!inlineLoader,
        resultsContainer: !!resultsContainer,
        headerTitle: !!headerTitle,
        aiInsightsButton: !!aiInsightsButton,
        viewByYearBtn: !!viewByYearBtn,
        viewByQuarterBtn: !!viewByQuarterBtn,
        viewByMonthBtn: !!viewByMonthBtn,
        showSeasonalPatternBtn: !!showSeasonalPatternBtn,
        allTimeBtn: !!allTimeBtn
    });
    
    // Check if auto-fetch is enabled
    const autoFetchContainer = document.querySelector('[data-auto-fetch="true"]');
    console.log('Auto-fetch container found:', !!autoFetchContainer);
    
    // Log initial keyword value if present
    if (keywordInput) {
        console.log('Initial keyword value:', keywordInput.value);
        console.log('Initial keyword data attribute:', keywordInput.dataset.initialKeyword);
    }
    
    // Setup form submission
    if (trendsForm) {
        trendsForm.addEventListener('submit', function(e) {
            const keyword = keywordInput.value.trim();
            const option = analysisOption.value;
            
            console.log('Form submitted with:', { keyword, option });
            
            if (!keyword) {
                e.preventDefault(); // Prevent submission if no keyword
                return false;
            }
            
            // Reset data fetched flag for user-initiated search
            if (keyword !== lastFetchedKeyword) {
                dataAlreadyFetched = false;
            }
            
            // Store the keyword for later use
            lastFetchedKeyword = keyword;
            
            // Always store the keyword in session storage for auto-fetch on reload
            try {
                sessionStorage.setItem('lastKeyword', keyword);
                sessionStorage.setItem('lastAnalysisOption', option);
                console.log('Stored in session storage:', { keyword, option });
            } catch (storageError) {
                console.error('Failed to store in session storage:', storageError);
            }
            
            // Check if we should handle this via AJAX or let the form submit normally
            const directSubmit = document.querySelector('input[name="direct_submit"]');
            
            if (directSubmit && directSubmit.value === 'true') {
                // Let the form submit normally - the backend will handle it
                // The showLoader function is called via onclick attribute
                console.log('Direct form submission, letting backend handle it');
                
                // Make sure the loader is properly displayed before form submits
                if (inlineLoader) {
                    inlineLoader.style.display = 'flex';
                    inlineLoader.style.opacity = '1';
                    
                    // Update the loader text with the current keyword
                    const keywordSpan = inlineLoader.querySelector('.text-sm .font-semibold');
                    if (keywordSpan) {
                        keywordSpan.textContent = keyword;
                    }
                    
                    // Add loading class to body
                    document.body.classList.add('loading');
                    
                    // Hide results container
                    if (resultsContainer) {
                        resultsContainer.style.display = 'none';
                    }
                }
                return true;
            } else {
                // Handle via AJAX
                e.preventDefault();
                
                // Show the loader immediately
                if (inlineLoader) {
                    inlineLoader.style.display = 'flex';
                    inlineLoader.style.opacity = '1';
                    
                    // Update the loader text with the current keyword
                    const keywordSpan = inlineLoader.querySelector('.text-sm .font-semibold');
                    if (keywordSpan) {
                        keywordSpan.textContent = keyword;
                    }
                    
                    // Add loading class to body
                    document.body.classList.add('loading');
                }
                
                // Hide results container
                if (resultsContainer) {
                    resultsContainer.style.display = 'none';
                }
                
                // Fetch data via AJAX
                fetchTrendsData(keyword, option);
                return false;
            }
        });
    }
    
    // Initialize auto-search on page load if we have a stored keyword
    function initializeAutoSearch() {
        try {
            const storedKeyword = sessionStorage.getItem('lastKeyword');
            const storedAnalysisOption = sessionStorage.getItem('lastAnalysisOption') || '1';
            
            console.log('Retrieved from session storage:', { 
                keyword: storedKeyword, 
                option: storedAnalysisOption 
            });
            
            if (storedKeyword && storedKeyword.trim() !== '') {
                console.log('Auto-searching for stored keyword:', storedKeyword);
                
                // Set the keyword input value
                if (keywordInput && keywordInput.value !== storedKeyword) {
                    keywordInput.value = storedKeyword;
                }
                
                // Set the analysis option if available
                if (analysisOption && storedAnalysisOption) {
                    analysisOption.value = storedAnalysisOption;
                }
                
                // Only auto-fetch if we're not in the middle of another operation
                if (!dataAlreadyFetched && !document.body.classList.contains('loading')) {
                    // Short delay to ensure everything is ready
                    setTimeout(() => {
                        fetchTrendsData(storedKeyword, storedAnalysisOption);
                    }, 300);
                }
            }
        } catch (error) {
            console.error('Error in auto-search initialization:', error);
        }
    }
    
    // Call initialization when DOM is loaded
    if (document.readyState === 'loading') {
        // If still loading, wait for DOMContentLoaded
        document.addEventListener('DOMContentLoaded', initializeAutoSearch);
    } else {
        // If already loaded, run immediately
        initializeAutoSearch();
    }
    
    // Setup Quick Fetch button
    const autoFetchBtn = document.getElementById('autoFetchBtn');
    if (autoFetchBtn) {
        autoFetchBtn.addEventListener('click', function() {
            const keyword = keywordInput.value.trim();
            const option = analysisOption.value;
            
            console.log('Quick Fetch clicked with:', { keyword, option });
            
            if (keyword) {
                // Reset data fetched flag for user-initiated search
                if (keyword !== lastFetchedKeyword) {
                    dataAlreadyFetched = false;
                }
                
                // Show the loader immediately
                if (inlineLoader) {
                    inlineLoader.style.display = 'flex';
                    inlineLoader.style.opacity = '0';
                    // Trigger a reflow to ensure the transition works
                    void inlineLoader.offsetWidth;
                    inlineLoader.style.opacity = '1';
                    
                    // Update the loader text with the current keyword
                    const keywordSpan = inlineLoader.querySelector('.text-sm .font-semibold');
                    if (keywordSpan) {
                        keywordSpan.textContent = keyword;
                    }
                    
                    // Add loading class to body
                    document.body.classList.add('loading');
                }
                
                // Hide results container
                if (resultsContainer) {
                    resultsContainer.style.display = 'none';
                }
                
                lastFetchedKeyword = keyword;
                
                // Store the keyword in session storage for auto-fetch on reload
                try {
                    sessionStorage.setItem('lastKeyword', keyword);
                    sessionStorage.setItem('lastAnalysisOption', option);
                    console.log('Stored in session storage from Quick Fetch:', { keyword, option });
                } catch (storageError) {
                    console.error('Failed to store in session storage:', storageError);
                }
                
                // Update header title
                if (headerTitle) {
                    headerTitle.textContent = `${keyword} in India`;
                }
                
                // Update AI insights button href
                if (aiInsightsButton) {
                    aiInsightsButton.href = `/trends/insights/${encodeURIComponent(keyword)}/?analysis_option=${option}`;
                }
                
                // Add a small delay to ensure the loader is visible
                setTimeout(() => {
                    fetchTrendsData(keyword, option);
                }, 100);
            }
        });
    }
    
    // Function to fetch trends data
    function fetchTrendsData(keyword, analysisOption) {
        if (!keyword) {
            console.error('No keyword provided');
            return;
        }
        
        console.group('Fetching trends data');
        console.log('Keyword:', keyword);
        console.log('Analysis option:', analysisOption);
        
        // Store the current keyword and option in session storage
        try {
            sessionStorage.setItem('lastKeyword', keyword);
            sessionStorage.setItem('lastAnalysisOption', analysisOption);
            console.log('Updated session storage with current search:', { keyword, analysisOption });
        } catch (storageError) {
            console.error('Failed to update session storage:', storageError);
        }
        
        // Prevent multiple fetches for the same keyword
        if (dataAlreadyFetched && keyword === lastFetchedKeyword) {
            console.log('Data already fetched for this keyword, reusing existing data');
            
            // Hide loader
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            
            // Show results
            if (resultsContainer) {
                resultsContainer.style.display = 'block';
            }
            
            // Render charts with existing data
            renderCharts();
            
            console.groupEnd();
            return;
        }
        
        // Reset the dataAlreadyFetched flag when fetching a new keyword
        if (keyword !== lastFetchedKeyword) {
            dataAlreadyFetched = false;
        }
        
        // Set a timeout to abort fetch if it takes too long
        let fetchTimeout = setTimeout(() => {
            console.error('Fetch operation timeout after 60 seconds');
            // Hide loader
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            showError('Request timed out. Please try again later.');
        }, 60000); // 60 second timeout
        
        // Create loading progress steps
        const steps = [
            'Connecting to Google Trends',
            'Fetching search interest data',
            'Processing time series data',
            'Analyzing regional patterns',
            'Preparing visualization'
        ];
        
        // Initialize step counter
        let currentStep = 0;
        
        // Initialize step interval
        let stepInterval = null;
        
        // Function to advance to the next step
        function advanceLoaderStep() {
            if (currentStep < steps.length) {
                if (inlineLoader) {
                    const stepText = inlineLoader.querySelector('.step-text');
                    if (stepText) {
                        stepText.textContent = steps[currentStep];
                    }
                }
                currentStep++;
            } else {
                clearInterval(stepInterval);
            }
        }
        
        // Start with first step
        advanceLoaderStep();
        
        // Set up interval to advance steps
        stepInterval = setInterval(() => {
            // Only advance if we haven't reached the end
            if (currentStep < steps.length) {
                advanceLoaderStep();
            } else {
                // If we've shown all steps, start showing wait messages
                if (inlineLoader) {
                    const stepText = inlineLoader.querySelector('.step-text');
                    if (stepText) {
                        stepText.textContent = "Still working... Please wait.";
                        
                        // After 5 more seconds, show a different message
                        setTimeout(() => {
                            if (stepText && inlineLoader.style.display !== 'none') {
                                stepText.textContent = "This is taking longer than expected. Still processing...";
                            }
                        }, 5000);
                    }
                }
            }
        }, 2000);
        
        lastFetchedKeyword = keyword;
        
        console.log('Fetching trends data for:', keyword, 'with option:', analysisOption);
        
        // Ensure the loader is visible and properly styled
        if (inlineLoader) {
            // Make sure the loader is visible
            inlineLoader.style.display = 'flex';
            
            // If the loader is already visible but transparent, make it visible with a transition
            if (inlineLoader.style.opacity !== '1') {
                inlineLoader.style.opacity = '0';
                // Trigger a reflow to ensure the transition works
                void inlineLoader.offsetWidth;
                inlineLoader.style.opacity = '1';
            }
            
            // Update the loader text with the current keyword
            const keywordSpan = inlineLoader.querySelector('.text-sm .font-semibold');
            if (keywordSpan) {
                keywordSpan.textContent = keyword;
            }
            
            // Add loading class to body to prevent scrolling
            document.body.classList.add('loading');
        }
        
        // Make sure results are hidden while loading
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
        
        // Hide any existing error message
        if (typeof hideError === 'function') {
            hideError();
        }
        
        // Update page title with the keyword
        if (headerTitle) {
            headerTitle.textContent = `${keyword} in India`;
        }
        
        // Reset searchCancelled flag
        window.searchCancelled = false;
        
        // Store the keyword for later use
        lastFetchedKeyword = keyword;
        
        // Build API URL
        const apiUrl = `/trends/api/data/?keyword=${encodeURIComponent(keyword)}&analysis_option=${analysisOption}&auto_triggered=true`;
        console.log('API URL:', apiUrl);
        
        // Add timestamp to prevent caching
        const timestampedUrl = `${apiUrl}&_t=${Date.now()}`;
        
        // Abort controller for fetch - allow cancellation
        const controller = new AbortController();
        const signal = controller.signal;
        
        // Fetch data from server with timeout
        fetch(timestampedUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            signal: signal,
            cache: 'no-store' // Ensure we don't get a cached response
        })
        .then(response => {
            // Clear the timeout since we got a response
            clearTimeout(fetchTimeout);
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            // Check content type
            const contentType = response.headers.get('content-type');
            if (contentType && !contentType.includes('application/json')) {
                console.warn(`Expected JSON response but got ${contentType}`);
            }
            
            // Don't use response.clone(), just return the text directly
            return response.text();
        })
        .then(rawData => {
            console.log('Raw data received, length:', rawData.length);
            
            // Check for obvious server error messages in the raw response
            if (rawData.includes('Internal Server Error') || 
                rawData.includes('<!DOCTYPE html>') ||
                rawData.startsWith('<html>')) {
                console.error('Received HTML error page instead of JSON');
                throw new Error('Server returned an error page instead of data. Please try again later.');
            }
            
            if (!rawData || rawData.trim() === '') {
                console.error('Received empty response');
                throw new Error('Server returned an empty response. Please try again later.');
            }
            
            // Try to parse the JSON using our enhanced fixBrokenJSON method
            let parsedData = null;
            let parseError = null;
            
            try {
                // First try standard parsing
                parsedData = JSON.parse(rawData);
                console.log('Standard JSON parsing succeeded');
            } catch (error) {
                console.warn('Standard JSON parsing failed, attempting repair:', error.message);
                parseError = error;
                
                // Use our enhanced JSON repair function
                try {
                    // fixBrokenJSON now returns the actual object, not a string
                    parsedData = fixBrokenJSON(rawData);
                    
                    if (parsedData) {
                        console.log('JSON repair succeeded');
                    } else {
                        throw new Error('JSON repair failed to produce valid data');
                    }
                } catch (repairError) {
                    console.error('JSON repair attempt failed:', repairError.message);
                    
                    // Create a minimal valid response as a last resort
                    console.log('Creating minimal fallback response');
                    parsedData = {
                        status: 'success',
                        error: null,
                        metadata: {
                            keywords: [lastFetchedKeyword],
                            timestamp: new Date().toISOString()
                        },
                        data: {
                            time_series: [],
                            time_trends: []
                        }
                    };
                }
            }
            
            // Validate that the parsed data has the required structure
            if (!parsedData || !parsedData.data) {
                console.error('Invalid data structure after parsing');
                
                // Create a valid structure
                parsedData = {
                    status: 'success',
                    metadata: {
                        keywords: [lastFetchedKeyword],
                        timestamp: new Date().toISOString()
                    },
                    data: {
                        time_series: [],
                        time_trends: []
                    },
                    error: 'Data structure was invalid'
                };
            }
            
            // Check for error status in the parsed data
            if (parsedData.status === 'error' || parsedData.error) {
                console.warn('Error status in parsed data:', parsedData.error);
                // Don't throw here, instead, we'll handle it in the next step
            }
            
            return parsedData;
        })
        .then(data => {
            console.log('Data parsed successfully, processing...');
            
            // Clear interval if still running
            clearInterval(stepInterval);
            
            // Check if search has been cancelled
            if (window.searchCancelled) {
                console.log('Search was cancelled, aborting data processing');
                return;
            }
            
            // Check for error status in the data
            if (data.status === 'error' || data.error) {
                const errorMessage = data.error || 'An error occurred while processing trends data';
                console.warn('Error status in response data:', errorMessage);
                
                // If there's no time_series data at all, show the error
                if (!data.data || !data.data.time_series || data.data.time_series.length === 0) {
                    console.error('No time series data available');
                    
                    // Hide loader
                    if (inlineLoader) {
                        inlineLoader.style.opacity = '0';
                        setTimeout(() => {
                            inlineLoader.style.display = 'none';
                            document.body.classList.remove('loading');
                        }, 300);
                    }
                    
                    // Show error message
                    if (typeof showError === 'function') {
                        showError(errorMessage);
                    } else {
                        alert(errorMessage);
                    }
                    
                    // Reset dataAlreadyFetched flag to allow retry
                    dataAlreadyFetched = false;
                    
                    return; // Stop processing
                } else {
                    // If we have time_series data, log the error but continue processing
                    console.log('Error in data but time_series available, continuing with processing');
                }
            }
            
            // Process and store the data
            trendsData = data;
            
            // Now that we have valid data, set the flag
            dataAlreadyFetched = true;
            
            // Debug data structure
            debugValue(trendsData, 'trendsData');
            if (trendsData && trendsData.data) {
                debugValue(trendsData.data.time_trends || trendsData.data.time_series || [], 'Time series data');
            }
            
            console.log('Data stored, keyword:', lastFetchedKeyword);
            
            // Ensure chart container exists
            const timeSeriesChartContainer = document.getElementById('timeSeriesChartContainer');
            if (!timeSeriesChartContainer) {
                console.error('Chart container not found in DOM');
                
                // Try to create the container if missing
                const resultsContainer = document.getElementById('resultsContainer');
                if (resultsContainer) {
                    console.log('Creating missing chart container');
                    const newContainer = document.createElement('div');
                    newContainer.id = 'timeSeriesChartContainer';
                    newContainer.className = 'w-full h-96 mb-8';
                    newContainer.innerHTML = '<canvas id="timeSeriesChart"></canvas>';
                    resultsContainer.prepend(newContainer);
                } else {
                    throw new Error('Chart container not found and could not create one');
                }
            }
            
            // Hide loader with animation
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            
            // Show results container
            if (resultsContainer) {
                resultsContainer.style.display = 'block';
            }
            
            // Render all charts
            console.log('Rendering charts...');
            renderCharts();
        })
        .catch(error => {
            // Clear the timeout since we've handled the error
            clearTimeout(fetchTimeout);
            
            console.error('Error fetching or processing trends data:', error);
            
            // Clear interval if still running
            clearInterval(stepInterval);
            
            // Hide loader
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            
            // Reset dataAlreadyFetched flag to allow retry
            dataAlreadyFetched = false;
            
            // Show user-friendly error message
            let errorMessage = error.message || 'Error loading data';
            let isNetworkError = false;
            
            // Make common error messages more user-friendly
            if (errorMessage.includes('HTTP error! Status: 429')) {
                errorMessage = 'Too many requests. Please wait a moment and try again.';
            } else if (errorMessage.includes('HTTP error! Status: 500')) {
                errorMessage = 'Server error. Please try again with a different keyword or later.';
            } else if (errorMessage.includes('Failed to fetch') || 
                      errorMessage.includes('NetworkError') || 
                      errorMessage.includes('network error') ||
                      error.name === 'TypeError') {
                errorMessage = 'Network connection error. Please check your internet connection and try again.';
                isNetworkError = true;
            } else if (errorMessage.includes('JSON')) {
                errorMessage = 'Error processing data. Please try again with a different keyword.';
            } else if (errorMessage.includes('aborted')) {
                errorMessage = 'Request was cancelled. Please try again.';
            }
            
            // Show error message
            if (typeof showError === 'function') {
                showError(errorMessage);
            } else {
                alert(errorMessage);
            }
            
            // For network errors, attempt to automatically reconnect after a delay
            if (isNetworkError && !window.searchCancelled) {
                console.log('Network error detected, scheduling retry attempt');
                
                // Add reconnection UI feedback
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    // Show reconnection message
                    if (typeof showError === 'function') {
                        showError('Attempting to reconnect... Please wait.');
                    }
                    
                    // Try to fetch again after a short delay
                    setTimeout(() => {
                        if (!window.searchCancelled) {
                            console.log('Retrying fetch operation');
                            fetchTrendsData(lastFetchedKeyword, analysisOption);
                        }
                    }, 3000);
                }, 2000);
            }
        })
        .finally(() => {
            // Always clean up
            clearTimeout(fetchTimeout);
            clearInterval(stepInterval);
            
            // Remove loading class
            document.body.classList.remove('loading');
            console.groupEnd();
        });
        
        // Add a cancellation method
        window.cancelTrendsFetch = function() {
            console.log('Cancelling trends fetch');
            window.searchCancelled = true;
            controller.abort();
            clearTimeout(fetchTimeout);
            clearInterval(stepInterval);
            
            // Hide loader
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            
            // Reset flag to allow new fetch attempts
            dataAlreadyFetched = false;
        };
    }
    
    // Function to generate insights from the time series data
    function generateInsights() {
        console.log('Generating insights from time series data');
        
        // Create or get the insights container
        let insightsContainer = document.getElementById('insightsContent');
        if (!insightsContainer) {
            // If insights section doesn't exist, create it
            const timeChartContainer = document.getElementById('timeChartContainer');
            if (!timeChartContainer) {
                return; // Exit if no chart container
            }
            
            const insightsSection = document.createElement('div');
            insightsSection.className = 'insights mt-6 bg-indigo-50 p-5 rounded-xl';
            insightsSection.innerHTML = `
                <h3 class="font-bold text-indigo-800 text-lg mb-2">Key Insights</h3>
                <div id="insightsContent">Loading analysis...</div>
            `;
            
            timeChartContainer.appendChild(insightsSection);
            insightsContainer = document.getElementById('insightsContent');
        }
        
        // Get time data
        let timeData = trendsData.data.time_trends || trendsData.data.time_series || [];
        if (!timeData || timeData.length === 0) {
            insightsContainer.innerHTML = 'No time data available for analysis.';
            return;
        }
        
        try {
            // Process data to ensure consistent format
            const processedData = [];
            
            timeData.forEach(item => {
                if (item.is_partial === true) return;
                
                // Extract date and value
                let date;
                if (item.date) {
                    date = new Date(item.date);
                } else if (item.index) {
                    date = new Date(item.index);
                } else {
                    return; // Skip if no date
                }
                
                if (isNaN(date.getTime())) {
                    return; // Skip invalid dates
                }
                
                // Extract value
                let value;
                if (typeof item.value === 'number') {
                    value = item.value;
                } else if (lastFetchedKeyword && typeof item[lastFetchedKeyword] === 'number') {
                    value = item[lastFetchedKeyword];
                } else {
                    // Look for any numeric value
                    for (const key in item) {
                        if (typeof item[key] === 'number' && 
                            key !== 'is_partial' && 
                            key !== 'date' && 
                            key !== 'index') {
                            value = item[key];
                            break;
                        }
                    }
                }
                
                if (value !== undefined && !isNaN(value)) {
                    processedData.push({
                        date: date,
                        value: value
                    });
                }
            });
            
            // Sort data by date
            processedData.sort((a, b) => a.date - b.date);
            
            if (processedData.length === 0) {
                insightsContainer.innerHTML = 'No valid data points for analysis.';
                return;
            }
            
            // Find maximum and minimum values
            const maxItem = processedData.reduce((max, item) => 
                item.value > max.value ? item : max, processedData[0]);
            
            const minItem = processedData.reduce((min, item) => 
                item.value < min.value ? item : min, processedData[0]);
            
            // Calculate average
            const sum = processedData.reduce((acc, item) => acc + item.value, 0);
            const average = sum / processedData.length;
            
            // Calculate trend (using last 10% of data vs first 10%)
            const segment = Math.max(1, Math.floor(processedData.length * 0.1));
            const firstSegment = processedData.slice(0, segment);
            const lastSegment = processedData.slice(-segment);
            
            const firstAvg = firstSegment.reduce((acc, item) => acc + item.value, 0) / firstSegment.length;
            const lastAvg = lastSegment.reduce((acc, item) => acc + item.value, 0) / lastSegment.length;
            
            const trendPercent = ((lastAvg - firstAvg) / firstAvg * 100).toFixed(1);
            const trendDirection = lastAvg > firstAvg ? 'increasing' : lastAvg < firstAvg ? 'decreasing' : 'stable';
            
            // Year-over-year comparison (if we have at least 1 year of data)
            let yoyAnalysis = '';
            if (processedData.length >= 52) {
                const currentValue = processedData[processedData.length - 1].value;
                const yearAgoIndex = Math.max(0, processedData.length - 53); // Approximately 1 year ago
                const yearAgoValue = processedData[yearAgoIndex].value;
                
                const yoyPercent = ((currentValue - yearAgoValue) / yearAgoValue * 100).toFixed(1);
                const yoyDirection = currentValue > yearAgoValue ? 'higher' : 'lower';
                
                yoyAnalysis = `
                    <p><strong>Year-over-Year Change:</strong> ${yoyPercent}% ${yoyDirection} than the same time last year.</p>
                `;
            }
            
            // Detect seasonality
            const monthlyAverages = Array(12).fill(0).map(() => []);
            
            processedData.forEach(item => {
                const month = item.date.getMonth();
                monthlyAverages[month].push(item.value);
            });
            
            const monthlyMeans = monthlyAverages.map(monthValues => {
                if (monthValues.length === 0) return 0;
                return monthValues.reduce((sum, val) => sum + val, 0) / monthValues.length;
            });
            
            const highestMonth = monthlyMeans.indexOf(Math.max(...monthlyMeans));
            const lowestMonth = monthlyMeans.indexOf(Math.min(...monthlyMeans));
            
            const monthNames = [
                'January', 'February', 'March', 'April', 'May', 'June', 
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            
            // Check if recent months show a change in trend
            const recentTrend = [];
            if (processedData.length >= 6) {
                const recent6Months = processedData.slice(-6);
                // Calculate simple moving average for detection
                for (let i = 2; i < recent6Months.length; i++) {
                    const prevAvg = (recent6Months[i-2].value + recent6Months[i-1].value) / 2;
                    const currentAvg = (recent6Months[i-1].value + recent6Months[i].value) / 2;
                    if (currentAvg > prevAvg * 1.1) {
                        recentTrend.push('increasing');
                    } else if (currentAvg < prevAvg * 0.9) {
                        recentTrend.push('decreasing');
                    } else {
                        recentTrend.push('stable');
                    }
                }
            }
            
            // Determine if there's a consistent recent trend
            let recentTrendText = '';
            if (recentTrend.length >= 3) {
                const increasing = recentTrend.filter(t => t === 'increasing').length;
                const decreasing = recentTrend.filter(t => t === 'decreasing').length;
                
                if (increasing >= recentTrend.length * 0.7) {
                    recentTrendText = '<p><strong>Recent Trend:</strong> Strong upward trend in the last few months.</p>';
                } else if (decreasing >= recentTrend.length * 0.7) {
                    recentTrendText = '<p><strong>Recent Trend:</strong> Strong downward trend in the last few months.</p>';
                }
            }
            
            // Traditional insights HTML
            const traditionalInsightsHTML = `
                <p><strong>Peak Interest:</strong> ${maxItem.value.toFixed(1)} on ${maxItem.date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                <p><strong>Lowest Interest:</strong> ${minItem.value.toFixed(1)} on ${minItem.date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                <p><strong>Overall Trend:</strong> Search interest is ${trendDirection} by ${trendPercent}% over the analyzed period.</p>
                ${yoyAnalysis}
                ${recentTrendText}
                <p><strong>Seasonal Pattern:</strong> Interest tends to be highest in ${monthNames[highestMonth]} and lowest in ${monthNames[lowestMonth]}.</p>
            `;
            
            // Update insights container with loading state
            insightsContainer.innerHTML = `
                <div class="traditional-insights mb-4">
                    ${traditionalInsightsHTML}
                </div>
                <div class="ai-insights-loading">
                    <div class="flex items-center justify-center">
                        <svg class="animate-spin h-5 w-5 text-indigo-700 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span class="text-indigo-700 font-medium">Generating AI-powered insights...</span>
                    </div>
                </div>
            `;
            
            // Prepare data for the AI API
            const trendData = {
                keyword: lastFetchedKeyword,
                timeframe: "last 5 years",
                region: "India",
                trendStats: {
                    peakInterest: {
                        value: maxItem.value,
                        date: maxItem.date.toISOString().split('T')[0]
                    },
                    lowestInterest: {
                        value: minItem.value,
                        date: minItem.date.toISOString().split('T')[0]
                    },
                    overallTrend: {
                        direction: trendDirection,
                        percentage: trendPercent
                    },
                    seasonality: {
                        highestMonth: monthNames[highestMonth],
                        lowestMonth: monthNames[lowestMonth]
                    },
                    recentTrend: recentTrend.length >= 3 ? 
                        (increasing >= recentTrend.length * 0.7 ? "strong upward" : 
                        decreasing >= recentTrend.length * 0.7 ? "strong downward" : "stable") : "mixed"
                },
                dataPoints: processedData.map(item => ({
                    date: item.date.toISOString().split('T')[0],
                    value: item.value
                }))
            };
            
            // Call Google Generative AI to get enhanced insights
            fetchAIInsights(trendData, insightsContainer);
            
        } catch (error) {
            console.error('Error generating insights:', error);
            insightsContainer.innerHTML = 'Error generating insights: ' + error.message;
        }
    }
    
    // Function to fetch AI-powered insights using Google Generative AI
    function fetchAIInsights(trendData, insightsContainer) {
        // API endpoint for AI insights
        const aiEndpoint = '/trends/api/ai-insights/';
        
        console.log('Fetching AI insights for:', trendData.keyword);
        
        // Prepare the request
        fetch(aiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                keyword: trendData.keyword,
                trend_data: trendData
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('AI insights received:', data);
            
            // Check if we have valid insights
            if (!data || !data.insights) {
                throw new Error('Invalid response from AI insights API');
            }
            
            // Format the AI insights with sections
            const aiInsightsHTML = `
                <div class="border-t border-indigo-200 my-4 pt-4">
                    <h4 class="text-lg font-semibold text-indigo-800 mb-3">AI-Powered Insights</h4>
                    
                    <div class="mb-4">
                        <h5 class="font-medium text-indigo-700 mb-2">Trend Analysis</h5>
                        <p class="text-gray-700">${data.insights.trend_analysis || 'No trend analysis available.'}</p>
                    </div>
                    
                    <div class="mb-4">
                        <h5 class="font-medium text-indigo-700 mb-2">Future Scope & Potential</h5>
                        <p class="text-gray-700">${data.insights.future_scope || 'No future scope analysis available.'}</p>
                    </div>
                    
                    <div class="mb-4">
                        <h5 class="font-medium text-indigo-700 mb-2">Advertising Recommendations</h5>
                        <p class="text-gray-700">${data.insights.ad_recommendations || 'No advertising recommendations available.'}</p>
                    </div>
                    
                    <div class="mb-2">
                        <h5 class="font-medium text-indigo-700 mb-2">Keyword Usage Tips</h5>
                        <p class="text-gray-700">${data.insights.keyword_tips || 'No keyword usage tips available.'}</p>
                    </div>
                </div>
            `;
            
            // Find the AI insights loading container and replace it
            const loadingContainer = insightsContainer.querySelector('.ai-insights-loading');
            if (loadingContainer) {
                const aiInsightsElement = document.createElement('div');
                aiInsightsElement.className = 'ai-insights';
                aiInsightsElement.innerHTML = aiInsightsHTML;
                loadingContainer.parentNode.replaceChild(aiInsightsElement, loadingContainer);
            } else {
                // If no loading container found, append to the end
                insightsContainer.innerHTML += aiInsightsHTML;
            }
        })
        .catch(error => {
            console.error('Error fetching AI insights:', error);
            
            // Find the AI insights loading container and replace with error message
            const loadingContainer = insightsContainer.querySelector('.ai-insights-loading');
            if (loadingContainer) {
                loadingContainer.innerHTML = `
                    <div class="text-red-600 p-3 bg-red-50 rounded-md">
                        <p><strong>Error loading AI insights:</strong> ${error.message}</p>
                        <p class="text-sm mt-2">Traditional insights are still available above.</p>
                    </div>
                `;
            }
        });
    }
    
    // Make functions globally available
    window.renderCharts = renderCharts;
    window.fetchTrendsData = fetchTrendsData;
    window.updateTimeUnit = updateTimeUnit;
    window.showSeasonalPattern = showSeasonalPattern;
    
    console.log('Exported functions to global scope');
    
    // Set flag to indicate the script is loaded and ready
    window.trendsChartsLoaded = true;
    
    // If we have already fetched data, try to render it
    if (window.trendsData) {
        console.log('Found existing trends data, attempting to render charts');
        trendsData = window.trendsData;
        renderCharts();
    }
}); 

// Helper function to show error
function showError(message) {
    console.error('Error:', message);
    
    // Try to create an error display element
    const errorContainer = document.createElement('div');
    errorContainer.className = 'bg-red-50 border-l-4 border-red-500 p-4 rounded-md shadow-sm mb-6';
    errorContainer.id = 'error-message-container';
    
    errorContainer.innerHTML = `
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
            </div>
            <div class="ml-3">
                <p class="text-sm text-red-700">${message}</p>
            </div>
        </div>
    `;
    
    // Remove any existing error messages first
    hideError();
    
    // Find a suitable container to add the error to
    const container = document.getElementById('timeSeriesChartContainer') || 
                    document.getElementById('chartControlsSection') || 
                    document.getElementById('resultsContainer');
    
    if (container) {
        // Insert at the beginning of the container
        if (container.firstChild) {
            container.insertBefore(errorContainer, container.firstChild);
        } else {
            container.appendChild(errorContainer);
        }
    }
}

// Function to hide error messages
function hideError() {
    // Remove any existing error messages
    const existingErrors = document.querySelectorAll('#error-message-container');
    existingErrors.forEach(error => {
        error.remove();
    });
}

// Make hideError globally available
window.hideError = hideError;

// Function to update seasonal chart legend
function updateSeasonalLegend() {
    const chartContainer = document.getElementById('timeChartContainer');
    if (!chartContainer) return;
    
    // Remove existing legend if it exists
    const existingLegend = chartContainer.querySelector('.legend');
    if (existingLegend) {
        existingLegend.remove();
    }
    
    // Get the years displayed in the chart (last 3 years)
    const years = [];
    if (trendsData && trendsData.data && (trendsData.data.time_trends || trendsData.data.time_series)) {
        const timeData = trendsData.data.time_trends || trendsData.data.time_series || [];
        const allYears = new Set();
        
        timeData.forEach(item => {
            let date;
            if (item.date) {
                date = new Date(item.date);
            } else if (item.index) {
                date = new Date(item.index);
            }
            
            if (date && !isNaN(date.getTime())) {
                allYears.add(date.getFullYear());
            }
        });
        
        // Get last 3 years
        years.push(...Array.from(allYears).sort().slice(-3));
    }
    
    // Create HTML for the legend - including both core lines and years
    let legendHTML = `
    <div class="legend flex justify-center gap-6 mt-4 flex-wrap">
        <div class="legend-item flex items-center">
            <div class="legend-color w-3 h-3 mr-2 rounded-sm" style="background: rgba(52, 152, 219, 0.7);"></div>
            <span class="text-sm text-gray-700">Average Seasonal Pattern</span>
        </div>
        <div class="legend-item flex items-center">
            <div class="legend-color w-3 h-3 mr-2 rounded-sm" style="background: rgba(231, 76, 60, 0.7);"></div>
            <span class="text-sm text-gray-700">Trend Line</span>
        </div>
        <div class="legend-item flex items-center">
            <div class="legend-color w-3 h-3 mr-2 rounded-sm" style="background: rgba(46, 204, 113, 0.7);"></div>
            <span class="text-sm text-gray-700">Moving Average</span>
        </div>`;
        
    // Add year-specific colors if we have years
    years.forEach(year => {
        const color = getYearColor(year, years);
        legendHTML += `
        <div class="legend-item flex items-center">
            <div class="legend-color w-3 h-3 mr-2 rounded-sm" style="background: ${color};"></div>
            <span class="text-sm text-gray-700">${year}</span>
        </div>`;
    });
    
    legendHTML += `</div>`;
    
    // Create and append the legend element
    const legendElem = document.createElement('div');
    legendElem.innerHTML = legendHTML;
    chartContainer.appendChild(legendElem.firstElementChild);
}

// Update showSeasonalPattern function to use updateSeasonalLegend
function showSeasonalPattern() {
    // ... existing code ...
    
    // Update active filter UI
    updateActiveFilter('seasonal');
    
    // Update chart legend for seasonal view
    updateSeasonalLegend();
    
    console.log('Seasonal pattern chart rendered successfully');
    
    // ... existing code ...
} 

// Add this debugging function at the top of the file, after the initial DOM load event listener
// Debug helper function to inspect values and log results
function debugValue(value, label) {
    if (value === undefined) {
        console.log(`DEBUG: ${label} is undefined`);
        return false;
    } else if (value === null) {
        console.log(`DEBUG: ${label} is null`);
        return false;
    } else if (Array.isArray(value)) {
        console.log(`DEBUG: ${label} is array with ${value.length} items`, value.length > 0 ? value.slice(0, 3) : []);
        return value.length > 0;
    } else if (typeof value === 'object') {
        console.log(`DEBUG: ${label} is object`, value);
        return Object.keys(value).length > 0;
    } else {
        console.log(`DEBUG: ${label} is ${typeof value}:`, value);
        return true;
    }
} 

// Ensure the data can be safely parsed as JSON
function ensureValidJSON(responseText) {
    console.log("Checking response validity...");
    
    // Check for empty response
    if (!responseText || responseText.trim() === '') {
        console.error("Empty response received");
        return JSON.stringify({
            "error": "Empty response from server", 
            "time_series": []
        });
    }
    
    // Check for error responses that are not valid JSON
    if (responseText.includes("Internal Server Error") || 
        responseText.includes("<!DOCTYPE html>") ||
        responseText.includes("<html>")) {
        console.error("Server error response detected");
        return JSON.stringify({
            "error": "Server error response", 
            "time_series": []
        });
    }
    
    // Quick fix for option field if it's clearly a numeric value without quotes
    if (responseText.includes('"option":')) {
        // Look for unquoted numeric values, common patterns include:
        // 1. "option":1, - numeric with comma
        // 2. "option":1} - numeric with closing brace
        // 3. "option":1", - numeric with extra quote 
        
        // Apply a quick fix to quote the value
        responseText = responseText
            // Fix unquoted numeric values
            .replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2')  
            // Fix extra quote after the number
            .replace(/"option"\s*:\s*(\d+)"\s*,/g, '"option":"$1",')
            // Fix misaligned quotes
            .replace(/"option"\s*:\s*"(\d+)([,}])/g, '"option":"$1"$2');
    }
    
    // Try to parse the original response first
    try {
        const data = JSON.parse(responseText);
        return responseText;
    } catch (error) {
        console.warn("JSON parse error:", error.message);
        
        // Try to fix the JSON string
        try {
            const fixed = fixBrokenJSON(responseText);
            // Validate the fixed JSON
            JSON.parse(fixed);
            console.log("JSON repair successful");
            return fixed;
        } catch (repairError) {
            console.error("JSON repair failed:", repairError.message);
            
            // Last resort - try JSONCrush if available
            if (typeof JSONCrush !== 'undefined') {
                try {
                    // Attempt to recover with JSONCrush
                    const decoded = JSONCrush.uncrush(responseText);
                    JSON.parse(decoded); // Validate
                    console.log("JSONCrush recovery successful");
                    return decoded;
                } catch (crushError) {
                    console.error("JSONCrush failed:", crushError.message);
                }
            }
            
            // Return a minimal valid response as a last resort
            return JSON.stringify({
                "error": "JSON parsing error: " + error.message, 
                "time_series": []
            });
        }
    }
}

// Add this function to your code or replace the existing one
function fixBrokenJSON(text) {
    console.log('Attempting to fix JSON data of length:', text.length);
    
    // Guard against empty or non-string inputs
    if (!text || typeof text !== 'string') {
        console.error('Invalid input to fixBrokenJSON:', text);
        return null;
    }
    
    try {
        // First try standard JSON parse - maybe it's actually valid
        return JSON.parse(text);
    } catch (initialError) {
        console.log('Initial JSON parse failed, attempting repair:', initialError.message);
        
        try {
            // Log some debug information about the error
            const errorMatch = initialError.message.match(/position (\d+)/);
            if (errorMatch && errorMatch[1]) {
                const errorPos = parseInt(errorMatch[1]);
                const contextStart = Math.max(0, errorPos - 30);
                const contextEnd = Math.min(text.length, errorPos + 30);
                console.log(`Error context at position ${errorPos}: "${text.substring(contextStart, errorPos)}[ERROR HERE]${text.substring(errorPos, contextEnd)}"`);
            }
            
            // Step 1: Fix common JSON syntax issues
            let fixedText = text
                // Remove control characters
                .replace(/[\x00-\x1F\x7F-\x9F]/g, '')
                // Fix unescaped quotes in strings - careful with this
                .replace(/([^\\])"([^"]*[^\\])"/g, '$1\\"$2\\"')
                // Fix missing quotes around property names
                .replace(/([{,]\s*)([a-zA-Z0-9_$]+)(\s*:)/g, '$1"$2"$3')
                // Fix trailing commas in objects
                .replace(/,(\s*})/g, '$1')
                // Fix trailing commas in arrays
                .replace(/,(\s*\])/g, '$1');
            
            // Step 2: Try to parse the fixed text
            try {
                return JSON.parse(fixedText);
            } catch (error) {
                console.log('Basic fixing failed, attempting more advanced repairs:', error.message);
                
                // Step 3: More aggressive fixing
                // Try to extract just the JSON object portion
                const objectStartIndex = text.indexOf('{');
                const objectEndIndex = text.lastIndexOf('}');
                
                if (objectStartIndex !== -1 && objectEndIndex !== -1 && objectEndIndex > objectStartIndex) {
                    const extractedObject = text.substring(objectStartIndex, objectEndIndex + 1);
                    try {
                        console.log('Attempting to parse extracted JSON object');
                        return JSON.parse(extractedObject);
                    } catch (extractError) {
                        console.log('Extracted object parsing failed:', extractError.message);
                    }
                }
                
                // Step 4: If we have a specific error about option field, fix that
                if (error.message.includes('option') || text.includes('"option":1') || text.includes('"option": 1')) {
                    console.log('Detected potential option field issue, applying specific fix');
                    fixedText = text.replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2');
                    
                    try {
                        return JSON.parse(fixedText);
                    } catch (optionError) {
                        console.log('Option field fix failed:', optionError.message);
                    }
                }
                
                // Step 5: Last resort - create a minimal valid response
                console.log('JSON repair partially succeeded but could not produce valid JSON');
                console.log('Creating fallback response object');
                
                // Get keyword from the page if possible
                const keywordInput = document.getElementById('keywordInput') || document.getElementById('id_keyword');
                const keyword = keywordInput ? keywordInput.value.trim() : 'unknown';
                
                return {
                    status: 'success',
                    metadata: {
                        keywords: [keyword],
                        timestamp: new Date().toISOString(),
                        message: 'Data reconstructed from invalid JSON'
                    },
                    data: {
                        time_series: [],
                        time_trends: []
                    }
                };
            }
        } catch (repairError) {
            console.error('Fatal error during JSON repair process:', repairError);
            
            // Return a valid but empty response object
            return {
                status: 'error',
                error: 'Failed to repair malformed JSON: ' + repairError.message,
                data: {
                    time_series: []
                }
            };
        }
    }
}

// Make key functions globally accessible
window.updateTimeUnit = updateTimeUnit;
window.showSeasonalPattern = showSeasonalPattern;
window.renderCharts = renderCharts;

// Set flag that charts are loaded
window.trendsChartsLoaded = true;

console.log('Trends charts module initialized and key functions exposed globally');

// Function to update UI for analysis option
function updateUIForAnalysisOption(option) {
    console.log('Updating UI for analysis option:', option);
    
    const chartControlsSection = document.getElementById('chartControlsSection');
    const geoOnlyInfoSection = document.getElementById('geoOnlyInfoSection');
    const timeChartContainer = document.getElementById('timeChartContainer');
    const stateChartContainer = document.getElementById('stateChartContainer');
    const cityChartContainer = document.getElementById('cityChartContainer');
    
    // State-only or city-only modes don't show time trends
    const isGeoOnly = option === '5' || option === '6';
    // Time-only mode doesn't show geographic charts
    const isTimeOnly = option === '1';
    
    if (chartControlsSection) chartControlsSection.style.display = isGeoOnly ? 'none' : 'flex';
    if (geoOnlyInfoSection) geoOnlyInfoSection.style.display = isGeoOnly ? 'block' : 'none';
    if (timeChartContainer) timeChartContainer.style.display = isGeoOnly ? 'none' : 'block';
    
    // Show/hide state chart based on option
    if (stateChartContainer) {
        if (isTimeOnly) {
            stateChartContainer.style.display = 'none';
        } else {
            stateChartContainer.style.display = (option === '2' || option === '4' || option === '5') ? 'block' : 'none';
        }
    }
    
    // Show/hide city chart based on option
    if (cityChartContainer) {
        if (isTimeOnly) {
            cityChartContainer.style.display = 'none';
        } else {
            cityChartContainer.style.display = (option === '3' || option === '4' || option === '6') ? 'block' : 'none';
        }
    }
}

/**
 * Helper function to fetch with retry and exponential backoff
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} maxRetries - Maximum number of retries
 * @param {number} delay - Initial delay in ms
 * @returns {Promise<Response>} - Fetch response
 */
async function fetchWithRetry(url, options = {}, retries = 3, delay = 1000) {
    return fetch(url, options)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.text();
        })
        .then(responseText => {
            // Ensure the response is valid JSON
            const validJSON = ensureValidJSON(responseText);
            const data = JSON.parse(validJSON);
            
            // Additional verification for option field
            if (data.metadata && data.metadata.analysis_option) {
                // Ensure option is stored as a string
                if (typeof data.metadata.analysis_option !== 'string') {
                    data.metadata.analysis_option = String(data.metadata.analysis_option);
                }
            }
            
            return data;
        })
        .catch(error => {
            if (retries > 0) {
                console.log(`Retry attempt remaining: ${retries}. Retrying in ${delay}ms...`);
                return new Promise(resolve => setTimeout(resolve, delay))
                    .then(() => fetchWithRetry(url, options, retries - 1, delay * 1.5));
            } else {
                console.error('Fetch failed after retries:', error);
                // Return a minimal valid response structure
                return {
                    error: `Fetch failed: ${error.message}`,
                    time_series: []
                };
            }
        });
}

/**
 * Show error message in the UI
 * @param {string} message - Error message to display
 */
function showErrorMessage(message) {
    // First try to use the existing showError function if available
    if (typeof showError === 'function') {
        showError(message);
        return;
    }
    
    // Otherwise implement our own error display
    const errorContainer = document.getElementById('error-container');
    if (!errorContainer) {
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            const newErrorContainer = document.createElement('div');
            newErrorContainer.id = 'error-container';
            newErrorContainer.className = 'alert alert-danger mt-3';
            newErrorContainer.style.display = 'none';
            chartContainer.parentNode.insertBefore(newErrorContainer, chartContainer);
            showErrorMessage(message);
            return;
        }
    } else {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
}

/**
 * Hide error message in the UI
 */
function hideErrorMessage() {
    // First try to use existing hideError function if available
    if (typeof hideError === 'function') {
        hideError();
        return;
    }
    
    // Otherwise implement our own error hiding
    const errorContainer = document.getElementById('error-container');
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
}

function renderCharts() {
    // Use lastFetchedKeyword or get it from the input if available
    const selectedKeyword = lastFetchedKeyword || (keywordInput ? keywordInput.value.trim() : null);
    
    if (!selectedKeyword) {
        console.error("No keyword available for renderCharts");
        return;
    }

    hideErrorMessage();
    
    // Get the selected option from the dropdown
    const analysisOption = document.getElementById('analysisOption')?.value || document.getElementById('analysis-option')?.value || '1';
    const url = `/trends/api/data/?keyword=${encodeURIComponent(selectedKeyword)}&analysis_option=${encodeURIComponent(analysisOption)}`;
    
    // Check if we already have data for this keyword and option
    if (dataAlreadyFetched && lastFetchedKeyword === selectedKeyword) {
        console.log('Using cached data for', selectedKeyword);
        // Render charts with existing data
        if (trendsData) {
            handleTrendsData(trendsData);
        }
        return;
    }
    
    // Show loading spinner
    if (document.getElementById('loading-spinner')) {
        document.getElementById('loading-spinner').style.display = 'block';
    }
    
    // Show the loader
    if (inlineLoader) {
        inlineLoader.style.display = 'flex';
        inlineLoader.style.opacity = '1';
        
        // Update the loader text with the current keyword
        const keywordSpan = inlineLoader.querySelector('.text-sm .font-semibold');
        if (keywordSpan) {
            keywordSpan.textContent = selectedKeyword;
        }
        
        // Add loading class to body
        document.body.classList.add('loading');
    }
    
    // Fetch with retry and better error handling
    fetchWithRetry(url)
        .then(response => {
            // Check if our custom header is present to confirm server-side sanitization
            const sanitized = response.headers.get('X-JSON-Sanitized');
            console.log('Response sanitized by server:', sanitized === 'true');
            return response.text();
        })
        .then(responseText => {
            try {
                console.log(`Raw response length: ${responseText.length}`);
                
                // Check for specific problematic patterns before parsing
                if (responseText.includes('"option":1') || responseText.includes('"option": 1')) {
                    console.log('Detected unquoted option value, fixing automatically');
                    responseText = responseText.replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2');
                }
                
                // First, attempt to parse the response as-is
                let jsonData = JSON.parse(responseText);
                console.log('JSON parsed successfully');
                trendsData = jsonData;
                dataAlreadyFetched = true;
                lastFetchedKeyword = selectedKeyword;
                handleTrendsData(jsonData);
            } catch (e) {
                console.error("JSON parsing error:", e);
                console.log("Error position:", e.message.match(/position (\d+)/)?.[1]);
                
                try {
                    // Attempt to fix the JSON
                    const fixedJson = fixBrokenJSON(responseText);
                    const jsonData = JSON.parse(fixedJson);
                    
                    // If we succeed, handle the data but log a warning
                    console.warn("JSON fixed successfully, but original response had issues");
                    trendsData = jsonData;
                    dataAlreadyFetched = true;
                    lastFetchedKeyword = selectedKeyword;
                    handleTrendsData(jsonData);
                } catch (fixError) {
                    console.error("Could not fix JSON:", fixError);
                    
                    // Show an error message to the user
                    showErrorMessage("Error loading trend data. Please try again or contact support if the issue persists.");
                    
                    // Create a minimal response to prevent charts from breaking
                    const fallbackResponse = {
                        status: "error",
                        error: "Failed to parse server response",
                        data: {
                            time_series: [],
                            metadata: {
                                keyword: selectedKeyword,
                                analysis_option: analysisOption,
                                message: "Data unavailable due to parsing error"
                            }
                        }
                    };
                    
                    // Still try to render whatever we can
                    handleTrendsData(fallbackResponse);
                }
            } finally {
                if (document.getElementById('loading-spinner')) {
                    document.getElementById('loading-spinner').style.display = 'none';
                }
                
                // Update header title with current keyword
                if (headerTitle) {
                    headerTitle.textContent = `${selectedKeyword} in India`;
                }
                
                // Update AI insights button href
                if (aiInsightsButton) {
                    aiInsightsButton.href = `/trends/insights/${encodeURIComponent(selectedKeyword)}/?analysis_option=${analysisOption}`;
                }
                
                // Hide loader
                if (inlineLoader) {
                    inlineLoader.style.opacity = '0';
                    setTimeout(() => {
                        inlineLoader.style.display = 'none';
                        document.body.classList.remove('loading');
                    }, 300);
                }
            }
        })
        .catch(error => {
            console.error("Fetch error:", error);
            
            if (document.getElementById('loading-spinner')) {
                document.getElementById('loading-spinner').style.display = 'none';
            }
            
            // Hide loader
            if (inlineLoader) {
                inlineLoader.style.opacity = '0';
                setTimeout(() => {
                    inlineLoader.style.display = 'none';
                    document.body.classList.remove('loading');
                }, 300);
            }
            
            // User-friendly error message
            let errorMessage = error.message || 'Error connecting to server';
            
            // Make common error messages more user-friendly
            if (error.message && error.message.includes('NetworkError')) {
                errorMessage = 'Network connection error. Please check your internet connection and try again.';
                // Add retry logic for network errors
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    if (typeof showError === 'function') {
                        showError('Attempting to reconnect... Please wait.');
                    }
                }, 2000);
            }
            
            showErrorMessage(`Error: ${errorMessage}`);
            
            // Create a minimal response to prevent charts from breaking
            const fallbackResponse = {
                status: "error",
                error: `Network error: ${error.message}`,
                data: {
                    time_series: [],
                    metadata: {
                        keyword: selectedKeyword,
                        analysis_option: analysisOption,
                        message: "Data unavailable due to network error"
                    }
                }
            };
            
            handleTrendsData(fallbackResponse);
        });
}

// Update the handleTrendsData function to use the enhanced chart rendering
function handleTrendsData(data) {
    if (!data) {
        console.error("No data provided to handleTrendsData");
        showErrorMessage("No data available to display");
        clearCharts();
        return;
    }
    
    // Handle error state
    if (data.status === "error") {
        console.error("Server returned error:", data.error);
        showErrorMessage(`Error: ${data.error || "Unknown server error"}`);
        clearCharts();
        return;
    }
    
    // Check for required data structure and normalize it
    let timeSeriesData = [];
    let keyword = lastFetchedKeyword || "";
    let metadata = {};
    
    // Handle different data structures
    if (data.data) {
        // New API format
        timeSeriesData = data.data.time_trends || data.data.time_series || [];
        if (data.data.metadata) {
            metadata = data.data.metadata;
            if (data.data.metadata.keywords && data.data.metadata.keywords.length > 0) {
                keyword = data.data.metadata.keywords[0];
            }
        }
    } else if (data.time_series) {
        // Old API format
        timeSeriesData = data.time_series;
        metadata = data.metadata || {};
        if (data.keyword) {
            keyword = data.keyword;
        }
    }
    
    if (timeSeriesData.length === 0) {
        console.error("No time series data found in response");
        showErrorMessage("No trend data available for this keyword");
        clearCharts();
        return;
    }
    
    // Store normalized data
    window.normalizedTrendsData = {
        time_series: timeSeriesData,
        keyword: keyword,
        metadata: metadata
    };
    
    console.log("Rendering charts with data for:", keyword);
    console.log("Time series data points:", timeSeriesData.length);
    
    // Clear any existing charts
    clearCharts();
    
    // Render the time series chart
    renderTimeSeriesChart(timeSeriesData, keyword);
    
    // Show results container
    if (resultsContainer) {
        resultsContainer.style.display = 'block';
    }
    
    // Update current time unit buttons to active state
    if (currentTimeUnit) {
        let btnId;
        switch (currentTimeUnit) {
            case 'year':
                btnId = 'viewByYear';
                break;
            case 'quarter':
                btnId = 'viewByQuarter';
                break;
            case 'month':
                btnId = 'viewByMonth';
                break;
            default:
                btnId = 'viewByMonth';
        }
        
        const activeBtn = document.getElementById(btnId);
        if (activeBtn && typeof updateActiveFilterButton === 'function') {
            updateActiveFilterButton(activeBtn);
        }
    }
    
    return true;
}

function clearCharts() {
    // Reset all chart instances
    if (volumeChart) {
        volumeChart.destroy();
        volumeChart = null;
    }
    
    if (deviceChart) {
        deviceChart.destroy();
        deviceChart = null;
    }
    
    if (regionChart) {
        regionChart.destroy();
        regionChart = null;
    }
    
    // Clear any data tables
    const relatedTable = document.getElementById('related-queries-table');
    if (relatedTable) {
        relatedTable.innerHTML = '';
    }
    
    const risingTable = document.getElementById('rising-queries-table');
    if (risingTable) {
        risingTable.innerHTML = '';
    }
}

// Function to update the time unit for the chart
function updateTimeUnit(unit) {
    if (!timeChart) {
        console.error('Time chart not initialized');
        return;
    }
    
    // Update global variable
    currentTimeUnit = unit;
    window.currentTimeUnit = unit;
    console.log('Updating time unit to:', unit);
    
    // Update the chart options
    timeChart.options.scales.x.time.unit = unit;
    
    // If it's a 'year' view, use a more appropriate format
    if (unit === 'year') {
        timeChart.options.scales.x.time.displayFormats = {
            year: 'YYYY'
        };
    } else if (unit === 'quarter') {
        timeChart.options.scales.x.time.displayFormats = {
            quarter: '[Q]Q YYYY'
        };
    } else if (unit === 'month') {
        timeChart.options.scales.x.time.displayFormats = {
            month: 'MMM YYYY'
        };
    }
    
    // Update the chart
    timeChart.update();
}

// Make the function globally available
window.updateTimeUnit = updateTimeUnit;

// Enhanced renderTimeSeriesChart function based on test-ui.html
function renderTimeSeriesChart(timeSeriesData, keyword) {
    const ctx = document.getElementById('timeSeriesChart')?.getContext('2d');
    if (!ctx) {
        console.error("Chart canvas not found");
        return;
    }
    
    // Extract dates and values
    const dates = timeSeriesData.map(item => item.date);
    const values = timeSeriesData.map(item => item[keyword]);
    
    // Calculate moving average (12-week window)
    const movingAverageWindow = 12;
    const movingAverages = [];
    
    for (let i = 0; i < values.length; i++) {
        if (i < movingAverageWindow - 1) {
            movingAverages.push(null);
        } else {
            const windowValues = values.slice(i - movingAverageWindow + 1, i + 1);
            const average = windowValues.reduce((sum, val) => sum + val, 0) / movingAverageWindow;
            movingAverages.push(average);
        }
    }
    
    // Calculate trend line using linear regression
    const xValues = Array.from({ length: values.length }, (_, i) => i);
    const xMean = xValues.reduce((sum, val) => sum + val, 0) / xValues.length;
    const yMean = values.reduce((sum, val) => sum + val, 0) / values.length;
    
    let numerator = 0;
    let denominator = 0;
    
    for (let i = 0; i < values.length; i++) {
        numerator += (xValues[i] - xMean) * (values[i] - yMean);
        denominator += Math.pow(xValues[i] - xMean, 2);
    }
    
    const slope = numerator / denominator;
    const intercept = yMean - slope * xMean;
    
    const trendLine = xValues.map(x => slope * x + intercept);
    
    // Destroy existing chart if it exists
    if (timeChart) {
        timeChart.destroy();
    }
    
    // Create new chart with enhanced visualization
    timeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Search Interest',
                    data: values,
                    borderColor: 'rgba(52, 152, 219, 0.7)',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    pointRadius: 1,
                    pointHoverRadius: 5,
                    fill: true,
                    tension: 0.1
                },
                {
                    label: 'Trend Line',
                    data: trendLine,
                    borderColor: 'rgba(231, 76, 60, 0.7)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    borderDash: [5, 5]
                },
                {
                    label: 'Moving Average (12-week)',
                    data: movingAverages,
                    borderColor: 'rgba(46, 204, 113, 0.7)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        title: function(tooltipItems) {
                            const date = new Date(tooltipItems[0].label);
                            return date.toLocaleDateString('en-US', { 
                                year: 'numeric', 
                                month: 'long', 
                                day: 'numeric' 
                            });
                        }
                    }
                },
                legend: {
                    display: false
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x'
                    },
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: currentTimeUnit || 'month',
                        displayFormats: {
                            month: 'MMM YYYY'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    beginAtZero: false,
                    min: Math.max(0, Math.min(...values) - 10),
                    max: 105,
                    title: {
                        display: true,
                        text: 'Search Interest'
                    }
                }
            }
        }
    });
    
    // Make the chart available globally
    window.timeChart = timeChart;
    
    // Generate enhanced insights based on the data
    generateEnhancedInsights(timeSeriesData, keyword);
    
    return timeChart;
}

// Enhanced insights generation function
function generateEnhancedInsights(timeSeriesData, keyword) {
    if (!timeSeriesData || timeSeriesData.length === 0) {
        const insightsContent = document.getElementById('insightsContent');
        if (insightsContent) {
            insightsContent.innerHTML = '<p>No data available for insights.</p>';
        }
        return;
    }

    const values = timeSeriesData.map(item => item[keyword]);
    const dates = timeSeriesData.map(item => item.date);
    
    const maxValue = Math.max(...values);
    const maxIndex = values.indexOf(maxValue);
    const maxDate = new Date(dates[maxIndex]);
    
    const minValue = Math.min(...values);
    const minIndex = values.indexOf(minValue);
    const minDate = new Date(dates[minIndex]);
    
    const currentValue = values[values.length - 1];
    const yearAgoIndex = values.length - 53; // Approximately 1 year ago (52 weeks)
    const yearAgoValue = yearAgoIndex >= 0 ? values[yearAgoIndex] : null;
    
    const percentChange = yearAgoValue ? ((currentValue - yearAgoValue) / yearAgoValue * 100).toFixed(1) : 'N/A';
    
    // Detect seasonality
    const monthlyAverages = Array(12).fill(0).map(() => []);
    
    dates.forEach((date, index) => {
        const month = new Date(date).getMonth();
        monthlyAverages[month].push(values[index]);
    });
    
    const monthlyMeans = monthlyAverages.map(monthValues => {
        if (monthValues.length === 0) return 0;
        return monthValues.reduce((sum, val) => sum + val, 0) / monthValues.length;
    });
    
    const highestMonth = monthlyMeans.indexOf(Math.max(...monthlyMeans));
    const lowestMonth = monthlyMeans.indexOf(Math.min(...monthlyMeans));
    
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Trend direction (using linear regression calculation from above)
    const xValues = Array.from({ length: values.length }, (_, i) => i);
    const xMean = xValues.reduce((sum, val) => sum + val, 0) / xValues.length;
    const yMean = values.reduce((sum, val) => sum + val, 0) / values.length;
    
    let numerator = 0;
    let denominator = 0;
    
    for (let i = 0; i < values.length; i++) {
        numerator += (xValues[i] - xMean) * (values[i] - yMean);
        denominator += Math.pow(xValues[i] - xMean, 2);
    }
    
    const slope = numerator / denominator;
    const trendDirection = slope > 0.05 ? 'increasing' : 
                          slope < -0.05 ? 'decreasing' : 'stable';
    
    // Generate HTML
    let insightsHTML = `
        <p><strong>Peak Interest:</strong> ${maxValue} on ${maxDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
        <p><strong>Lowest Interest:</strong> ${minValue} on ${minDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
        <p><strong>Current Trend:</strong> The overall trend is ${trendDirection} over the 5-year period.</p>
        <p><strong>Year-over-Year Change:</strong> ${percentChange}% compared to the same time last year.</p>
        <p><strong>Seasonal Pattern:</strong> Interest tends to be highest in ${monthNames[highestMonth]} and lowest in ${monthNames[lowestMonth]}.</p>
    `;
    
    const insightsContent = document.getElementById('insightsContent');
    if (insightsContent) {
        insightsContent.innerHTML = insightsHTML;
    }
}

// Last lines of the file, add these exports
window.renderTimeSeriesChart = renderTimeSeriesChart;
window.generateEnhancedInsights = generateEnhancedInsights;
window.trendsChartsLoaded = true;