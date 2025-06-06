// Trends Chart Rendering and Google AI Integration

// Create global variables to check if functions are loaded
window.trendsChartsLoaded = false;
window.isTrendsChartsLoaded = function() {
    return window.trendsChartsLoaded === true && typeof window.renderCharts === 'function';
};

// Add gradient plugin for chart background
const gradientPlugin = {
    id: 'customCanvasBackgroundColor',
    beforeDraw: (chart, args, options) => {
        const {ctx} = chart;
        ctx.save();
        ctx.globalCompositeOperation = 'destination-over';
        
        if (options.color) {
            ctx.fillStyle = options.color;
            ctx.fillRect(0, 0, chart.width, chart.height);
        }
        
        // Create a gradient effect
        if (options.gradient) {
            const gradient = ctx.createLinearGradient(0, 0, 0, chart.height);
            gradient.addColorStop(0, options.gradient.start || 'rgba(255, 255, 255, 0.1)');
            gradient.addColorStop(1, options.gradient.end || 'rgba(255, 255, 255, 0.8)');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, chart.width, chart.height);
        }
        
        ctx.restore();
    }
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded, initializing Trends Chart functionality');
    
    // Get common elements used across functions
    const keywordInput = document.getElementById('keywordInput');
    const timeframeSelect = document.getElementById('timeframeSelect');
    const regionSelect = document.getElementById('regionSelect');
    const analyzeButton = document.getElementById('analyzeButton');
    const timeUnitButtons = document.querySelectorAll('.time-unit-btn');
    const yearlyFilter = document.getElementById('yearlyFilter');
    const yearlyFilterContainer = document.getElementById('yearlyFilterContainer');
    
    // Only set up the analyze button event listener if it's not already set up in the HTML
    if (analyzeButton && !analyzeButton._hasClickListener) {
        analyzeButton.addEventListener('click', function(e) {
            e.preventDefault();
            handleFormSubmit(e);
        });
        analyzeButton._hasClickListener = true;
    }
    
    // Add enter key event listener for keyword input
    if (keywordInput) {
        keywordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (analyzeButton) {
                    // Trigger the click event on the analyze button to ensure validation runs
                    analyzeButton.click();
                } else {
                    handleFormSubmit(e);
                }
            }
        });
    }
    
    // Register gradient plugin
    Chart.register(gradientPlugin);
    
    // Initialize chart instances to prevent destroy errors
    window.trendsChart = null;
    window.regionChart = null;
    window.originalChartData = null;
    window.originalRegionData = null;
    
    // Add event listeners to time unit buttons
    timeUnitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const unit = this.getAttribute('data-unit');
            // Remove active class from all buttons
            timeUnitButtons.forEach(btn => {
                btn.classList.remove('bg-[#27FFB4]/20');
                btn.classList.remove('border-[#27FFB4]');
            });
            // Add active class to clicked button
            this.classList.add('bg-[#27FFB4]/20');
            this.classList.add('border-[#27FFB4]');
            // Update the chart time unit
            if (typeof window.updateTimeUnit === 'function') {
                window.updateTimeUnit(unit);
            }
        });
    });
    
    // Add event listener for year filter dropdown
    if (yearlyFilter) {
        yearlyFilter.addEventListener('change', function() {
            const selectedYear = this.value;
            console.log('Selected year:', selectedYear);
            updateChartWithYearFilter(selectedYear);
        });
    }
    
    // Add event listener to analysis_type dropdown to log when it changes
    const analysisTypeDropdown = document.getElementById('analysis_type');
    if (analysisTypeDropdown) {
        console.log('Adding change listener to analysis_type dropdown');
        analysisTypeDropdown.addEventListener('change', function() {
            console.log('Analysis type changed to:', this.value);
        });
    } else {
        console.warn('analysis_type dropdown not found');
    }
    
    // Function to update the chart with year filter
    function updateChartWithYearFilter(year) {
        if (!window.trendsChart || !window.originalChartData) {
            console.error('Chart or original data not available for filtering');
            return;
        }
        
        // Store the current year filter
        window.currentYearFilter = year;
        
        // Get the keyword from the chart
        const keyword = window.lastFetchedKeyword;
        if (!keyword) {
            console.error('No keyword found for chart update');
            return;
        }
        
        // Apply year filter to the data
        const filteredData = filterDataByYear(window.originalChartData, year);
        
        // Update datasets
        window.trendsChart.data.labels = filteredData.labels;
        window.trendsChart.data.datasets[0].data = filteredData.values;
        
        // Update additional datasets if they exist
        if (window.trendsChart.data.datasets.length > 1) {
            // Update moving average
            if (filteredData.values.length >= 7) {
                const movingAvgData = calculateMovingAverage(filteredData.values, 7);
                window.trendsChart.data.datasets[1].data = movingAvgData;
            } else {
                window.trendsChart.data.datasets[1].data = Array(filteredData.values.length).fill(null);
            }
            
            // Update trend line
            if (window.trendsChart.data.datasets.length > 2) {
                const trendLineData = calculateTrendLine(filteredData.values);
                window.trendsChart.data.datasets[2].data = trendLineData;
            }
        }
        
        // Update chart title with year information
        const yearInfo = year === 'all' ? 'All Years' : `Year ${year}`;
        window.trendsChart.options.plugins.title = {
            display: true,
            text: `${keyword} Trends - ${yearInfo}`,
            font: {
                size: 16,
                weight: 'bold'
            },
            padding: {
                top: 10,
                bottom: 15
            }
        };
        
        // Update the chart
        window.trendsChart.update();
    }
    
    // Function to handle form submission
    async function handleFormSubmit(e) {
        if (e) {
            e.preventDefault();
        }
        console.log('Form submission handled by handleFormSubmit');
        
        // Get form values
        const keyword = keywordInput ? keywordInput.value.trim() : '';
        let analysisType = '1'; // Default value
        
        // Try to get analysis type from the appropriate element
        const analysisElement = document.getElementById('analysis_type');
        if (analysisElement) {
            analysisType = analysisElement.value;
            console.log('Using analysis_type element value:', analysisType);
        } else if (document.getElementById('analysisOption')) {
            analysisType = document.getElementById('analysisOption').value;
            console.log('Using analysisOption element value:', analysisType);
        } else {
            console.warn('No analysis type element found, using default:', analysisType);
        }
        
        // Get business intent value
        const businessIntentElement = document.getElementById('business_intent');
        const businessIntent = businessIntentElement ? businessIntentElement.value : '';
        console.log('Using business_intent value:', businessIntent);
        
        // Check if business intent is required but not selected
        if (businessIntentElement && businessIntentElement.hasAttribute('required') && !businessIntent) {
            showError('Please select your business intent');
            return;
        }
        
        // Default values for timeframe and geo that match backend expectations
        const timeframe = timeframeSelect ? timeframeSelect.value : 'today 5-y';
        const geo = regionSelect ? regionSelect.value : 'IN';
        
        if (!keyword) {
            showError('Please enter a keyword to analyze');
            return;
        }
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('loadingIndicator');
        const errorContainer = document.getElementById('errorContainer');
        const resultsContainer = document.getElementById('resultsContainer');
        
        // Hide error and results container, show loading
        if (errorContainer) errorContainer.style.display = 'none';
        if (resultsContainer) resultsContainer.style.display = 'none';
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex'; // Use flex to center content
            console.log('Showing loading indicator');
        }
        
        try {
            console.log('Making API request for analysis_type:', analysisType);
            
            const requestBody = {
                keyword: keyword,
                analysis_type: analysisType,
                timeframe: timeframe,
                geo: geo,
                business_intent: businessIntent
            };
            
            // Add business details if business intent is 'no'
            if (businessIntent === 'no') {
                const brandName = document.getElementById('brandName').value;
                const businessWebsite = document.getElementById('businessWebsite').value;
                const marketplace = document.getElementById('marketplace').value;
                
                // Check if required business details are provided (website is optional)
                if (!brandName || !marketplace) {
                    showError('Please provide brand name and marketplace');
                    if (loadingIndicator) loadingIndicator.style.display = 'none';
                    return;
                }
                
                // Add business details to request body
                requestBody.brand_name = brandName;
                requestBody.user_website = businessWebsite;
                requestBody.marketplaces_selected = marketplace;
            }
            
            console.log('API request full payload:', JSON.stringify(requestBody));
            
            const response = await fetch('/trends/api/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received API response:', data);
            
            if (data.status === 'error') {
                throw new Error(data.errors && data.errors.length > 0 ? data.errors[0] : 'Failed to fetch trends data');
            }
            
            // Check if data is from SERP API
            const isFromSerpApi = data.metadata && data.metadata.source === 'serp_api';
            if (isFromSerpApi) {
                console.log('Data is from SERP API');
                
                // Check if this is raw data directly passed through
                if (data.metadata.raw_data === true) {
                    console.log('Raw SERP API data passed through by backend, using special handler');
                    const processedData = processSerpApiData(data, keyword);
                    console.log('Processed raw SERP API data:', processedData);
                    
                    if (processedData && processedData.length > 0) {
                        // Store the processed data for potential reuse
                        window.trendsData = processedData;
                        
                        // Create proper chart data format for originalChartData
                        const labels = processedData.map(item => item.date);
                        const values = processedData.map(item => item[keyword]);
                        window.originalChartData = { labels, values };
                        
                        // Render the chart with the processed data
                        renderTrendsChart(processedData, keyword);
                        
                        // Extract years from data and populate the year filter dropdown
                        extractYearsFromData(window.originalChartData);
                        
                        // Initialize AI analysis
                        if (typeof window.initializeAIAnalysis === 'function') {
                            window.initializeAIAnalysis();
                        }
                        return;
                    } else {
                        console.error('Failed to process raw SERP API data');
                        showError('Failed to process data from SERP API. Please try again.');
                        return;
                    }
                }
                
                // Otherwise transform processed SERP API data
                data = transformSerpApiData(data, keyword);
            }
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
                console.log('Hiding loading indicator');
            }
            
            // Show results container
            if (resultsContainer) {
                resultsContainer.style.display = 'grid';
                console.log('Showing results container');
            }
            
            // Store the data globally for debugging and reuse
            window.trendsData = data.data || data;
            window.lastFetchedKeyword = keyword;
            
            console.log('Analysis Type:', analysisType);
            
            // Check if this is direct SERP API data (not processed by backend)
            if (data.interest_over_time && data.interest_over_time.timeline_data) {
                console.log('Detected direct raw SERP API data, using special handler');
                const processedData = processSerpApiData(data, keyword);
                console.log('Processed SERP API data:', processedData);
                
                if (processedData && processedData.length > 0) {
                    // Store the processed data for potential reuse
                    window.trendsData = processedData;
                    
                    // Create proper chart data format for originalChartData
                    const labels = processedData.map(item => item.date);
                    const values = processedData.map(item => item[keyword]);
                    window.originalChartData = { labels, values };
                    
                    // Render the chart with the processed data
                    renderTrendsChart(processedData, keyword);
                    
                    // Extract years from data and populate the year filter dropdown
                    extractYearsFromData(window.originalChartData);
                    
                    // Initialize AI analysis after chart is rendered
                    if (typeof window.initializeAIAnalysis === 'function') {
                        window.initializeAIAnalysis();
                    }
                    return;
                } else {
                    console.error('Failed to process SERP API data');
                    showError('Failed to process SERP API data. Please try again.');
                    return;
                }
            }
            
            // Get chart containers
            const timeChartContainer = document.getElementById('chartContainer').parentElement;
            const regionChartContainer = document.getElementById('regionChartContainer');
            
            // Default - hide region chart
            if (regionChartContainer) {
                regionChartContainer.style.display = 'none';
            }
            
            // Determine which chart to show based on analysis type
            if (analysisType === '2') { // Regional Analysis
                console.log('Selected Regional Analysis');
                
                // Hide time chart, show region chart
                if (timeChartContainer) {
                    timeChartContainer.style.display = 'none';
                }
                
                // Make sure any existing chart is destroyed
                try {
                    if (window.regionChart) {
                        if (typeof window.regionChart === 'object' && 
                            typeof window.regionChart.destroy === 'function') {
                            window.regionChart.destroy();
                        }
                        window.regionChart = null;
                    }
                } catch (chartError) {
                    console.error('Error cleaning up existing chart:', chartError);
                    window.regionChart = null;
                }
                
                // For regional analysis, ensure we have the region_data from the response
                let regionData = null;
                
                // Check different possible formats of regional data
                if (data.interest_by_region && Array.isArray(data.interest_by_region)) {
                    console.log('Found direct SERP API interest_by_region format');
                    regionData = data.interest_by_region;
                } else if (data.data && data.data.region_data && Array.isArray(data.data.region_data)) {
                    console.log('Found nested region_data array');
                    regionData = data.data.region_data;
                }
                
                // Make a copy of the raw data for debugging
                window.rawRegionalData = JSON.parse(JSON.stringify(data));
                
                if (regionData && regionData.length > 0) {
                    console.log(`Rendering regional chart with ${regionData.length} regions`);
                    try {
                        renderRegionalChart(regionData, keyword);
                    } catch (renderError) {
                        console.error('Error rendering regional chart with provided data:', renderError);
                        
                        // Try again with SERP API fallback
                        console.log('Attempting to fetch from SERP API as fallback...');
                        tryFetchSerpApiRegionalData(keyword, timeframe, geo);
                    }
                } else {
                    console.log('No regional data found in the response, attempting to fetch from SERP API');
                    tryFetchSerpApiRegionalData(keyword, timeframe, geo);
                }
            } else if (analysisType === '6') { // City-Level Analysis
                console.log('Selected City-Level Analysis');
                // Future implementation for city-level visualization
                
                // For now, default to time trends
                if (timeChartContainer) {
                    timeChartContainer.style.display = 'block';
                }
                
                // Determine the actual data to render for time trends
                let chartData = data.data;
                if (!chartData && Array.isArray(data)) {
                    chartData = data;
                }
                
                renderTrendsChart(chartData || data, keyword);
                
            } else if (analysisType === '7') { // Complete Analysis
                console.log('Selected Complete Analysis');
                
                // Show both charts if data is available
                if (timeChartContainer) {
                    timeChartContainer.style.display = 'block';
                }
                
                // Render time trends chart
                let chartData = data.data;
                if (!chartData && Array.isArray(data)) {
                    chartData = data;
                }
                
                renderTrendsChart(chartData || data, keyword);
                
                // Render regional chart if data is available
                const regionData = data.data?.region_data || [];
                if (regionData && regionData.length > 0) {
                    console.log('Rendering regional chart with data:', regionData);
                    renderRegionalChart(regionData, keyword);
                    
                    // Show the region chart container
                    if (regionChartContainer) {
                        regionChartContainer.style.display = 'block';
                    }
                } else {
                    console.warn('No regional data available for complete analysis');
                }
                
            } else { // Default to Time Trends Analysis (analysis_type=1)
                console.log('Using Time Trends Analysis');
                
                // Show time chart
                if (timeChartContainer) {
                    timeChartContainer.style.display = 'block';
                }
                
                // Determine the actual data to render
                let chartData = data.data;
                if (!chartData && Array.isArray(data)) {
                    chartData = data;
                    console.log('Data is directly an array, using it as chart data');
                }
                
                // Check what format the data is in
                if (Array.isArray(chartData) && chartData.length > 0) {
                    console.log('First data point sample:', chartData[0]);
                    if (chartData[0][keyword] !== undefined) {
                        console.log(`Data point has keyword "${keyword}" as property with value:`, chartData[0][keyword]);
                    }
                } else if (chartData && typeof chartData === 'object') {
                    console.log('Data structure:', Object.keys(chartData));
                }
                
                // Try to render the chart with the data
                renderTrendsChart(chartData || data, keyword);
            }
            
            // Initialize AI analysis after chart is rendered
            if (typeof window.initializeAIAnalysis === 'function') {
                window.initializeAIAnalysis();
            }
        } catch (error) {
            console.error('Error fetching trends data:', error);
            
            // Hide loading
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Show error
            showError(error.message || 'Failed to fetch trends data. Please try again later.');
            
            // Keep results container hidden
            if (resultsContainer) {
                resultsContainer.style.display = 'none';
            }
        }
    }
    
    // Global variables
    let trendsData = null;
    let dataAlreadyFetched = false;
    let lastFetchedKeyword = '';
    let trendsChart = null;
    let currentTimeUnit = 'month'; // Default time unit
    let currentFetchController = null; // For fetch abort control
    
    // Make key variables available globally
    window.currentTimeUnit = currentTimeUnit;
    window.trendsData = trendsData;
    window.lastFetchedKeyword = lastFetchedKeyword;
    window.trendsChart = trendsChart;
    window.currentFetchController = currentFetchController;
    window.filterChartByYear = function(year) {
        // Public function to filter chart by year
        if (typeof updateChartWithYearFilter === 'function') {
            updateChartWithYearFilter(year);
        } else {
            console.error('updateChartWithYearFilter function not available');
        }
    };
    
    const googleApiConfigured = window.googleApiConfigured || false;
    
    // Debug logging
    console.log('Trends charts JS loaded');
    console.log('Google API configured:', googleApiConfigured);
    
    // Set the trendsChartsLoaded flag to true
    window.trendsChartsLoaded = true;
    
    // Function to update the time unit for the time series chart
    function updateTimeUnit(unit) {
        console.log('Updating time unit to:', unit);
        
        if (!window.trendsChart) {
            console.error('Trends chart not found');
            return;
        }
        
        // Update current time unit
        window.currentTimeUnit = unit;
        
        // Check if the chart is using time scale
        if (window.trendsChart.options.scales.x && window.trendsChart.options.scales.x.type === 'time') {
            // Update the time unit
            window.trendsChart.options.scales.x.time.unit = unit;
            window.trendsChart.update();
        } else {
            console.warn('Chart is not using time scale, cannot update time unit');
        }
    }
    
    // Make the updateTimeUnit function available globally
    window.updateTimeUnit = updateTimeUnit;
    
    // Function to render the trends chart
    window.renderTrendsChart = function(data, keyword) {
        console.log('Rendering trends chart with data:', data);
        
        if (!data) {
            console.error('No data provided for chart rendering');
            return;
        }
        
        // Clear any existing chart
        if (window.trendsChart) {
            window.trendsChart.destroy();
            window.trendsChart = null;
        }
        
        // Get chart container
        const chartContainer = document.getElementById('trendsChart');
        if (!chartContainer) {
            console.error('Chart container not found');
            return;
        }
        
        try {
            // Process and format the data for Chart.js
            const chartData = processTimeSeriesData(data, keyword);
            
            // Store the original chart data globally for filtering
            window.originalChartData = chartData;
            window.currentYearFilter = 'all';
            
            // Additional validation for SERP API data
            // Make sure we have valid data after processing
            if (!chartData || !chartData.labels || chartData.labels.length === 0) {
                console.error('Failed to process chart data - no valid labels found:', chartData);
                
                // Try direct handling for SERP API data as a last resort
                if (Array.isArray(data) && data.length > 0 && (data[0].date || data[0].timestamp)) {
                    console.log('Attempting direct chart rendering with supplied array data');
                    
                    // Create simple labels and values
                    const labels = [];
                    const values = [];
                    
                    data.forEach(point => {
                        let date = point.date instanceof Date ? point.date : (point.date ? new Date(point.date) : null);
                        
                        // If date is invalid or missing, try using timestamp
                        if (!date || isNaN(date.getTime())) {
                            if (point.timestamp) {
                                date = new Date(parseInt(point.timestamp, 10) * 1000);
                            }
                        }
                        
                        // Skip if we couldn't get a valid date
                        if (!date || isNaN(date.getTime())) {
                            return;
                        }
                        
                        // Get the value either directly or from the keyword property
                        let value = point[keyword] !== undefined ? point[keyword] : 
                                  (point.value !== undefined ? point.value : null);
                                  
                        // Skip if we don't have a value
                        if (value === null || value === undefined) {
                            return;
                        }
                        
                        // Convert to number if string
                        if (typeof value === 'string') {
                            value = parseInt(value, 10);
                        }
                        
                        // Add valid data point
                        labels.push(date);
                        values.push(value);
                    });
                    
                    // Check if we have enough data points
                    if (labels.length > 0 && values.length > 0) {
                        console.log(`Using direct data with ${labels.length} points`);
                        
                        // Sort by date
                        const combined = labels.map((date, i) => ({ date, value: values[i] }));
                        combined.sort((a, b) => a.date - b.date);
                        
                        // Use the direct data instead
                        chartData = { 
                            labels: combined.map(item => item.date),
                            values: combined.map(item => item.value)
                        };
                        
                        // Store the original chart data globally for filtering
                        window.originalChartData = chartData;
                        
                        // Extract years from data and populate the year filter dropdown
                        extractYearsFromData(chartData);
                    } else {
                        showError('Unable to display chart - no valid data found');
                        return;
                    }
                } else {
                    showError('Unable to display chart - no valid data found');
                    return;
                }
            }
            
            // Create beautiful fill gradients
            const ctx = chartContainer.getContext('2d');
            const primaryGradient = ctx.createLinearGradient(0, 0, 0, 400);
            primaryGradient.addColorStop(0, 'rgba(39, 255, 180, 0.4)');
            primaryGradient.addColorStop(1, 'rgba(39, 255, 180, 0.05)');
            
            // Create dataset with multiple lines for comparison
            const datasets = [
                {
                    label: keyword,
                    data: chartData.values,
                    borderColor: 'rgba(39, 255, 180, 1)', // bright teal (#27FFB4)
                    backgroundColor: primaryGradient,
                    borderWidth: 3,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(39, 255, 180, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(39, 255, 180, 1)',
                    tension: 0.4,
                    fill: true
                }
            ];
            
            // Add moving average line if enough data points
            if (chartData.values.length >= 7) {
                const movingAvgData = calculateMovingAverage(chartData.values, 7);
                datasets.push({
                    label: '7-period Moving Average',
                    data: movingAvgData,
                    borderColor: 'rgba(139, 92, 246, 0.9)', // purple-500
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    tension: 0.4,
                    fill: false
                });
            }
            
            // Add trend line
            const trendLineData = calculateTrendLine(chartData.values);
            datasets.push({
                label: 'Trend Line',
                data: trendLineData,
                borderColor: 'rgba(255, 102, 204, 0.8)', // pink
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 0,
                tension: 0,
                fill: false
            });
            
            // Chart configuration
            const config = {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: {
                            top: 10,
                            right: 25,
                            bottom: 10,
                            left: 10
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: currentTimeUnit,
                                displayFormats: {
                                    day: 'MMM d, yyyy',
                                    week: 'MMM d, yyyy',
                                    month: 'MMM yyyy',
                                    quarter: 'QQQ yyyy',
                                    year: 'yyyy'
                                },
                                tooltipFormat: 'MMMM d, yyyy'
                            },
                            title: {
                                display: true,
                                text: 'Date',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                font: {
                                    size: 12
                                }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Interest',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                font: {
                                    size: 12
                                },
                                callback: function(value) {
                                    return value;
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: `${keyword} Trends - All Years`,
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 15
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                boxWidth: 8,
                                padding: 20,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {
                                size: 14,
                                weight: 'bold'
                            },
                            bodyFont: {
                                size: 13
                            },
                            padding: 12,
                            cornerRadius: 6,
                            callbacks: {
                                title: function(tooltipItems) {
                                    const date = new Date(tooltipItems[0].parsed.x);
                                    if (currentTimeUnit === 'day' || currentTimeUnit === 'week') {
                                        return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
                                    } else if (currentTimeUnit === 'month') {
                                        return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long' });
                                    } else if (currentTimeUnit === 'quarter') {
                                        const quarter = Math.floor(date.getMonth() / 3) + 1;
                                        return `Q${quarter} ${date.getFullYear()}`;
                                    } else {
                                        return date.getFullYear().toString();
                                    }
                                },
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += context.parsed.y;
                                    }
                                    return label;
                                }
                            }
                        },
                        customCanvasBackgroundColor: {
                            color: 'rgba(255, 255, 255, 1)',
                            gradient: {
                                start: 'rgba(240, 249, 255, 1)',
                                end: 'rgba(255, 255, 255, 1)'
                            }
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    },
                    animations: {
                        tension: {
                            duration: 1000,
                            easing: 'easeInOutQuad'
                        },
                        y: {
                            duration: 1000,
                            easing: 'easeOutCubic'
                        },
                        x: {
                            duration: 1000,
                            easing: 'easeOutCubic'
                        },
                        radius: {
                            duration: 400,
                            easing: 'easeOutCubic'
                        }
                    },
                    transitions: {
                        active: {
                            animation: {
                                duration: 400
                            }
                        }
                    }
                }
            };
            
            // Create and render the chart
            window.trendsChart = new Chart(chartContainer, config);
            console.log('Chart rendered successfully');
            
            // Add chart zoom in/out animation on container hover
            const chartContainerDiv = document.getElementById('chartContainer');
            if (chartContainerDiv) {
                chartContainerDiv.addEventListener('mouseenter', () => {
                    window.trendsChart.options.layout.padding = {
                        top: 5, right: 15, bottom: 5, left: 5
                    };
                    window.trendsChart.update();
                });
                
                chartContainerDiv.addEventListener('mouseleave', () => {
                    window.trendsChart.options.layout.padding = {
                        top: 10, right: 25, bottom: 10, left: 10
                    };
                    window.trendsChart.update();
                });
            }
            
            // Extract years from data and populate the year filter dropdown
            extractYearsFromData(chartData);
        } catch (error) {
            console.error('Error rendering chart:', error);
            showError('Error rendering chart: ' + error.message);
        }
    };
    
    // Helper function to process time series data
    function processTimeSeriesData(data, keyword) {
        console.log('Processing time series data for keyword:', keyword);
        
        if (!data || (!Array.isArray(data) && typeof data !== 'object')) {
            console.error('Invalid data format for processing');
            return null;
        }
        
        try {
            let timeSeriesData = null;
            
            // Debug data structure
            console.log('Data structure:', typeof data);
            if (typeof data === 'object') {
                console.log('Top-level keys:', Object.keys(data));
                
                // Check for data.data structure
                if (data.data && typeof data.data === 'object') {
                    console.log('Data.data keys:', Object.keys(data.data));
                    
                    // Check for time_trends in data.data
                    if (data.data.time_trends) {
                        console.log('Found time_trends array with length:', 
                            Array.isArray(data.data.time_trends) ? data.data.time_trends.length : 'not an array');
                    }
                }
            }
            
            // Handle different data formats - check the most specific paths first
            
            // 1. Backend API format: data -> data -> time_trends (array)
            if (data && data.data && data.data.time_trends && Array.isArray(data.data.time_trends)) {
                console.log('Using data.data.time_trends format');
                timeSeriesData = data.data.time_trends;
            } 
            // 2. Backend API direct format: data -> time_trends (array)
            else if (data && data.time_trends && Array.isArray(data.time_trends)) {
                console.log('Using data.time_trends format');
                timeSeriesData = data.time_trends;
            }
            // 3. Google Trends API format
            else if (data && data.default && data.default.timelineData && Array.isArray(data.default.timelineData)) {
                console.log('Using Google Trends API format');
                timeSeriesData = data.default.timelineData;
            }
            // 4. SERP API format - interest_over_time with timeline_data array
            else if (data && data.interest_over_time && data.interest_over_time.timeline_data && 
                     Array.isArray(data.interest_over_time.timeline_data)) {
                console.log('Using SERP API interest_over_time.timeline_data format');
                timeSeriesData = data.interest_over_time.timeline_data;
            }
            // 5. Direct array of time series data
            else if (Array.isArray(data)) {
                console.log('Data is directly an array');
                timeSeriesData = data;
            }
            // 6. Fallback: try to find an array inside the object
            else if (typeof data === 'object') {
                console.log('Searching for time series array in object');
                // First look for known keys that might contain time series data
                const possibleKeys = ['time_trends', 'timelineData', 'timeline', 'data', 'trends', 'values', 'series'];
                
                for (const key of possibleKeys) {
                    if (data[key] && Array.isArray(data[key]) && data[key].length > 0) {
                        console.log(`Found array in data.${key}`);
                        timeSeriesData = data[key];
                        break;
                    } else if (data[key] && typeof data[key] === 'object') {
                        // Check one level deeper
                        for (const subKey of possibleKeys) {
                            if (data[key][subKey] && Array.isArray(data[key][subKey]) && data[key][subKey].length > 0) {
                                console.log(`Found array in data.${key}.${subKey}`);
                                timeSeriesData = data[key][subKey];
                                break;
                            }
                        }
                        if (timeSeriesData) break;
                    }
                }
                
                // If still not found, try to find any array in the object
                if (!timeSeriesData) {
                    for (const key in data) {
                        if (Array.isArray(data[key]) && data[key].length > 0) {
                            console.log(`Found array in data.${key}`);
                            timeSeriesData = data[key];
                            break;
                        } else if (data[key] && typeof data[key] === 'object') {
                            // Check one level deeper
                            for (const subKey in data[key]) {
                                if (Array.isArray(data[key][subKey]) && data[key][subKey].length > 0) {
                                    console.log(`Found array in data.${key}.${subKey}`);
                                    timeSeriesData = data[key][subKey];
                                    break;
                                }
                            }
                            if (timeSeriesData) break;
                        }
                    }
                }
            }
            
            if (!timeSeriesData || !Array.isArray(timeSeriesData) || timeSeriesData.length === 0) {
                console.error('Could not extract time series data');
                return null;
            }
            
            console.log('First data point sample:', timeSeriesData[0]);
            
            // Extract dates and values
            const labels = [];
            const values = [];
            
            timeSeriesData.forEach((point, index) => {
                // Handle different time/date formats
                let date = null;
                let value = null;
                
                if (point.date) {
                    // Format: { date: '2020-01-01', keyword: 42 }
                    
                    // Check if the date string has SERP API's format with range (e.g., "May 19–25, 2024")
                    if (typeof point.date === 'string' && point.date.includes('–')) {
                        // Extract the month and year (and possibly first day) from the range format
                        const dateStr = point.date;
                        let month, year, day;
                        
                        // Parse month and year
                        const monthMatch = dateStr.match(/([A-Za-z]+)/);
                        const yearMatch = dateStr.match(/\d{4}/);
                        
                        if (monthMatch && yearMatch) {
                            month = monthMatch[1];
                            year = yearMatch[0];
                            
                            // Try to extract day (first number before the en-dash)
                            const dayMatch = dateStr.match(/(\d+)\s*[–\-]/);
                            day = dayMatch ? dayMatch[1] : '1';
                            
                            // Construct a date string that's easier to parse
                            const parsableDate = `${month} ${day}, ${year}`;
                            date = new Date(parsableDate);
                            
                            // If invalid, fallback to first day of month and year
                            if (isNaN(date.getTime())) {
                                date = new Date(`${month} 1, ${year}`);
                            }
                        } else {
                            // Fallback: just use the current date with an offset based on the index
                            date = new Date();
                            date.setDate(date.getDate() - (timeSeriesData.length - index));
                        }
                    } else {
                        // Standard date format
                        date = new Date(point.date);
                    }
                    
                    // Check for SERP API format which has nested values array with extracted_value
                    if (point.values && Array.isArray(point.values)) {
                        // Find the value for the specific keyword or just take the first one
                        const valueObj = point.values.find(v => v.query === keyword) || point.values[0];
                        if (valueObj) {
                            value = valueObj.extracted_value !== undefined ? 
                                   valueObj.extracted_value : 
                                   (valueObj.value !== undefined ? valueObj.value : null);
                        }
                    } else {
                        // Regular format
                        value = point[keyword] !== undefined ? point[keyword] : (point.value !== undefined ? point.value : null);
                    }
                } else if (point.timestamp) {
                    // SERP API format with timestamp (seconds since epoch)
                    const timestamp = parseInt(point.timestamp, 10) * 1000; // Convert to milliseconds
                    date = new Date(timestamp);
                    
                    // Extract value from nested values array if present
                    if (point.values && Array.isArray(point.values)) {
                        const valueObj = point.values.find(v => v.query === keyword) || point.values[0];
                        if (valueObj) {
                            value = valueObj.extracted_value !== undefined ? 
                                   valueObj.extracted_value : 
                                   (valueObj.value !== undefined ? valueObj.value : null);
                        }
                    } else {
                        value = point.value !== undefined ? point.value : null;
                    }
                } else if (point.time) {
                    // Format: { time: '2020-01-01', value: 42 }
                    date = new Date(point.time);
                    value = point.value !== undefined ? point.value : null;
                } else if (point.formattedTime || point.formattedAxisTime) {
                    // Google Trends format
                    const timeStr = point.formattedTime || point.formattedAxisTime;
                    date = new Date(timeStr);
                    
                    if (point.value && Array.isArray(point.value)) {
                        value = point.value[0];
                    } else {
                        value = point.value;
                    }
                } else if (typeof point === 'number' && timeSeriesData.length > index) {
                    // Simple array of values without dates
                    // Use index as x-coordinate (relative dates)
                    date = new Date();
                    date.setDate(date.getDate() - (timeSeriesData.length - index));
                    value = point;
                }
                
                // Final fallback: if we have a value but no date, use the index
                if (value !== null && !isNaN(value) && !date) {
                    date = new Date();
                    date.setDate(date.getDate() - (timeSeriesData.length - index));
                }
                
                if (date && value !== null && !isNaN(value)) {
                    labels.push(date);
                    values.push(Number(value));
                }
            });
            
            // If we couldn't extract any data points, return null
            if (labels.length === 0 || values.length === 0) {
                console.error('No valid data points extracted');
                return null;
            }
            
            console.log(`Processed ${labels.length} data points for chart`);
            
            // Ensure data is ordered by date
            const combined = labels.map((date, i) => ({ date, value: values[i] }));
            combined.sort((a, b) => a.date - b.date);
            
            return { 
                labels: combined.map(item => item.date),
                values: combined.map(item => item.value)
            };
        } catch (error) {
            console.error('Error processing time series data:', error);
            return null;
        }
    }
    
    // Function to filter chart data by selected year
    function filterDataByYear(chartData, year) {
        if (!chartData || !chartData.labels || !chartData.values || chartData.labels.length === 0) {
            console.error('Invalid chart data for filtering');
            return chartData;
        }

        // If "all" is selected, return all data
        if (year === 'all') {
            return chartData;
        }

        const yearNumber = parseInt(year, 10);
        if (isNaN(yearNumber)) {
            console.error('Invalid year for filtering:', year);
            return chartData;
        }

        console.log(`Filtering data for year: ${yearNumber}`);

        // Filter data points for the selected year
        const filteredIndices = [];
        chartData.labels.forEach((date, index) => {
            if (date instanceof Date && date.getFullYear() === yearNumber) {
                filteredIndices.push(index);
            }
        });

        // If no data points for the selected year, return original data
        if (filteredIndices.length === 0) {
            console.warn(`No data points found for year: ${yearNumber}`);
            return chartData;
        }

        console.log(`Found ${filteredIndices.length} data points for year: ${yearNumber}`);

        // Create new filtered dataset
        return {
            labels: filteredIndices.map(i => chartData.labels[i]),
            values: filteredIndices.map(i => chartData.values[i])
        };
    }

    // Function to extract unique years from chart data and populate the year filter dropdown
    function extractYearsFromData(chartData) {
        if (!chartData || !chartData.labels || chartData.labels.length === 0) {
            console.error('Invalid chart data for extracting years');
            return [];
        }

        // Extract years from date labels
        const years = new Set();
        chartData.labels.forEach(date => {
            if (date instanceof Date && !isNaN(date.getTime())) {
                years.add(date.getFullYear());
            }
        });

        // Convert to array and sort in descending order (most recent first)
        const yearsArray = Array.from(years).sort((a, b) => b - a);
        console.log('Extracted years from data:', yearsArray);

        // Populate the year filter dropdown
        const yearlyFilter = document.getElementById('yearlyFilter');
        if (yearlyFilter) {
            // Clear existing options except 'All Years'
            while (yearlyFilter.options.length > 1) {
                yearlyFilter.remove(1);
            }

            // Add options for each year
            yearsArray.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                yearlyFilter.appendChild(option);
            });
        }

        return yearsArray;
    }

    // Make the processTimeSeriesData function available globally
    window.renderTrendsChart = renderTrendsChart;
});

