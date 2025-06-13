/**
 * Enhanced Charts Module for Business Analytics Dashboard
 * 
 * This module provides advanced visualization components using Chart.js
 */

// Initialize the enhanced charts module
document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced charts module initialized');
    
    // Make sure Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Enhanced visualizations will not work.');
        loadChartJsLibrary();
    } else {
        console.log('Chart.js detected and ready');
    }
    
    // Initialize any chart containers that should be visible by default
    initChartContainers();
});

/**
 * Attempts to load Chart.js dynamically if not already available
 */
function loadChartJsLibrary() {
    console.log('Attempting to load Chart.js dynamically');
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js';
    script.async = true;
    script.onload = function() {
        console.log('Chart.js loaded successfully');
        initChartContainers();
    };
    script.onerror = function() {
        console.error('Failed to load Chart.js. Enhanced visualizations will be disabled.');
    };
    document.head.appendChild(script);
}

/**
 * Initialize chart containers
 */
function initChartContainers() {
    console.log('Initializing chart containers...');
    
    // Get all chart containers
    const chartContainers = [
        'returnsVsCancellationsContainer',
        'salesTrendContainer',
        'salesChannelContainer',
        'salesByCategoryContainer',
        'topProductsContainer',
        'topRegionsContainer',
        'bottomProductsContainer',
        'bottomRegionsContainer',
        'highReturnsContainer',
        'topSellingStatesContainer',
        'topSellingProductsContainer'
    ];
    
    // Make sure all containers exist and are properly initialized
    chartContainers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            // Keep containers hidden until they have data
            container.classList.add('hidden');
            
            // Check if the container has a canvas element
            const containerDiv = container.querySelector('div');
            if (containerDiv) {
                const existingCanvas = containerDiv.querySelector('canvas');
                if (!existingCanvas) {
                    console.log(`Creating canvas for ${containerId}`);
                    // Create canvas element with appropriate ID based on container
                    const canvas = document.createElement('canvas');
                    
                    // Set appropriate ID for the canvas based on container ID
                    if (containerId === 'salesTrendContainer') {
                        canvas.id = 'dashboardSalesTrendChart';
                    } else if (containerId === 'salesChannelContainer') {
                        canvas.id = 'dashboardSalesChannelChart';
                    } else if (containerId === 'returnsVsCancellationsContainer') {
                        canvas.id = 'returnsVsCancellationsChart';
                    } else if (containerId === 'salesByCategoryContainer') {
                        canvas.id = 'salesByCategoryChart';
                    } else if (containerId === 'topSellingStatesContainer') {
                        canvas.id = 'topSellingStatesChart';
                    } else if (containerId === 'topSellingProductsContainer') {
                        canvas.id = 'topSellingProductsChart';
                    } else if (containerId === 'fallbackChartContainer') {
                        canvas.id = 'fallbackChart';
                    }
                    
                    // Only append if we set an ID
                    if (canvas.id) {
                        containerDiv.appendChild(canvas);
                        console.log(`Canvas ${canvas.id} created and appended to ${containerId}`);
                    }
                }
            }
            
            console.log(`Chart container ${containerId} initialized`);
        } else {
            console.warn(`Chart container ${containerId} not found in the DOM`);
        }
    });

    // Check for chart canvases
    const chartCanvases = [
        'dashboardSalesTrendChart',
        'dashboardSalesChannelChart',
        'returnsVsCancellationsChart',
        'salesByCategoryChart',
        'topSellingStatesChart',
        'topSellingProductsChart',
        'fallbackChart'
    ];

    chartCanvases.forEach(canvasId => {
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            console.log(`Chart canvas ${canvasId} is available`);
        } else {
            console.warn(`Chart canvas ${canvasId} not found in the DOM, this may cause rendering issues`);
            
            // Try to find the corresponding container to create the canvas
            let containerId = '';
            if (canvasId === 'dashboardSalesTrendChart') containerId = 'salesTrendContainer';
            else if (canvasId === 'dashboardSalesChannelChart') containerId = 'salesChannelContainer';
            else if (canvasId === 'returnsVsCancellationsChart') containerId = 'returnsVsCancellationsContainer';
            else if (canvasId === 'salesByCategoryChart') containerId = 'salesByCategoryContainer';
            else if (canvasId === 'topSellingStatesChart') containerId = 'topSellingStatesContainer';
            else if (canvasId === 'topSellingProductsChart') containerId = 'topSellingProductsContainer';
            else if (canvasId === 'fallbackChart') containerId = 'fallbackChartContainer';
            
            if (containerId) {
                const container = document.getElementById(containerId);
                if (container) {
                    const containerDiv = container.querySelector('div');
                    if (containerDiv) {
                        const newCanvas = document.createElement('canvas');
                        newCanvas.id = canvasId;
                        containerDiv.appendChild(newCanvas);
                        console.log(`Created missing canvas ${canvasId} in ${containerId}`);
                    }
                }
            }
        }
    });
    
    console.log('Chart containers initialization complete');
}

