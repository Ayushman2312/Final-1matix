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
        'highReturnsContainer'
    ];
    
    // Make sure all containers exist and are properly initialized
    chartContainers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            // Keep containers hidden until they have data
            container.classList.add('hidden');
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
        'fallbackChart'
    ];

    chartCanvases.forEach(canvasId => {
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            console.log(`Chart canvas ${canvasId} is available`);
        } else {
            console.warn(`Chart canvas ${canvasId} not found in the DOM`);
        }
    });
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
    
    // Calculate regular orders percentage
    const return_rate = parseFloat(metrics.return_rate) || 0;
    const cancellation_rate = parseFloat(metrics.cancellation_rate) || 0;
    const regular_rate = Math.max(0, 100 - return_rate - cancellation_rate);
    
    // Prepare chart data
    const data = {
        labels: ['Returns', 'Cancellations', 'Regular Orders'],
        datasets: [{
            data: [return_rate, cancellation_rate, regular_rate],
            backgroundColor: [
                'rgba(255, 159, 64, 0.7)',  // orange for returns
                'rgba(255, 99, 132, 0.7)',   // red for cancellations
                'rgba(75, 192, 192, 0.7)'    // green for regular orders
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
 * Creates a list of products with high returns/cancellations
 */
function createHighReturnsProductsList(metrics, highReturnProducts) {
    console.log('Creating High Returns Products list with:', highReturnProducts);
    if (!highReturnProducts || highReturnProducts.length === 0) {
        console.warn('No high return products data available');
        return;
    }
    
    // Get the container
    const container = document.getElementById('highReturnsList');
    if (!container) {
        console.error('High returns container not found');
        return;
    }
    
    // Show the parent container
    const parentContainer = document.getElementById('highReturnsContainer');
    if (parentContainer) {
        parentContainer.classList.remove('hidden');
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Create list items for high return products
    highReturnProducts.slice(0, 10).forEach((product, index) => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between py-1.5';
        
        // Determine which rate to display (return or cancellation)
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
                <div class="text-sm font-medium ${colorClass}">${rate.toFixed(1)}% ${rateType}</div>
                <div class="ml-2 w-16 bg-gray-100 rounded-full h-2">
                    <div class="bg-${rate > 15 ? 'red' : rate > 10 ? 'orange' : 'yellow'}-400 h-2 rounded-full" 
                         style="width: ${Math.min(100, rate * 4)}%"></div>
                </div>
            </div>
        `;
        
        container.appendChild(item);
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
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + formatCurrency(context.raw);
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
    if (value === undefined || value === null) return 'N/A';
    return new Intl.NumberFormat('en-IN').format(value);
}

// Export functions for use in other modules
window.enhancedCharts = {
    createReturnsVsCancellationsChart,
    createTopProductsChart,
    createBottomProductsList,
    createHighReturnsProductsList,
    createConsolidatedTimeSeriesChart,
    formatCurrency,
    formatCurrencyShort,
    formatNumber
}; 