// Function to render regional chart with bar visualization
function renderRegionalChart(data, keyword) {
    console.log('Rendering regional chart with data:', typeof data, Array.isArray(data) ? data.length : 'not array');
    
    try {
        // Check for valid regional data first
        if (!data || !Array.isArray(data) || data.length === 0) {
            // Check if this is a full response object that contains regional data
            if (data && typeof data === 'object') {
                console.log('Checking for regional data in response object');
                
                // Try to find regional data in various formats
                if (data.interest_by_region && Array.isArray(data.interest_by_region) && data.interest_by_region.length > 0) {
                    console.log('Found interest_by_region array, using it for regional chart');
                    data = data.interest_by_region;
                } else if (data.data && data.data.region_data && Array.isArray(data.data.region_data) && data.data.region_data.length > 0) {
                    console.log('Found data.region_data array, using it for regional chart');
                    data = data.data.region_data;
                } else {
                    // Last chance: check if data has properties that look like regional data
                    const firstKey = Object.keys(data)[0];
                    if (firstKey && Array.isArray(data[firstKey]) && data[firstKey].length > 0) {
                        console.log(`Found array in data.${firstKey}, attempting to use it for regional chart`);
                        data = data[firstKey];
                    } else {
                        console.error('Response object does not contain valid regional data');
                        showError('No valid regional data available. Please try a different search term or region.');
                        return;
                    }
                }
            } else {
                console.error('No valid regional data provided for chart rendering');
                showError('No regional data available. Please try a different search term or region.');
                return;
            }
        }
        
        if (!Array.isArray(data) || data.length === 0) {
            console.error('Data is still not a valid array after initial processing');
            showError('Invalid regional data format. Please try a different search term or region.');
            return;
        }
        
        console.log('Regional data sample (first item):', JSON.stringify(data[0]));
        
        // Transform SERP API data format if needed
        let transformedData = [...data]; // Create a copy of the data
        
        try {
            if (data[0] && typeof data[0] === 'object') {
                // Check for common SERP API formats
                if ((data[0].location || data[0].geo_name) && (data[0].value !== undefined || data[0].extracted_value !== undefined)) {
                    console.log('Detected direct SERP API region format, transforming data');
                    transformedData = data.map(region => {
                        const regionValue = region.extracted_value !== undefined ? 
                            (typeof region.extracted_value === 'string' ? parseInt(region.extracted_value, 10) : region.extracted_value) :
                            (region.value !== undefined ? 
                                (typeof region.value === 'string' ? parseInt(region.value, 10) : region.value) : 0);
                                
                        return {
                            geoName: region.location || region.geo_name || 'Unknown',
                            values: {
                                [keyword]: isNaN(regionValue) ? 0 : regionValue
                            }
                        };
                    });
                }
            }
        } catch (transformError) {
            console.error('Error transforming regional data:', transformError);
            // Continue with original data if transformation fails
            transformedData = [...data];
        }
        
        // Extra validation for debugging
        console.log('After transformation - Regional data sample:', JSON.stringify(transformedData[0]));
        
        // Data validation - ensure all values are valid
        let processedData = [];
        
        try {
            processedData = transformedData.map(region => {
                // Make a copy to avoid modifying original data
                const processedRegion = {...region};
                
                // Ensure region has a geoName property
                if (!processedRegion.geoName) {
                    if (processedRegion.location) {
                        processedRegion.geoName = processedRegion.location;
                    } else if (processedRegion.geo_name) {
                        processedRegion.geoName = processedRegion.geo_name;
                    } else if (processedRegion.name) {
                        processedRegion.geoName = processedRegion.name;
                    } else {
                        processedRegion.geoName = 'Unknown Region';
                    }
                }
                
                // Ensure values object exists
                if (!processedRegion.values || typeof processedRegion.values !== 'object') {
                    processedRegion.values = {};
                    
                    // Try to get values from direct properties
                    if (processedRegion.extracted_value !== undefined) {
                        const value = processedRegion.extracted_value;
                        processedRegion.values[keyword] = typeof value === 'string' ? parseInt(value, 10) : value;
                    } else if (processedRegion.value !== undefined) {
                        const value = processedRegion.value;
                        processedRegion.values[keyword] = typeof value === 'string' ? parseInt(value, 10) : value;
                    } else {
                        processedRegion.values[keyword] = 0; // Set to 0 to indicate missing data
                    }
                }
                
                // If value is missing for this keyword, set to 0
                if (processedRegion.values[keyword] === undefined || processedRegion.values[keyword] === null) {
                    processedRegion.values[keyword] = 0;
                } else if (typeof processedRegion.values[keyword] !== 'number') {
                    // Convert string values to numbers
                    const numValue = parseFloat(processedRegion.values[keyword]);
                    processedRegion.values[keyword] = isNaN(numValue) ? 0 : numValue;
                }
                
                return processedRegion;
            });
        } catch (processingError) {
            console.error('Error processing region data:', processingError);
            showError('Error processing regional data: ' + processingError.message);
            return;
        }
        
        // Filter out invalid or zero-value regions
        const validData = processedData.filter(region => 
            region.geoName && 
            region.geoName !== 'Unknown Region' && 
            region.values && 
            region.values[keyword] !== undefined && 
            region.values[keyword] > 0
        );
        
        // If we have no valid data after filtering, show error
        if (validData.length === 0) {
            console.error('No regions with valid values found after processing');
            
            // Log the raw data for debugging
            console.log('Raw region data before filtering:', JSON.stringify(processedData.slice(0, 3)));
            
            showError('No valid regional data available. Please try a different search term or region.');
            return;
        }
        
        console.log(`Found ${validData.length} regions with valid values`);
        
        // Clear any existing chart
        try {
            if (window.regionChart) {
                // Check if it's a valid Chart.js instance
                if (typeof window.regionChart === 'object' && 
                    typeof window.regionChart.destroy === 'function') {
                    // Properly destroy the chart
                    window.regionChart.destroy();
                } else {
                    console.warn('Invalid Chart.js instance found in window.regionChart, recreating it');
                }
                window.regionChart = null;
            }
        } catch (destroyError) {
            console.error('Error destroying existing chart:', destroyError);
            // Continue anyway, we'll create a new chart
            window.regionChart = null;
        }
        
        // Get chart container
        const chartContainer = document.getElementById('regionChart');
        if (!chartContainer) {
            console.error('Region chart container not found');
            showError('Chart container not found on page.');
            return;
        }
        
        // Reset the canvas to ensure a clean state
        try {
            const parent = chartContainer.parentNode;
            if (parent) {
                // Store the original canvas
                const originalCanvas = chartContainer;
                const width = originalCanvas.width || 300;
                const height = originalCanvas.height || 200;
                const classNames = originalCanvas.className || '';
                const id = originalCanvas.id;
                
                // Create a replacement canvas with the same dimensions and ID
                const newCanvas = document.createElement('canvas');
                newCanvas.id = id;
                newCanvas.width = width;
                newCanvas.height = height;
                newCanvas.className = classNames;
                
                // Replace the old canvas with the new one
                parent.replaceChild(newCanvas, originalCanvas);
                
                console.log('Canvas reset successfully');
            }
        } catch (canvasError) {
            console.error('Error resetting canvas:', canvasError);
            // Not fatal, continue with existing canvas
        }
        
        // Re-get the chart container since we might have replaced it
        const refreshedChartContainer = document.getElementById('regionChart');
        
        try {
            // Store original data for sorting/filtering
            window.originalRegionData = validData.slice();
            
            // Process the data for visualization - limit to top 10 by default
            const chartData = processRegionalDataSafe(validData, keyword, 10, 'value');
            
            console.log('Processed data for chart:', chartData);
            
            // Validate processed data
            if (!chartData.labels || !chartData.values || chartData.labels.length === 0) {
                console.error('Processed data is invalid:', chartData);
                showError('Failed to process regional data for chart visualization.');
                return;
            }
            
            // Create beautiful colors for the bars
            const ctx = refreshedChartContainer.getContext('2d');
            
            // Create a gradient for each bar
            const createGradient = (ctx, index, total) => {
                // Create a range of beautiful colors with different hues
                const baseHue = 25; // Orange base
                const hueRange = 180; // Range of colors
                const hue = baseHue + (index / total) * hueRange;
                
                const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                gradient.addColorStop(0, `hsla(${hue}, 85%, 60%, 0.8)`);
                gradient.addColorStop(1, `hsla(${hue}, 85%, 75%, 0.4)`);
                return gradient;
            };
            
            // Create datasets with beautiful gradients
            const backgroundColors = chartData.labels.map((_, i) => 
                createGradient(ctx, i, chartData.labels.length)
            );
            
            // Create the chart configuration
            const config = {
                type: 'bar',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: keyword,
                        data: chartData.values,
                        backgroundColor: backgroundColors,
                        borderColor: backgroundColors.map(c => c.replace('0.4', '0.9')),
                        borderWidth: 1,
                        borderRadius: 4,
                        barThickness: 'flex',
                        barPercentage: 0.8,
                        minBarLength: 5
                    }]
                },
                options: {
                    indexAxis: 'y', // Horizontal bar chart
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: {
                            top: 10,
                            right: 25,
                            bottom: 10,
                            left: 10
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                display: false
                            },
                            ticks: {
                                font: {
                                    size: 12
                                },
                                // Truncate long region names
                                callback: function(value) {
                                    if (value < 0 || value >= chartData.labels.length) {
                                        return '';
                                    }
                                    const label = chartData.labels[value];
                                    if (label && typeof label === 'string' && label.length > 18) {
                                        return label.substr(0, 15) + '...';
                                    }
                                    return label || '';
                                }
                            }
                        },
                        x: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                font: {
                                    size: 12
                                }
                            },
                            title: {
                                display: true,
                                text: 'Search Interest',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: `Regional Interest for "${keyword}"`,
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 15
                            }
                        },
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {
                                size: 14,
                                weight: 'bold'
                            },
                            bodyFont: {
                                size: 13
                            },
                            padding: 12,
                            cornerRadius: 6,
                            callbacks: {
                                label: function(context) {
                                    return `Search interest: ${context.parsed.x}`;
                                }
                            }
                        },
                        customCanvasBackgroundColor: {
                            color: 'rgba(255, 255, 255, 1)',
                            gradient: {
                                start: 'rgba(255, 249, 240, 1)', // Light orange tint
                                end: 'rgba(255, 255, 255, 1)'
                            }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeOutQuart'
                    }
                }
            };
            
            // Create and render the chart
            try {
                window.regionChart = new Chart(refreshedChartContainer, config);
                console.log('Regional chart rendered successfully');
                
                // Show the region chart container
                const regionChartContainer = document.getElementById('regionChartContainer');
                if (regionChartContainer) {
                    regionChartContainer.style.display = 'block';
                }
                
                // Hide any error messages
                hideError();
                
                // Add event listeners for sorting buttons
                setupRegionalChartControls(keyword);
            } catch (chartError) {
                console.error('Error creating Chart.js instance:', chartError);
                showError('Error creating chart: ' + (chartError.message || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('Error in chart preparation:', error);
            showError('Error preparing regional chart: ' + error.message);
        }
    } catch (outerError) {
        console.error('Outer error in renderRegionalChart:', outerError);
        showError('Error rendering regional chart: ' + outerError.message);
    }
}

