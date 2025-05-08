// Trends Chart Rendering and Google AI Integration

// Create global variables to check if functions are loaded
window.trendsChartsLoaded = false;
window.isTrendsChartsLoaded = function() {
    return window.trendsChartsLoaded === true && typeof window.renderCharts === 'function';
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded - initializing trends charts');
    
    // Get form and button elements
    const trendsForm = document.getElementById('trendsForm');
    const analyzeButton = document.getElementById('analyzeButton');
    const keywordInput = document.getElementById('keywordInput');
    const timeframeSelect = document.getElementById('timeframeSelect');
    const regionSelect = document.getElementById('regionSelect');
    const analysisTypeSelect = document.getElementById('analysisTypeSelect');
    
    // Add event listeners
    if (trendsForm) {
        console.log('Adding submit listener to form');
        trendsForm.addEventListener('submit', handleFormSubmit);
    } else {
        console.warn('Trends form not found');
    }
    
    // Add direct click event listener to analyze button if it exists
    if (analyzeButton) {
        console.log('Adding click listener to analyze button');
        analyzeButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent default button behavior
            console.log('Analyze button clicked');
            handleFormSubmit(e);
        });
    } else {
        console.warn('Analyze button not found');
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
        
        // Try different selectors for analysis type
        if (analysisTypeSelect) {
            analysisType = analysisTypeSelect.value;
        } else if (document.getElementById('analysisOption')) {
            analysisType = document.getElementById('analysisOption').value;
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
        const chartsContainer = document.getElementById('chartsContainer');
        
        // Hide error and charts, show loading
        if (errorContainer) errorContainer.style.display = 'none';
        if (chartsContainer) chartsContainer.style.display = 'none';
        if (loadingIndicator) {
            loadingIndicator.style.display = 'flex'; // Use flex to center content
            console.log('Showing loading indicator');
        }
        
        try {
            console.log('Making API request with:', { keyword, analysisType, timeframe, geo });
            
            // Make API request
            const response = await fetch('/trends/api/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    keyword: keyword,
                    analysis_type: analysisType,
                    timeframe: timeframe,
                    geo: geo
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received API response:', data);
            
            if (data.status === 'error') {
                throw new Error(data.message || 'Failed to fetch trends data');
            }
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
                console.log('Hiding loading indicator');
            }
            
            // Show charts container
            if (chartsContainer) {
                chartsContainer.style.display = 'flex';
                console.log('Showing charts container');
            }
            
            // Store the data globally for debugging and reuse
            window.trendsData = data.data || data;
            window.lastFetchedKeyword = keyword;
            
            console.log('Analysis Type:', analysisType);
            
            // For "Trends Only" format (analysis_type=1), handling might be different
            if (analysisType === '1') {
                console.log('Using Trends Only data format');
                
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
                renderCharts(chartData || data, keyword);
            } else {
                // Standard data format
                renderCharts(data.data || data, keyword);
            }
        } catch (error) {
            console.error('Error fetching trends data:', error);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
                console.log('Hiding loading indicator due to error');
            }
            
            // Show error message
            const errorMessage = document.getElementById('errorMessage');
            if (errorMessage) {
                errorMessage.textContent = error.message || 'An error occurred while fetching trends data';
                if (errorContainer) {
                    errorContainer.style.display = 'block';
                    console.log('Showing error container with message:', errorMessage.textContent);
                }
            }
            
            // Hide charts container
            if (chartsContainer) chartsContainer.style.display = 'none';
        }
    }
    
    // Global variables
    let trendsData = null;
    let dataAlreadyFetched = false;
    let lastFetchedKeyword = '';
    let timeChart = null;
    let stateChart = null;
    let cityChart = null;
    let currentTimeUnit = 'month'; // Default time unit
    let currentFetchController = null; // For fetch abort control
    
    // Make key variables available globally
    window.currentTimeUnit = currentTimeUnit;
    window.trendsData = trendsData;
    window.lastFetchedKeyword = lastFetchedKeyword;
    window.timeChart = timeChart;
    window.currentFetchController = currentFetchController;
    
    const googleApiConfigured = window.googleApiConfigured || false;
    
    // Debug logging
    console.log('Trends charts JS loaded');
    console.log('Google API configured:', googleApiConfigured);
    
    // Set the trendsChartsLoaded flag to true
    window.trendsChartsLoaded = true;
    
    // Initialize other features if needed
    if (typeof initializeAutoSearch === 'function') {
        initializeAutoSearch();
    }
    
    // Function to update the time unit for the time series chart
    function updateTimeUnit(unit) {
        console.log('Updating time unit to:', unit);
        
        if (!window.timeChart) {
            console.error('Time chart not found');
            return;
        }
        
        // Update current time unit
        window.currentTimeUnit = unit;
        
        // Check if the chart is using time scale
        if (window.timeChart.options.scales.x && window.timeChart.options.scales.x.type === 'time') {
            // Update the time unit
            window.timeChart.options.scales.x.time.unit = unit;
            window.timeChart.update();
        } else {
            console.warn('Chart is not using time scale, cannot update time unit');
        }
    }
    
    // Make the updateTimeUnit function available globally
    window.updateTimeUnit = updateTimeUnit;
    
    // Debug logging
    console.log('Trends charts JS loaded');
    console.log('Google API configured:', googleApiConfigured);
});