/**
 * Creates a Returns vs Cancellations chart
 */
function createReturnsVsCancellationsChart(metrics) {
    console.log('Creating Returns vs Cancellations chart with metrics:', metrics);
    
    // Verify we have the required metrics
    if (!metrics || metrics.return_rate === undefined || metrics.cancellation_rate === undefined) {
        console.warn('Missing required metrics for Returns vs Cancellations chart');
        return;
    }
    
    // Get the container and verify it exists
    const container = document.getElementById('returnsVsCancellationsContainer');
    if (!container) {
        console.error('Returns vs Cancellations container not found');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    
    // Get the canvas and verify it exists
    const canvas = document.getElementById('returnsVsCancellationsChart');
    if (!canvas) {
        console.error('Returns vs Cancellations canvas not found');
        // Try to create the canvas if it doesn't exist
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'returnsVsCancellationsChart';
        container.appendChild(newCanvas);
        canvas = newCanvas;
    }
    
    // Get the context
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
        labels: ['Returns/Refunds', 'Cancellations', 'Normal Orders'],
        datasets: [{
            data: [
                metrics.return_rate || 0,
                metrics.cancellation_rate || 0,
                100 - ((metrics.return_rate || 0) + (metrics.cancellation_rate || 0))
            ],
            backgroundColor: [
                'rgba(255, 159, 64, 0.7)',  // orange for returns/refunds
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
    try {
        window.returnsVsCancellationsChart = new Chart(ctx, {
            type: 'pie',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: {
                                size: 11
                            }
                        }
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
        console.log('Returns vs Cancellations chart created successfully');
    } catch (error) {
        console.error('Error creating Returns vs Cancellations chart:', error);
    }
}

/**
 * Creates a Top Products chart/list with enhanced visualization
 */
function createTopProductsChart(metrics, topProducts) {
    console.log('Creating Top Products visualization with:', topProducts);
    if (!topProducts || topProducts.length === 0) {
        console.warn('No top products data available');
        return;
    }
    
    // Get the container
    const container = document.getElementById('dashboardTopProductsList');
    if (!container) {
        console.error('Top products container not found');
        return;
    }
    
    // Show the parent container
    const parentContainer = document.getElementById('topProductsContainer');
    if (parentContainer) {
        parentContainer.classList.remove('hidden');
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Create list items for top products with enhanced styling
    topProducts.slice(0, 10).forEach((product, index) => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between py-1.5';
        
        // Calculate percentage relative to top product
        const topValue = topProducts[0].value || 1;  // Prevent division by zero
        const percentage = (product.value / topValue) * 100;
        
        // Determine color based on ranking
        const colors = [
            'bg-[#7B3DF3]', // Purple (primary)
            'bg-[#8F5DF5]', // Lighter purple
            'bg-[#A37DF7]', // Even lighter purple
            'bg-[#B89DF9]', // Very light purple
            'bg-gray-400'   // Gray for the rest
        ];
        
        const bgColor = index < colors.length ? colors[index] : colors[colors.length - 1];
        
        item.innerHTML = `
            <div class="flex items-center">
                <div class="text-sm font-medium ${index < 3 ? 'text-[#7B3DF3]' : 'text-gray-700'} mr-2">${index + 1}.</div>
                <div class="text-sm text-gray-600 truncate max-w-[150px]">${product.name}</div>
            </div>
            <div class="flex items-center">
                <div class="text-sm font-medium text-gray-700 mr-2">${formatCurrency(product.value)}</div>
                <div class="w-24 bg-gray-100 rounded-full h-2.5">
                    <div class="${bgColor} h-2.5 rounded-full" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
        
        container.appendChild(item);
    });

    console.log('Top Products visualization created successfully');
}

/**
 * Creates a Bottom Products list with enhanced visualization
 */
function createBottomProductsList(metrics, bottomProducts) {
    console.log('Creating Bottom Products visualization with:', bottomProducts);
    if (!bottomProducts || bottomProducts.length === 0) {
        console.warn('No bottom products data available');
        return;
    }
    
    // Get the container
    const container = document.getElementById('dashboardBottomProductsList');
    if (!container) {
        console.error('Bottom products container not found');
        return;
    }
    
    // Show the parent container
    const parentContainer = document.getElementById('bottomProductsContainer');
    if (parentContainer) {
        parentContainer.classList.remove('hidden');
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Create list items for bottom products with enhanced styling
    bottomProducts.slice(0, 10).forEach((product, index) => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between py-1.5';
        
        // Calculate percentage relative to top bottom product
        const topValue = bottomProducts[0].value || 1;  // Prevent division by zero
        const percentage = (product.value / topValue) * 100;
        
        item.innerHTML = `
            <div class="flex items-center">
                <div class="text-sm font-medium text-gray-700 mr-2">${index + 1}.</div>
                <div class="text-sm text-gray-600 truncate max-w-[150px]">${product.name}</div>
            </div>
            <div class="flex items-center">
                <div class="text-sm font-medium text-gray-700 mr-2">${formatCurrency(product.value)}</div>
                <div class="w-24 bg-gray-100 rounded-full h-2.5">
                    <div class="bg-gray-400 h-2.5 rounded-full" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
        
        container.appendChild(item);
    });

    console.log('Bottom Products visualization created successfully');
}

/**
 * Creates a list of products with high returns/refunds
 */
function createHighReturnsProductsList(metrics, highReturnProducts) {
    console.log('📊 Creating high returns/refunds products list');
    
    const container = document.getElementById('highReturnsContainer');
    if (!container) return;
    
    // Show the container
    container.classList.remove('hidden');
    
    // Update the title to reflect combined returns/refunds
    const titleElement = container.querySelector('h4');
    if (titleElement) {
        titleElement.textContent = 'Products with High Returns/Refunds';
    }
    
    // Get the list container
    const listContainer = document.getElementById('highReturnsList');
    if (!listContainer) return;
    
    // Clear previous content
    listContainer.innerHTML = '';
    
    // Check if we have data to display
    if (!highReturnProducts || highReturnProducts.length === 0) {
        listContainer.innerHTML = `
            <div class="text-center py-4 text-gray-500 text-sm">
                No products with high returns/refunds found
            </div>
        `;
        return;
    }
    
    // Create list items for high return products
    highReturnProducts.slice(0, 10).forEach((product, index) => {
        // Calculate rate based on return_rate (preferred) or fallback to cancellation_rate
        const rate = product.return_rate !== undefined ? product.return_rate : product.cancellation_rate;
        const rateType = product.return_rate !== undefined ? 'return/refund' : 'cancellation';
        
        // Determine color class based on rate
        const colorClass = rate > 15 ? 'text-red-500' : 
                           rate > 10 ? 'text-orange-500' : 'text-yellow-500';
        
        // Create the list item
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between py-1.5 border-b border-gray-100';
        
        item.innerHTML = `
            <div class="flex items-center flex-1 min-w-0">
                <div class="text-xs font-medium text-gray-700 mr-2">${index + 1}.</div>
                <div class="text-xs text-gray-600 truncate">${product.name}</div>
            </div>
            <div class="flex items-center">
                <div class="text-xs font-medium ${colorClass} whitespace-nowrap">${rate.toFixed(1)}% ${rateType}</div>
            </div>
        `;
        
        listContainer.appendChild(item);
    });

    console.log('High Returns Products list created successfully');
}

/**
 * Creates a consolidated time series chart showing sales and returns/cancellations over time
 */
function createConsolidatedTimeSeriesChart(metrics) {
    console.log('Creating consolidated time series chart with:', metrics.time_series);
    if (!metrics.time_series || !metrics.time_series.labels || !metrics.time_series.data) {
        console.warn('No time series data available for consolidated chart');
        return;
    }
    
    // Get the container
    const container = document.getElementById('salesTrendContainer');
    if (!container) {
        console.error('Sales trend container not found');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    
    // Get the canvas
    const canvas = document.getElementById('dashboardSalesTrendChart');
    if (!canvas) {
        console.error('Sales trend canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.salesTrendChart) {
        window.salesTrendChart.destroy();
    }
    
    // Create datasets for the chart
    const datasets = [
        {
            label: 'Sales',
            data: metrics.time_series.data,
            backgroundColor: 'rgba(123, 61, 243, 0.1)',
            borderColor: 'rgba(123, 61, 243, 1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true
        }
    ];
    
    // Add returns data if available
    if (metrics.time_series.returns_data) {
        datasets.push({
            label: 'Returns',
            data: metrics.time_series.returns_data,
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true
        });
    }
    
    // Create the chart
    try {
        window.salesTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: metrics.time_series.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            padding: 10,
                            usePointStyle: true,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#333',
                        bodyColor: '#333',
                        borderColor: 'rgba(123, 61, 243, 0.2)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + formatCurrency(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0,
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            },
                            font: {
                                size: 10
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                hover: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
        console.log('Consolidated time series chart created successfully');
    } catch (error) {
        console.error('Error creating consolidated time series chart:', error);
    }
}

/**
 * Helper function to format currency values
 */
function formatCurrency(value) {
    if (value === undefined || value === null) return 'N/A';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value);
}

/**
 * Helper function to format currency values in a shortened format
 */
function formatCurrencyShort(value) {
    if (value === undefined || value === null) return 'N/A';
    if (value >= 10000000) return '₹' + (value / 10000000).toFixed(1) + 'Cr';
    if (value >= 100000) return '₹' + (value / 100000).toFixed(1) + 'L';
    if (value >= 1000) return '₹' + (value / 1000).toFixed(1) + 'K';
    return '₹' + value.toFixed(0);
}

/**
 * Helper function to format regular numbers with thousand separators
 */
function formatNumber(value) {
    // Handle invalid values
    if (value === undefined || value === null || isNaN(value)) {
        return '0';
    }
    
    value = parseFloat(value);
    
    // Format based on value range
    if (Math.abs(value) >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    } else if (Math.abs(value) >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
    } else {
        return value.toFixed(0);
    }
}

/**
 * Creates a bar chart for top 10 selling states
 */
function createTopSellingStatesChart(metrics, topRegions) {
    console.log('Creating Top Selling States bar chart with data:', topRegions);
    
    // Verify we have the required data
    if (!topRegions || !Array.isArray(topRegions) || topRegions.length === 0) {
        console.warn('Missing required data for Top Selling States chart');
        return;
    }
    
    // Get the container and verify it exists
    const container = document.getElementById('topSellingStatesContainer');
    if (!container) {
        console.error('Top Selling States container not found');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    
    // Get the canvas and verify it exists
    let canvas = document.getElementById('topSellingStatesChart');
    if (!canvas) {
        console.error('Top Selling States canvas not found, creating it');
        canvas = document.createElement('canvas');
        canvas.id = 'topSellingStatesChart';
        
        // Find the chart container inside the main container
        const chartContainer = container.querySelector('div');
        if (chartContainer) {
            chartContainer.appendChild(canvas);
        } else {
            // If there's no inner div, append directly to container
            container.appendChild(canvas);
        }
    }
    
    // Get the context
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context for Top Selling States chart');
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded, attempting to load it dynamically');
        loadChartJsLibrary();
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.topSellingStatesChart) {
        try {
            // Check if it's a valid Chart.js instance with a destroy method
            if (typeof window.topSellingStatesChart === 'object' && 
                window.topSellingStatesChart !== null && 
                typeof window.topSellingStatesChart.destroy === 'function') {
                window.topSellingStatesChart.destroy();
            } else {
                console.warn('Existing topSellingStatesChart is not a valid Chart.js instance');
                // Just delete the reference if it's not a valid chart
                window.topSellingStatesChart = null;
            }
        } catch (error) {
            console.error('Error destroying existing Top Selling States chart:', error);
            // Reset the chart reference
            window.topSellingStatesChart = null;
        }
    }
    
    // Prepare data for chart - limit to top 10
    const data = topRegions.slice(0, 10);
    
    // Create labels and datasets
    const labels = data.map(item => item.name || "Unknown");
    const values = data.map(item => parseFloat(item.value) || 0);
    
    // Generate gradient colors from primary color to lighter shades
    const colors = generateGradientColors('#7B3DF3', '#F0EFFF', data.length);
    
    // Create the chart
    try {
        // Clear any existing chart instance
        window.topSellingStatesChart = null;
        
        // Create a new chart instance
        window.topSellingStatesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales Amount',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 4,
                    maxBarThickness: 35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',  // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Sales: ${formatCurrency(context.raw)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
        
        // Verify we have a valid chart instance
        if (!window.topSellingStatesChart || typeof window.topSellingStatesChart.destroy !== 'function') {
            console.error('Failed to create a valid Chart.js instance for Top Selling States');
            window.topSellingStatesChart = null;
        } else {
            console.log('Top Selling States chart created successfully');
        }
    } catch (error) {
        console.error('Error creating Top Selling States chart:', error);
        console.error('Chart data:', { labels, values });
    }
}

/**
 * Creates a bar chart for top 10 selling products
 */
function createTopSellingProductsChart(metrics, topProducts) {
    console.log('Creating Top Selling Products bar chart with data:', topProducts);
    
    // Verify we have the required data
    if (!topProducts || !Array.isArray(topProducts) || topProducts.length === 0) {
        console.warn('Missing required data for Top Selling Products chart');
        return;
    }
    
    // Get the container and verify it exists
    const container = document.getElementById('topSellingProductsContainer');
    if (!container) {
        console.error('Top Selling Products container not found');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    
    // Get the canvas and verify it exists
    let canvas = document.getElementById('topSellingProductsChart');
    if (!canvas) {
        console.error('Top Selling Products canvas not found, creating it');
        canvas = document.createElement('canvas');
        canvas.id = 'topSellingProductsChart';
        
        // Find the chart container inside the main container
        const chartContainer = container.querySelector('div');
        if (chartContainer) {
            chartContainer.appendChild(canvas);
        } else {
            // If there's no inner div, append directly to container
            container.appendChild(canvas);
        }
    }
    
    // Get the context
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context for Top Selling Products chart');
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded, attempting to load it dynamically');
        loadChartJsLibrary();
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.topSellingProductsChart) {
        try {
            // Check if it's a valid Chart.js instance with a destroy method
            if (typeof window.topSellingProductsChart === 'object' && 
                window.topSellingProductsChart !== null && 
                typeof window.topSellingProductsChart.destroy === 'function') {
                window.topSellingProductsChart.destroy();
            } else {
                console.warn('Existing topSellingProductsChart is not a valid Chart.js instance');
                // Just delete the reference if it's not a valid chart
                window.topSellingProductsChart = null;
            }
        } catch (error) {
            console.error('Error destroying existing Top Selling Products chart:', error);
            // Reset the chart reference
            window.topSellingProductsChart = null;
        }
    }
    
    // Prepare data for chart - limit to top 10
    const data = topProducts.slice(0, 10);
    
    // Create labels and datasets
    const labels = data.map(item => {
        // Truncate long product names for better display
        const name = item.name || 'Unknown';
        return name.length > 20 ? name.substring(0, 20) + '...' : name;
    });
    const values = data.map(item => parseFloat(item.value) || 0);
    
    // Generate colors with a different hue for variety
    const colors = generateGradientColors('#3D7BF3', '#EFF0FF', data.length);
    
    // Create the chart
    try {
        // Clear any existing chart instance
        window.topSellingProductsChart = null;
        
        // Create a new chart instance
        window.topSellingProductsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales Amount',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 4,
                    maxBarThickness: 35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',  // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Sales: ${formatCurrency(context.raw)}`;
                            },
                            title: function(tooltipItems) {
                                // Show full product name in tooltip
                                const index = tooltipItems[0].dataIndex;
                                return data[index].name;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
        
        // Verify we have a valid chart instance
        if (!window.topSellingProductsChart || typeof window.topSellingProductsChart.destroy !== 'function') {
            console.error('Failed to create a valid Chart.js instance for Top Selling Products');
            window.topSellingProductsChart = null;
        } else {
            console.log('Top Selling Products chart created successfully');
        }
    } catch (error) {
        console.error('Error creating Top Selling Products chart:', error);
        console.error('Chart data:', { labels, values });
    }
}

/**
 * Helper function to generate gradient colors
 */
function generateGradientColors(startColor, endColor, steps) {
    const result = [];
    
    // Convert hex to RGB
    const startRGB = hexToRgb(startColor);
    const endRGB = hexToRgb(endColor);
    
    // Calculate step sizes for each component
    const rStep = (endRGB.r - startRGB.r) / (steps - 1);
    const gStep = (endRGB.g - startRGB.g) / (steps - 1);
    const bStep = (endRGB.b - startRGB.b) / (steps - 1);
    
    // Generate colors
    for (let i = 0; i < steps; i++) {
        const r = Math.round(startRGB.r + (rStep * i));
        const g = Math.round(startRGB.g + (gStep * i));
        const b = Math.round(startRGB.b + (bStep * i));
        result.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
    }
    
    return result;
}

/**
 * Helper function to convert hex color to RGB
 */
function hexToRgb(hex) {
    // Remove # if present
    hex = hex.replace('#', '');
    
    // Parse hex values
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    return { r, g, b };
}

/**
 * Creates a bar chart showing bottom selling states
 */
function createBottomSellingStatesChart(metrics, bottomRegions) {
    console.log('Creating Bottom Selling States chart with:', bottomRegions);
    
    // Validate input data
    if (!bottomRegions || !Array.isArray(bottomRegions) || bottomRegions.length === 0) {
        console.warn('No bottom regions data available for chart');
        return;
    }
    
    // Get the container
    const container = document.getElementById('bottomRegionsContainer');
    if (!container) {
        console.error('Bottom regions container not found. Element with ID "bottomRegionsContainer" does not exist in the DOM');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    console.log('Bottom regions container is now visible');
    
    // Check if there's a chart container div, create one if not
    let chartDiv = container.querySelector('div.h-60');
    if (!chartDiv) {
        console.log('Creating chart div for bottom regions');
        chartDiv = document.createElement('div');
        chartDiv.className = 'h-60 mt-4';
        
        // Insert it at the beginning of the container
        if (container.firstChild) {
            container.insertBefore(chartDiv, container.firstChild);
        } else {
            container.appendChild(chartDiv);
        }
    } else {
        console.log('Found existing chart div for bottom regions');
    }
    
    // Look for existing canvas or create a new one
    let canvas = chartDiv.querySelector('canvas');
    if (!canvas) {
        console.log('Creating new canvas for bottom regions chart');
        canvas = document.createElement('canvas');
        canvas.id = 'bottomSellingStatesChart';
        chartDiv.appendChild(canvas);
    } else {
        console.log('Found existing canvas for bottom regions chart');
    }
    
    // Verify we have a valid canvas context
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context for bottom regions chart');
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Cannot create bottom regions chart');
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.bottomSellingStatesChart) {
        try {
            window.bottomSellingStatesChart.destroy();
            console.log('Destroyed existing bottom regions chart');
        } catch (error) {
            console.error('Error destroying existing bottom regions chart:', error);
        }
        window.bottomSellingStatesChart = null;
    }
    
    try {
        // Prepare data for the chart - limit to 10 states
        const data = bottomRegions.slice(0, 10).reverse(); // Reverse to show lowest at bottom
        
        // Get labels and values
        const labels = data.map(region => region.name.length > 15 ? region.name.substring(0, 15) + '...' : region.name);
        const values = data.map(region => region.value);
        
        console.log('Chart data prepared:', { labels, values });
        
        // Generate gradient colors from red to orange
        const colors = generateGradientColors('#FF6B6B', '#FFA94D', data.length);
        
        // Create the chart
        window.bottomSellingStatesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales Value',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',  // Horizontal bar chart
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
                    x: {
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        console.log('Bottom Selling States chart created successfully');
    } catch (error) {
        console.error('Error creating bottom selling states chart:', error);
        console.error('Chart data:', { bottomRegions });
    }
}

/**
 * Creates a bar chart showing bottom selling products
 */
function createBottomSellingProductsChart(metrics, bottomProducts) {
    console.log('Creating Bottom Selling Products chart with:', bottomProducts);
    
    // Validate input data
    if (!bottomProducts || !Array.isArray(bottomProducts) || bottomProducts.length === 0) {
        console.warn('No bottom products data available for chart');
        return;
    }
    
    // Get the container
    const container = document.getElementById('bottomProductsContainer');
    if (!container) {
        console.error('Bottom products container not found. Element with ID "bottomProductsContainer" does not exist in the DOM');
        return;
    }
    
    // Show the container
    container.classList.remove('hidden');
    console.log('Bottom products container is now visible');
    
    // Check if there's a chart container div, create one if not
    let chartDiv = container.querySelector('div.h-60');
    if (!chartDiv) {
        console.log('Creating chart div for bottom products');
        chartDiv = document.createElement('div');
        chartDiv.className = 'h-60 mt-4';
        
        // Insert it at the beginning of the container
        if (container.firstChild) {
            container.insertBefore(chartDiv, container.firstChild);
        } else {
            container.appendChild(chartDiv);
        }
    } else {
        console.log('Found existing chart div for bottom products');
    }
    
    // Look for existing canvas or create a new one
    let canvas = chartDiv.querySelector('canvas');
    if (!canvas) {
        console.log('Creating new canvas for bottom products chart');
        canvas = document.createElement('canvas');
        canvas.id = 'bottomSellingProductsChart';
        chartDiv.appendChild(canvas);
    } else {
        console.log('Found existing canvas for bottom products chart');
    }
    
    // Verify we have a valid canvas context
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context for bottom products chart');
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Cannot create bottom products chart');
        return;
    }
    
    // Destroy existing chart if it exists
    if (window.bottomSellingProductsChart) {
        try {
            window.bottomSellingProductsChart.destroy();
            console.log('Destroyed existing bottom products chart');
        } catch (error) {
            console.error('Error destroying existing bottom products chart:', error);
        }
        window.bottomSellingProductsChart = null;
    }
    
    try {
        // Prepare data for the chart - limit to 10 products
        const data = bottomProducts.slice(0, 10).reverse(); // Reverse to show lowest at bottom
        
        // Get labels and values
        const labels = data.map(product => product.name.length > 15 ? product.name.substring(0, 15) + '...' : product.name);
        const values = data.map(product => product.value);
        
        console.log('Chart data prepared:', { labels, values });
        
        // Generate gradient colors from red to orange
        const colors = generateGradientColors('#FF6B6B', '#FFA94D', data.length);
        
        // Create the chart
        window.bottomSellingProductsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sales Value',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.7', '1')),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',  // Horizontal bar chart
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
                    x: {
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        console.log('Bottom Selling Products chart created successfully');
    } catch (error) {
        console.error('Error creating bottom selling products chart:', error);
        console.error('Chart data:', { bottomProducts });
    }
}

// Export functions for use in other modules
window.enhancedCharts = {
    createReturnsVsCancellationsChart,
    createTopProductsChart,
    createBottomProductsList,
    createHighReturnsProductsList,
    createConsolidatedTimeSeriesChart,
    createBottomSellingStatesChart,
    createBottomSellingProductsChart,
    formatCurrency,
    formatCurrencyShort,
    formatNumber
};

// Add these functions to the window object directly as well
window.createBottomSellingStatesChart = createBottomSellingStatesChart;
window.createBottomSellingProductsChart = createBottomSellingProductsChart; 