// A safer version of processRegionalData with additional error handling
function processRegionalDataSafe(data, keyword, limit = 10, sortBy = 'value') {
    try {
        // Check for empty or invalid data
        if (!data || !Array.isArray(data) || data.length === 0) {
            console.error('Invalid or empty region data');
            // Return minimal structure so chart rendering doesn't fail
            return {
                labels: ['No Data Available'],
                values: [0]
            };
        }
        
        // Extract labels and values directly, with validation
        const labels = [];
        const values = [];
        
        // First pass: extract valid regions
        for (let i = 0; i < data.length; i++) {
            const region = data[i];
            
            if (!region || typeof region !== 'object') continue;
            
            // Get region name
            let regionName = region.geoName;
            if (!regionName && region.location) regionName = region.location;
            if (!regionName && region.geo_name) regionName = region.geo_name;
            if (!regionName && region.name) regionName = region.name;
            
            // Skip if no valid name
            if (!regionName || regionName === 'Unknown Region') continue;
            
            // Get value
            let value = 0;
            if (region.values && region.values[keyword] !== undefined) {
                value = parseFloat(region.values[keyword]);
            } else if (region.value !== undefined) {
                value = parseFloat(region.value);
            } else if (region.extracted_value !== undefined) {
                value = parseFloat(region.extracted_value);
            }
            
            // Skip if value is not valid or zero
            if (isNaN(value) || value <= 0) continue;
            
            // Add to our arrays
            labels.push(regionName);
            values.push(value);
        }
        
        // If no valid data, return placeholder
        if (labels.length === 0) {
            return {
                labels: ['No Data Available'],
                values: [0]
            };
        }
        
        // Sort entries
        const combined = labels.map((label, index) => ({
            label,
            value: values[index]
        }));
        
        if (sortBy === 'value') {
            combined.sort((a, b) => b.value - a.value);
        } else if (sortBy === 'name') {
            combined.sort((a, b) => a.label.localeCompare(b.label));
        }
        
        // Apply limit
        const limitedCombined = (limit !== 'all' && !isNaN(parseInt(limit))) 
            ? combined.slice(0, parseInt(limit)) 
            : combined;
        
        // Extract sorted and limited labels/values
        const sortedLabels = limitedCombined.map(item => item.label);
        const sortedValues = limitedCombined.map(item => item.value);
        
        console.log(`Processed ${sortedLabels.length} regions with values for "${keyword}"`);
        
        return {
            labels: sortedLabels,
            values: sortedValues
        };
    } catch (error) {
        console.error('Error in processRegionalDataSafe:', error);
        return {
            labels: ['Error Processing Data'],
            values: [0]
        };
    }
}