// --------- Helper Functions ---------
    
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
                    time_trends: []
                    }
                };
            }
        }
    }
    
// --------- Cookie Management ---------
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

// --------- Error Handling ---------
function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    
    if (errorContainer && errorMessage) {
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        errorContainer.classList.add('fade-in');
        } else {
        console.error('Error:', message);
    }
}

function hideError() {
    const errorContainer = document.getElementById('errorContainer');
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
}

// --------- Chart Functions ---------
function clearCharts() {
    const chartContainers = ['timeSeriesChartContainer', 'regionChartContainer', 'cityChartContainer'];
    
    // Destroy existing chart instances
    if (window.timeChart) {
        window.timeChart.destroy();
        window.timeChart = null;
    }
    
    // Hide all chart containers initially
    chartContainers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'none';
        }
    });
}

// --------- Data Processing Functions ---------
function calculateMovingAverage(data, windowSize = 7) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - Math.floor(windowSize / 2));
        const end = Math.min(data.length, i + Math.floor(windowSize / 2) + 1);
        const windowData = data.slice(start, end);
        const sum = windowData.reduce((acc, val) => acc + val, 0);
        result.push(sum / windowData.length);
    }
    return result;
}

function calculateTrendLine(data) {
    const n = data.length;
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;
    
    for (let i = 0; i < n; i++) {
        sumX += i;
        sumY += data[i];
        sumXY += i * data[i];
        sumXX += i * i;
    }
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    
    return Array.from({ length: n }, (_, i) => slope * i + intercept);
}