// Function to set up event listeners for regional chart controls
function setupRegionalChartControls(keyword) {
    // Sort buttons
    const sortByValueBtn = document.getElementById('sortByValueBtn');
    const sortByNameBtn = document.getElementById('sortByNameBtn');
    
    // Region limit select
    const regionLimitSelect = document.getElementById('regionLimitSelect');
    
    // Store current settings
    window.regionChartSettings = {
        sortBy: 'value',
        limit: 10
    };
    
    // Add click event listeners to sort buttons
    if (sortByValueBtn) {
        sortByValueBtn.addEventListener('click', () => {
            // Update the button styles
            sortByValueBtn.classList.add('bg-[#FF9F40]/20', 'border-[#FF9F40]');
            if (sortByNameBtn) sortByNameBtn.classList.remove('bg-[#FF9F40]/20', 'border-[#FF9F40]');
            
            // Update settings
            window.regionChartSettings.sortBy = 'value';
            
            // Redraw the chart
            updateRegionalChart(keyword);
        });
    }
    
    if (sortByNameBtn) {
        sortByNameBtn.addEventListener('click', () => {
            // Update the button styles
            sortByNameBtn.classList.add('bg-[#FF9F40]/20', 'border-[#FF9F40]');
            if (sortByValueBtn) sortByValueBtn.classList.remove('bg-[#FF9F40]/20', 'border-[#FF9F40]');
            
            // Update settings
            window.regionChartSettings.sortBy = 'name';
            
            // Redraw the chart
            updateRegionalChart(keyword);
        });
    }
    
    // Add change event listener to limit select
    if (regionLimitSelect) {
        regionLimitSelect.addEventListener('change', () => {
            // Update settings
            window.regionChartSettings.limit = regionLimitSelect.value;
            
            // Redraw the chart
            updateRegionalChart(keyword);
        });
    }
}

// Function to update the regional chart based on current settings
function updateRegionalChart(keyword) {
    if (!window.originalRegionData || !window.regionChartSettings) {
        console.error('Original region data or chart settings not available');
        return;
    }
    
    // Get current settings
    const { sortBy, limit } = window.regionChartSettings;
    
    // Process data with new settings
    const processedData = processRegionalData(window.originalRegionData, keyword, limit, sortBy);
    
    // Update the chart
    if (window.regionChart) {
        window.regionChart.data.labels = processedData.labels;
        window.regionChart.data.datasets[0].data = processedData.values;
        
        // Update the background colors for the bars
        const ctx = document.getElementById('regionChart').getContext('2d');
        const createGradient = (ctx, index, total) => {
            const baseHue = 25; // Orange base
            const hueRange = 180; // Range of colors
            const hue = baseHue + (index / total) * hueRange;
            
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, `hsla(${hue}, 85%, 60%, 0.8)`);
            gradient.addColorStop(1, `hsla(${hue}, 85%, 75%, 0.4)`);
            return gradient;
        };
        
        const backgroundColors = processedData.labels.map((_, i) => 
            createGradient(ctx, i, processedData.labels.length)
        );
        
        window.regionChart.data.datasets[0].backgroundColor = backgroundColors;
        window.regionChart.data.datasets[0].borderColor = backgroundColors.map(c => c.replace('0.4', '0.9'));
        
        window.regionChart.update();
        console.log('Regional chart updated successfully');
    }
}