// --------- Chart Rendering Functions ---------
function renderTimeSeriesChart(timeSeriesData, keyword) {
    console.log('Rendering time series chart with data length:', timeSeriesData.length);
    console.log('Using keyword:', keyword);
    
    if (!timeSeriesData || timeSeriesData.length === 0) {
        console.error('No time series data available');
        showError('No time series data available to display');
        return null;
    }
    
    if (!keyword) {
        console.error('No keyword provided for chart rendering');
        showError('Missing keyword for chart rendering');
        return null;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js library is not loaded!');
        showError('Chart.js library is not available. Please refresh the page and try again.');
        return null;
    }
    
    const ctx = document.getElementById('timeSeriesChart');
    if (!ctx) {
        console.error('Chart canvas element "timeSeriesChart" not found');
        showError('Chart canvas element not found');
        return null;
    }
    
    const container = document.getElementById('timeSeriesChartContainer');
    if (!container) {
        console.error('Chart container element "timeSeriesChartContainer" not found');
        showError('Chart container element not found');
        return null;
    }
    
    // Show the container
    container.style.display = 'block';
    
    // Process the data
    const dates = [];
    const values = [];
    
    // Log the first data point to help with debugging
    if (timeSeriesData.length > 0) {
        console.log('First data point sample:', JSON.stringify(timeSeriesData[0]));
        
        // Check the first item to ensure we understand the data format
        const firstPoint = timeSeriesData[0];
        if (firstPoint[keyword] !== undefined) {
            console.log(`Data format contains keyword property "${keyword}". Using Trends Only format.`);
        } else if (firstPoint.value !== undefined) {
            console.log('Data format contains generic "value" property. Using standard format.');
        } else {
            console.warn('Could not identify data format. Data may not be displayed correctly.');
            // Log all properties in the first point to help diagnose the issue
            console.log('Properties in first data point:', Object.keys(firstPoint));
        }
    }
    
    timeSeriesData.forEach((point, index) => {
        // Handle both data formats - standard format and "Trends Only" format
        if (point.date) {
            try {
                // Parse date safely
                const date = new Date(point.date);
                if (!isNaN(date.getTime())) {
                    dates.push(date);
                    
                    // Check if data is in the format { date: "2020-05-03", BJP: 4, isPartial: false }
                    if (point[keyword] !== undefined) {
                        // "Trends Only" format where keyword is a property
                        const value = parseFloat(point[keyword]);
                        if (!isNaN(value)) {
                            values.push(value);
                        } else {
                            console.warn(`Invalid value for keyword "${keyword}" at index ${index}:`, point[keyword]);
                            values.push(0); // Use 0 as fallback to maintain data point count
                        }
                    } else if (point.value !== undefined) {
                        // Standard format with a value property
                        const value = parseFloat(point.value);
                        if (!isNaN(value)) {
                            values.push(value);
                        } else {
                            console.warn(`Invalid value at index ${index}:`, point.value);
                            values.push(0); // Use 0 as fallback to maintain data point count
                        }
                    } else {
                        console.warn(`No value found for data point at index ${index}:`, point);
                        values.push(0); // Use 0 as fallback to maintain data point count
                    }
                } else {
                    console.warn(`Invalid date at index ${index}:`, point.date);
                }
            } catch (e) {
                console.error(`Error processing data point at index ${index}:`, e);
            }
        } else {
            console.warn(`No date found for data point at index ${index}:`, point);
        }
    });
    
    console.log(`Processed ${dates.length} data points with ${values.length} values`);
    
    if (values.length === 0) {
        console.error('No valid data points found for chart');
        showError('No valid data points found for time series chart');
        return null;
    }
    
    // Calculate moving average and trend line only if we have values
    const movingAverage = values.length > 0 ? calculateMovingAverage(values, 7) : [];
    const trendLine = values.length > 0 ? calculateTrendLine(values) : [];
    
    // Destroy previous chart if it exists
    if (window.timeChart) {
        try {
            window.timeChart.destroy();
        } catch (e) {
            console.error('Error destroying previous chart:', e);
        }
    }
    
    // Create new chart
    try {
        const chartConfig = {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: keyword,
                        data: values,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        borderWidth: 2,
                        pointRadius: 1,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.1
                    },
                    {
                        label: 'Moving Average (7-day)',
                        data: movingAverage,
                        borderColor: 'rgba(255, 159, 64, 0.8)',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        borderDash: [5, 5],
                        fill: false
                    },
                    {
                        label: 'Trend Line',
                        data: trendLine,
                        borderColor: 'rgba(255, 99, 132, 0.8)',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Interest Over Time for "${keyword}"`,
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(tooltipItems) {
                                const date = new Date(tooltipItems[0].parsed.x);
                                return date.toLocaleDateString(undefined, {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                });
                            }
                        }
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month',
                            displayFormats: {
                                month: 'MMM yyyy'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Search Interest (Relative)'
                        }
                    }
                }
            }
        };
        
        console.log('Creating new chart with config:', chartConfig);
        window.timeChart = new Chart(ctx.getContext('2d'), chartConfig);
        console.log('Chart created successfully!');
        
        // Make the container visible if it was hidden
        container.style.display = 'block';
        
        if (container.classList.contains('chart-container')) {
            container.classList.add('loaded');
        }
        
        // Ensure filter controls are visible
        const chartFilters = document.getElementById('chartFilters');
        if (chartFilters) {
            chartFilters.style.display = 'flex';
            console.log('Chart filters are now visible');
        } else {
            console.warn('Chart filters container not found');
        }
        
    } catch (e) {
        console.error('Error rendering time series chart:', e);
        console.error('Error details:', e.message);
        console.error('Stack trace:', e.stack);
        showError('Error rendering time series chart: ' + e.message);
    }
    
    return window.timeChart;
}

function renderRegionChart(regionData, keyword) {
    if (!regionData || regionData.length === 0) {
        return null;
    }
    
    const ctx = document.getElementById('regionChart').getContext('2d');
    const container = document.getElementById('regionChartContainer');
    
    // Show the container
    if (container) container.style.display = 'block';
    
    // Sort data and take top 10
    const sortedData = [...regionData].sort((a, b) => b.value - a.value).slice(0, 10);
    
    // Create the chart
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedData.map(item => item.name),
            datasets: [{
                label: 'Interest by Region',
                data: sortedData.map(item => item.value),
                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                title: {
                    display: true,
                    text: `Regional Interest for "${keyword}"`,
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Relative Interest'
                    }
                }
            }
        }
    });
}

function renderCityChart(cityData, keyword) {
    if (!cityData || cityData.length === 0) {
        return null;
    }
    
    const ctx = document.getElementById('cityChart').getContext('2d');
    const container = document.getElementById('cityChartContainer');
    
    // Show the container
    if (container) container.style.display = 'block';
    
    // Sort data and take top 10
    const sortedData = [...cityData].sort((a, b) => b.value - a.value).slice(0, 10);
    
    // Create the chart
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedData.map(item => item.name),
            datasets: [{
                label: 'Interest by City',
                data: sortedData.map(item => item.value),
                backgroundColor: 'rgba(153, 102, 255, 0.7)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                title: {
                    display: true,
                    text: `City-Level Interest for "${keyword}"`,
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Relative Interest'
                    }
                }
            }
        }
    });
}

// --------- Main Render Function ---------
function renderCharts(data, keyword) {
    console.log('Rendering charts with data:', data);
    console.log('Using keyword for chart:', keyword);
    
    // Clear existing charts
    clearCharts();
    
    // If data is empty or invalid, show error
    if (!data) {
        showError('No data available');
        return;
    }
    
    try {
        // For case when the entire response is the data array (no wrapper object)
        // This can happen with the Trends Only format
        if (Array.isArray(data)) {
            console.log('Detected array data format (likely Trends Only format)');
            // Verify that at least one item has the keyword property
            if (data.length > 0) {
                if (data[0][keyword] !== undefined) {
                    console.log('Confirmed Trends Only format with keyword property:', keyword);
                } else {
                    console.warn('Array data does not contain keyword property:', keyword);
                    console.log('Available properties:', Object.keys(data[0]).join(', '));
                }
                renderTimeSeriesChart(data, keyword);
            } else {
                console.error('Empty data array');
                showError('No data points available for analysis');
            }
            return;
        }
        
        // For case when the data is in data.data format
        if (data.data && Array.isArray(data.data)) {
            console.log('Data is wrapped in a data property');
            // If data.data is an array, it could be the Trends Only format
            if (data.data.length > 0) {
                if (data.data[0][keyword] !== undefined) {
                    console.log('Confirmed Trends Only format in data.data with keyword property:', keyword);
                    renderTimeSeriesChart(data.data, keyword);
                    return;
                }
            }
        }
        
        // For case when data.data contains structured data with time_trends, etc.
        const actualData = data.data || data; // Use data.data if available, otherwise use data
        
        // Render time series chart if data is available
        if (actualData.time_trends && actualData.time_trends.length > 0) {
            console.log('Rendering time series from time_trends array with length:', actualData.time_trends.length);
            renderTimeSeriesChart(actualData.time_trends, keyword);
        } else if (Array.isArray(actualData) && actualData.length > 0) {
            // As a fallback, if actualData is itself an array, try to use it
            console.log('Rendering time series from direct array data with length:', actualData.length);
            renderTimeSeriesChart(actualData, keyword);
        } else {
            console.warn('No valid time series data found');
            showError('No time series data available');
        }
        
        // Render region chart if data is available
        if (actualData.region_data && actualData.region_data.length > 0) {
            renderRegionChart(actualData.region_data, keyword);
        }
        
        // Render city chart if data is available
        if (actualData.city_data && actualData.city_data.length > 0) {
            renderCityChart(actualData.city_data, keyword);
        }
    } catch (e) {
        console.error('Error rendering charts:', e);
        console.error('Error details:', e.message);
        console.error('Stack trace:', e.stack);
        showError('Error rendering charts: ' + e.message);
    }
}

// End of basic chart functions

// ... the rest of the file remains unchanged ...
// ... the rest of the file remains unchanged ...