// Make the renderRegionalChart function available globally
window.renderRegionalChart = renderRegionalChart;
window.processRegionalData = processRegionalData;
window.updateRegionalChart = updateRegionalChart;

// --------- Helper Functions ---------
    
// Enhanced safe JSON parse function
function safeJSONParse(text) {
    if (!text) return null;
    
    try {
        // Try standard parsing first
        return JSON.parse(text);
    } catch (error) {
        console.warn('Standard JSON parse failed:', error.message);
        // If standard parsing fails, could implement more forgiving parse methods here
        return null;
    }
}

// Function to get a CSRF token from cookies
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

// Function to transform SERP API data to our standard format
function transformSerpApiData(data, keyword) {
    // If not SERP API data or already properly structured, return as is
    if (!data) return data;
    
    // Check if from SERP API either directly or as processed by backend
    const isDirectSerpApi = data.interest_over_time && data.interest_over_time.timeline_data;
    const isProcessedSerpApi = data.metadata && data.metadata.source === 'serp_api';
    const hasSerpSearchMetadata = data.search_metadata && data.search_metadata.google_trends_url;
    
    if (!isDirectSerpApi && !isProcessedSerpApi && !hasSerpSearchMetadata) {
        return data;
    }
    
    console.log('Transforming SERP API data');
    
    try {
        // Make a copy of the data to avoid modifying the original
        const transformedData = {...data};
        
        // Case 1: Raw SERP API response with search_metadata and search_parameters (direct from SERP API)
        if (hasSerpSearchMetadata) {
            console.log('Processing raw SERP API response with search_metadata');
            
            // Initialize data structure if needed
            if (!transformedData.data) {
                transformedData.data = {};
            }
            
            // Check for region data (interest_by_region)
            if (data.interest_by_region && Array.isArray(data.interest_by_region)) {
                console.log('Found interest_by_region data:', data.interest_by_region.length);
                
                // Transform to our expected format
                const regionData = data.interest_by_region.map(region => {
                    // Get the location/region name
                    const regionName = region.location || region.geo_name || region.name || 'Unknown';
                    
                    // Get the value - try extracted_value first, then value
                    let regionValue = null;
                    if (region.extracted_value !== undefined) {
                        regionValue = typeof region.extracted_value === 'string' ? 
                            parseInt(region.extracted_value, 10) : 
                            region.extracted_value;
                    } else if (region.value !== undefined) {
                        regionValue = typeof region.value === 'string' ? 
                            parseInt(region.value, 10) : 
                            region.value;
                    }
                    
                    return {
                        geoName: regionName,
                        values: {
                            [keyword]: regionValue
                        }
                    };
                });
                
                // Filter out any regions with undefined or null values
                const validRegionData = regionData.filter(r => r.values[keyword] !== null && r.values[keyword] !== undefined);
                
                transformedData.data.region_data = validRegionData;
                console.log(`Processed ${validRegionData.length} regions`);
            }
            
            // Add metadata if missing
            if (!transformedData.metadata) {
                transformedData.metadata = {
                    keywords: [keyword],
                    source: 'serp_api'
                };
            }
            
            // Initialize empty arrays for other types of data
            if (!transformedData.data.time_trends) transformedData.data.time_trends = [];
            if (!transformedData.data.city_data) transformedData.data.city_data = [];
            if (!transformedData.data.related_queries) transformedData.data.related_queries = {};
            
            transformedData.status = 'success';
        }
        // Case 2: Direct SERP API data (interest_over_time format)
        else if (isDirectSerpApi) {
            console.log('Processing raw SERP API format with interest_over_time');
            
            // Transform to our expected format
            const timeData = data.interest_over_time.timeline_data.map(point => {
                const valueObj = point.values.find(v => v.query === keyword) || point.values[0];
                return {
                    date: point.date,
                    timestamp: point.timestamp,
                    [keyword]: valueObj ? (valueObj.extracted_value || parseInt(valueObj.value, 10)) : 0
                };
            });
            
            // Create our standard data structure
            transformedData.data = {
                time_trends: timeData
            };
            
            // Process region data if available
            if (data.interest_by_region && Array.isArray(data.interest_by_region)) {
                console.log('Found interest_by_region data in direct SERP API format');
                
                // Transform to our expected format
                const regionData = data.interest_by_region.map(region => {
                    // Get the location/region name
                    const regionName = region.location || region.geo_name || region.name || 'Unknown';
                    
                    // Get the value - try extracted_value first, then value
                    let regionValue = null;
                    if (region.extracted_value !== undefined) {
                        regionValue = typeof region.extracted_value === 'string' ? 
                            parseInt(region.extracted_value, 10) : 
                            region.extracted_value;
                    } else if (region.value !== undefined) {
                        regionValue = typeof region.value === 'string' ? 
                            parseInt(region.value, 10) : 
                            region.value;
                    }
                    
                    return {
                        geoName: regionName,
                        values: {
                            [keyword]: regionValue
                        }
                    };
                });
                
                transformedData.data.region_data = regionData.filter(r => 
                    r.values[keyword] !== null && r.values[keyword] !== undefined);
                
                console.log(`Processed ${transformedData.data.region_data.length} regions from interest_by_region`);
            }
            
            // Add metadata if missing
            if (!transformedData.metadata) {
                transformedData.metadata = {
                    keywords: [keyword],
                    source: 'serp_api'
                };
            }
            
            // Add other data sections if they don't exist
            if (!transformedData.data.region_data) transformedData.data.region_data = [];
            if (!transformedData.data.city_data) transformedData.data.city_data = [];
            if (!transformedData.data.related_queries) transformedData.data.related_queries = {};
        }
        // Case 3: SERP API data already processed by backend
        else if (isProcessedSerpApi && data.data) {
            console.log('Processing backend-formatted SERP API data');
            
            // Data is already in the right structure, just ensure all values are numbers
            if (data.data.time_trends && Array.isArray(data.data.time_trends)) {
                transformedData.data.time_trends = data.data.time_trends.map(point => {
                    const result = {...point};
                    
                    // Ensure the value is a number
                    if (result.value !== undefined) {
                        result.value = typeof result.value === 'string' ? parseInt(result.value, 10) : result.value;
                    }
                    
                    // Ensure keyword value is a number if present
                    if (result[keyword] !== undefined) {
                        result[keyword] = typeof result[keyword] === 'string' ? parseInt(result[keyword], 10) : result[keyword];
                    }
                    
                    return result;
                });
            }
            
            // Ensure region data is properly formatted
            if (data.data.region_data && Array.isArray(data.data.region_data)) {
                // No need to transform, the backend should have done this already
                // Just verify the structure for debugging
                console.log(`Found ${data.data.region_data.length} regions from backend-processed SERP API data`);
            }
        }
        
        return transformedData;
    } catch (error) {
        console.error('Error transforming SERP API data:', error);
        return data; // Return original data if transformation fails
    }
}

// Function to process raw SERP API data for direct chart rendering
function processSerpApiData(data, keyword) {
    console.log('Processing SERP API data for direct chart rendering');
    
    try {
        // Check for various possible data structures
        let timelineData = null;
        
        // 1. Check for data.interest_over_time.timeline_data (standard SERP API format)
        if (data && data.interest_over_time && data.interest_over_time.timeline_data) {
            console.log('Found standard SERP API timeline_data structure');
            timelineData = data.interest_over_time.timeline_data;
        }
        // 2. Check for data.timeline_data (sometimes the response is flattened)
        else if (data && data.timeline_data) {
            console.log('Found flattened SERP API timeline_data structure');
            timelineData = data.timeline_data;
        }
        // 3. Check if data itself is the timeline array
        else if (Array.isArray(data)) {
            console.log('Data itself appears to be an array of timeline data');
            timelineData = data;
        }
        
        // If we couldn't find the timeline data, return empty array
        if (!timelineData || !Array.isArray(timelineData)) {
            console.error('Could not locate timeline data in SERP API response');
            console.log('Available data:', data);
            return [];
        }
        
        // Now convert the timeline data to chart-compatible format
        const chartData = timelineData.map((point, index) => {
            // Default values
            let dateValue = null;
            let dataValue = 0;
            
            // Extract date
            if (point.timestamp) {
                // Use timestamp for precise dating (convert seconds to milliseconds)
                const timestamp = parseInt(point.timestamp, 10) * 1000;
                dateValue = new Date(timestamp);
            } else if (point.date) {
                // Try to parse the date string which might be in format "May 19–25, 2024"
                try {
                    const dateStr = point.date;
                    
                    // Extract month, year and first day if available
                    const parts = dateStr.split(/[\s\u2009–-]+/); // Split by spaces, en-dashes, etc.
                    const monthMatch = dateStr.match(/([A-Za-z]{3,})/); // Match month name
                    const yearMatch = dateStr.match(/\d{4}/);  // Match 4-digit year
                    
                    if (monthMatch && yearMatch) {
                        const month = monthMatch[1];
                        const year = yearMatch[0];
                        
                        // Look for first day number
                        let day = '1';
                        for (const part of parts) {
                            if (/^\d{1,2}$/.test(part)) { // If part is 1-2 digit number
                                day = part;
                                break;
                            }
                        }
                        
                        // Create date from parts
                        dateValue = new Date(`${month} ${day}, ${year}`);
                    }
                } catch (e) {
                    console.warn('Error parsing date string:', e);
                }
                
                // If date parsing failed, create sequential date
                if (!dateValue || isNaN(dateValue.getTime())) {
                    dateValue = new Date();
                    dateValue.setDate(dateValue.getDate() - (timelineData.length - index));
                }
            } else {
                // If no date info, create sequential date
                dateValue = new Date();
                dateValue.setDate(dateValue.getDate() - (timelineData.length - index));
            }
            
            // Extract value
            if (point.values && Array.isArray(point.values) && point.values.length > 0) {
                // Find value for specific query/keyword or use first
                const valueObj = point.values.find(v => v.query === keyword) || point.values[0];
                if (valueObj) {
                    dataValue = valueObj.extracted_value !== undefined ? 
                                valueObj.extracted_value : 
                                (valueObj.value !== undefined ? 
                                 (typeof valueObj.value === 'string' ? parseInt(valueObj.value, 10) : valueObj.value) 
                                 : 0);
                }
            } else if (point.value !== undefined) {
                // Direct value property
                dataValue = typeof point.value === 'string' ? parseInt(point.value, 10) : point.value;
            }
            
            // Return data point in expected format for the chart
            return {
                date: dateValue,
                [keyword]: dataValue
            };
        });
        
        return chartData;
    } catch (error) {
        console.error('Error processing SERP API data:', error);
        return []; // Return empty array on error
    }
}

// Function to show an error message
function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    
    if (errorContainer && errorMessage) {
        // Format the error message more nicely
        if (message.includes('proxies') || message.includes('proxy')) {
            message = 'Error: Unable to connect to Google Trends API. The proxy connection failed. Please try again later.';
        } else if (message.includes('data not found') || message.includes('No data') || message.includes('empty data')) {
            message = 'Error: Google Trends did not return any data for this query. Please try a different search term or time period.';
        }
        
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        
        // Scroll to error container to ensure it's visible
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
        console.error('Error:', message);
        // Fallback if container not found
        alert('Error: ' + message);
    }
}

// Function to hide error message
function hideError() {
    const errorContainer = document.getElementById('errorContainer');
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
}

// Function to calculate moving average
function calculateMovingAverage(data, windowSize = 7) {
    if (!Array.isArray(data) || data.length < windowSize) {
        return [];
    }
    
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < windowSize - 1) {
            result.push(null); // Not enough data for the first few points
        } else {
            // Calculate average of windowSize items ending at i
            const window = data.slice(i - windowSize + 1, i + 1);
            const sum = window.reduce((a, b) => a + b, 0);
            result.push(sum / windowSize);
        }
    }
    
    return result;
}

// Function to calculate a simple trend line
function calculateTrendLine(data) {
    if (!Array.isArray(data) || data.length <= 1) {
        return [];
    }
    
    // Calculate the slope and intercept using linear regression
    const n = data.length;
    const sum_x = n * (n - 1) / 2; // Sum of indices: 0 + 1 + ... + (n-1)
    const sum_y = data.reduce((a, b) => a + b, 0);
    const sum_xy = data.reduce((sum, y, i) => sum + i * y, 0);
    const sum_xx = n * (n - 1) * (2 * n - 1) / 6; // Sum of i^2 for i = 0...(n-1)
    
    const slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x);
    const intercept = (sum_y - slope * sum_x) / n;
    
    // Generate the trend line points
    return data.map((_, i) => intercept + slope * i);
}

// ... existing code ...
async function handleFormSubmit(e) {
    // ... existing code ...
    
    try {
        // ... existing code ...
        
        // Determine which chart to show based on analysis type
        if (analysisType === '2') { // Regional Analysis
            console.log('Selected Regional Analysis');
            
            // Hide time chart, show region chart
            if (timeChartContainer) {
                timeChartContainer.style.display = 'none';
            }
            
            // Make sure any existing chart is destroyed
            try {
                if (window.regionChart) {
                    if (typeof window.regionChart === 'object' && 
                        typeof window.regionChart.destroy === 'function') {
                        window.regionChart.destroy();
                    }
                    window.regionChart = null;
                }
            } catch (chartError) {
                console.error('Error cleaning up existing chart:', chartError);
                window.regionChart = null;
            }
            
            // For regional analysis, ensure we have the region_data from the response
            let regionData = null;
            
            // Check different possible formats of regional data
            if (data.interest_by_region && Array.isArray(data.interest_by_region)) {
                console.log('Found direct SERP API interest_by_region format');
                regionData = data.interest_by_region;
            } else if (data.data && data.data.region_data && Array.isArray(data.data.region_data)) {
                console.log('Found nested region_data array');
                regionData = data.data.region_data;
            }
            
            // Make a copy of the raw data for debugging
            window.rawRegionalData = JSON.parse(JSON.stringify(data));
            
            if (regionData && regionData.length > 0) {
                console.log(`Rendering regional chart with ${regionData.length} regions`);
                try {
                    renderRegionalChart(regionData, keyword);
                } catch (renderError) {
                    console.error('Error rendering regional chart with provided data:', renderError);
                    
                    // Try again with SERP API fallback
                    console.log('Attempting to fetch from SERP API as fallback...');
                    tryFetchSerpApiRegionalData(keyword, timeframe, geo);
                }
            } else {
                console.log('No regional data found in the response, attempting to fetch from SERP API');
                tryFetchSerpApiRegionalData(keyword, timeframe, geo);
            }
        }
        
        // ... existing code ...
    } catch (error) {
        // ... existing code ...
    }
    
    // Helper function to fetch regional data from SERP API
    async function tryFetchSerpApiRegionalData(keyword, timeframe, geo) {
        try {
            // Make sure any existing chart is destroyed
            try {
                if (window.regionChart) {
                    if (typeof window.regionChart === 'object' && 
                        typeof window.regionChart.destroy === 'function') {
                        window.regionChart.destroy();
                    }
                    window.regionChart = null;
                }
            } catch (chartError) {
                console.error('Error cleaning up existing chart before fetching new data:', chartError);
                window.regionChart = null;
            }
            
            // Show informative message
            showError('Fetching regional data from alternative source...');
            
            // Make a special request to get SERP API regional data
            fetch('/trends/api/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    keyword: keyword,
                    analysis_type: '2', // Force regional analysis
                    timeframe: timeframe,
                    geo: geo,
                    use_serp_api: true // Request to use SERP API specifically
                })
            }).then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch from SERP API: ${response.status}`);
                }
                return response.json();
            }).then(serpData => {
                console.log('Received SERP API response:', serpData);
                
                // Save raw response for debugging
                window.rawSerpApiData = JSON.parse(JSON.stringify(serpData));
                
                // Look through all properties for potential regional data arrays
                let serpRegionData = null;
                const possibleDataKeys = Object.keys(serpData);
                
                for (const key of possibleDataKeys) {
                    // Check direct array
                    if (Array.isArray(serpData[key]) && serpData[key].length > 0) {
                        // Check first item to see if it looks like regional data
                        const firstItem = serpData[key][0];
                        if (firstItem && typeof firstItem === 'object' && 
                            (firstItem.location || firstItem.geo_name || 
                            (firstItem.values && typeof firstItem.values === 'object'))) {
                            console.log(`Found potential region data in serpData.${key}`);
                            serpRegionData = serpData[key];
                            break;
                        }
                    }
                    
                    // Check one level deeper
                    if (serpData[key] && typeof serpData[key] === 'object') {
                        const nestedKeys = Object.keys(serpData[key]);
                        for (const nestedKey of nestedKeys) {
                            if (Array.isArray(serpData[key][nestedKey]) && serpData[key][nestedKey].length > 0) {
                                const firstItem = serpData[key][nestedKey][0];
                                if (firstItem && typeof firstItem === 'object' && 
                                    (firstItem.location || firstItem.geo_name || 
                                    (firstItem.values && typeof firstItem.values === 'object'))) {
                                    console.log(`Found potential region data in serpData.${key}.${nestedKey}`);
                                    serpRegionData = serpData[key][nestedKey];
                                    break;
                                }
                            }
                        }
                        if (serpRegionData) break;
                    }
                }
                
                // Check specific formats that we know about
                if (!serpRegionData) {
                    // Try direct interest_by_region format
                    if (serpData.interest_by_region && Array.isArray(serpData.interest_by_region)) {
                        console.log('Found interest_by_region in SERP API response with length:', serpData.interest_by_region.length);
                        serpRegionData = serpData.interest_by_region;
                    } 
                    // Try nested data.region_data format
                    else if (serpData.data && serpData.data.region_data && 
                        Array.isArray(serpData.data.region_data) && 
                        serpData.data.region_data.length > 0) {
                        console.log('Found nested region_data in SERP API response with length:', serpData.data.region_data.length);
                        serpRegionData = serpData.data.region_data;
                    }
                }
                
                if (serpRegionData && serpRegionData.length > 0) {
                    // Hide the error message
                    hideError();
                    
                    try {
                        // Render with SERP API data
                        renderRegionalChart(serpRegionData, keyword);
                    } catch (renderError) {
                        console.error('Error rendering regional chart with SERP API data:', renderError, renderError.stack);
                        showError('Error rendering regional chart. Please try a different search term.');
                    }
                } else {
                    throw new Error('SERP API returned data without valid regional information');
                }
            }).catch(error => {
                console.error('Failed to get regional data from SERP API:', error);
                showError('No regional data available. Please try a different search term or region.');
            });
        } catch (outerError) {
            console.error('Outer error in tryFetchSerpApiRegionalData:', outerError);
            showError('Error fetching regional data: ' + outerError.message);
        }
    }
}
// ... existing code ...