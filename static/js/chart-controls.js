// Chart Controls and Filter Buttons
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chart controls script loaded');
    
    // Function to update active filter button
    function updateActiveFilterButton(activeButton) {
        // Get all filter buttons
        const filterButtons = document.querySelectorAll('.filter-button');
        
        // Remove active class from all buttons
        filterButtons.forEach(button => {
            button.classList.remove('active');
            button.classList.remove('bg-indigo-600');
            button.classList.remove('text-white');
            button.classList.add('bg-white');
            button.classList.add('text-indigo-700');
        });
        
        // Add active class to clicked button
        if (activeButton) {
            activeButton.classList.add('active');
            activeButton.classList.remove('bg-white');
            activeButton.classList.remove('text-indigo-700');
            activeButton.classList.add('bg-indigo-600');
            activeButton.classList.add('text-white');
        }
    }
    
    // Setup chart filter buttons
    function setupChartFilterButtons() {
        const viewByYearBtn = document.getElementById('viewByYear');
        const viewByQuarterBtn = document.getElementById('viewByQuarter');
        const viewByMonthBtn = document.getElementById('viewByMonth');
        const showSeasonalPatternBtn = document.getElementById('showSeasonalPattern');
        const allTimeBtn = document.getElementById('allTimeBtn');
        
        console.log('Filter buttons found:', {
            viewByYearBtn: !!viewByYearBtn,
            viewByQuarterBtn: !!viewByQuarterBtn,
            viewByMonthBtn: !!viewByMonthBtn,
            showSeasonalPatternBtn: !!showSeasonalPatternBtn,
            allTimeBtn: !!allTimeBtn
        });
        
        if (viewByYearBtn) {
            viewByYearBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Year button clicked');
                
                // Check if function is available in global scope
                if (typeof window.updateTimeUnit === 'function') {
                    window.updateTimeUnit('year');
                } else if (typeof updateTimeUnit === 'function') {
                    updateTimeUnit('year');
                } else {
                    console.error('updateTimeUnit function not found');
                }
                
                updateActiveFilterButton(this);
            });
        }
        
        if (viewByQuarterBtn) {
            viewByQuarterBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Quarter button clicked');
                
                if (typeof window.updateTimeUnit === 'function') {
                    window.updateTimeUnit('quarter');
                } else if (typeof updateTimeUnit === 'function') {
                    updateTimeUnit('quarter');
                } else {
                    console.error('updateTimeUnit function not found');
                }
                
                updateActiveFilterButton(this);
            });
        }
        
        if (viewByMonthBtn) {
            viewByMonthBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Month button clicked');
                
                if (typeof window.updateTimeUnit === 'function') {
                    window.updateTimeUnit('month');
                } else if (typeof updateTimeUnit === 'function') {
                    updateTimeUnit('month');
                } else {
                    console.error('updateTimeUnit function not found');
                }
                
                updateActiveFilterButton(this);
            });
        }
        
        if (showSeasonalPatternBtn) {
            showSeasonalPatternBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Seasonal pattern button clicked');
                
                // Implement seasonal pattern visualization
                if (typeof window.showSeasonalPattern === 'function') {
                    window.showSeasonalPattern();
                } else if (typeof showSeasonalPattern === 'function') {
                    showSeasonalPattern();
                } else {
                    // If the function doesn't exist yet, implement it here directly
                    showSeasonalPatternImplementation();
                }
                
                updateActiveFilterButton(this);
            });
        }
        
        if (allTimeBtn) {
            allTimeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('All time button clicked');
                
                if (typeof window.updateTimeUnit === 'function') {
                    window.updateTimeUnit('month'); // Default to month view for all time
                } else if (typeof updateTimeUnit === 'function') {
                    updateTimeUnit('month');
                } else {
                    console.error('updateTimeUnit function not found');
                }
                
                // Reset time range selector if it exists
                const timeRangeSelector = document.getElementById('timeRangeSelector');
                if (timeRangeSelector) {
                    timeRangeSelector.value = 'all';
                }
                
                // Call the filter by time range function with 'all'
                if (typeof window.filterByTimeRange === 'function') {
                    window.filterByTimeRange('all');
                }
                
                updateActiveFilterButton(viewByMonthBtn); // Set month button as active
            });
        }
        
        // Add event listener for time range select (year filter)
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', function() {
                const selectedValue = this.value;
                console.log('Time range changed to:', selectedValue);
                
                if (typeof window.filterByTimeRange === 'function') {
                    window.filterByTimeRange(selectedValue);
                } else {
                    // If the function doesn't exist yet, implement time range filtering here directly
                    filterByTimeRangeImplementation(selectedValue);
                }
            });
        }
        
        // Set month as default active button
        if (viewByMonthBtn) {
            setTimeout(() => {
                updateActiveFilterButton(viewByMonthBtn);
            }, 300);
        }
    }
    
    // Seasonal pattern implementation based on test-ui.html
    function showSeasonalPatternImplementation() {
        console.log('Implementing seasonal pattern visualization');
        
        // Get the trends data from the global scope
        const trendsData = window.trendsData || {};
        if (!trendsData.data || !trendsData.data.time_trends) {
            console.error('No trend data available for seasonal pattern');
            return;
        }
        
        const timeSeriesData = trendsData.data.time_trends;
        const keyword = trendsData.metadata.keywords[0];
        const ctx = document.getElementById('timeSeriesChart').getContext('2d');
        
        // Get the current chart instance
        let timeChart = null;
        if (window.timeChart) {
            timeChart = window.timeChart;
        } else {
            // Try to find the chart from Chart.js registry
            const charts = Chart.instances;
            for (let id in charts) {
                if (charts[id].canvas.id === 'timeSeriesChart') {
                    timeChart = charts[id];
                    break;
                }
            }
        }
        
        if (!timeChart) {
            console.error('Could not find time chart instance');
            return;
        }
        
        // Group data by month to show seasonal patterns
        const monthlyData = Array(12).fill(0).map(() => []);
        
        timeSeriesData.forEach((item) => {
            const date = new Date(item.date);
            const month = date.getMonth();
            monthlyData[month].push(item[keyword]);
        });
        
        const monthlyAverages = monthlyData.map(monthValues => {
            if (monthValues.length === 0) return 0;
            return monthValues.reduce((sum, val) => sum + val, 0) / monthValues.length;
        });
        
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        // Destroy existing chart
        timeChart.destroy();
        
        // Create new seasonal chart
        const newChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: monthNames,
                datasets: [{
                    label: 'Average Search Interest by Month',
                    data: monthlyAverages,
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }]
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
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Average Search Interest'
                        }
                    }
                }
            }
        });
        
        // Store the new chart in the global scope
        window.timeChart = newChart;
        
        // Update the legend to show the new chart type
        updateSeasonalLegend();
    }
    
    // Function to update the legend for the seasonal chart
    function updateSeasonalLegend() {
        const legendContainer = document.querySelector('.legend');
        if (legendContainer) {
            legendContainer.innerHTML = `
                <div class="legend-item flex items-center">
                    <div class="legend-color w-3 h-3 mr-2 rounded-sm" style="background: rgba(52, 152, 219, 0.7);"></div>
                    <span class="text-sm text-gray-700">Average Monthly Interest</span>
                </div>
            `;
        }
    }
    
    // Time range filtering implementation based on test-ui.html
    function filterByTimeRangeImplementation(selectedValue) {
        console.log('Implementing time range filtering:', selectedValue);
        
        // Get the trends data from the global scope
        const trendsData = window.trendsData || {};
        if (!trendsData.data || !trendsData.data.time_trends) {
            console.error('No trend data available for time range filtering');
            return;
        }
        
        // Get the current chart instance
        let timeChart = null;
        if (window.timeChart) {
            timeChart = window.timeChart;
        } else {
            // Try to find the chart from Chart.js registry
            const charts = Chart.instances;
            for (let id in charts) {
                if (charts[id].canvas.id === 'timeSeriesChart') {
                    timeChart = charts[id];
                    break;
                }
            }
        }
        
        if (!timeChart) {
            console.error('Could not find time chart instance');
            return;
        }
        
        // If current chart is bar chart (seasonal view), revert to line chart
        if (timeChart.config.type === 'bar') {
            console.log('Cannot filter seasonal view by time range, please return to line chart view first');
            return;
        }
        
        const timeSeriesData = trendsData.data.time_trends;
        const keyword = trendsData.metadata.keywords[0];
        
        let filteredDates = [];
        let filteredValues = [];
        let filteredMovingAverages = [];
        let filteredTrendLine = [];
        
        if (selectedValue === 'all') {
            // Use all data
            filteredDates = timeSeriesData.map(item => item.date);
            filteredValues = timeSeriesData.map(item => item[keyword]);
            
            // Get existing moving averages and trend line
            filteredMovingAverages = timeChart.data.datasets[2].data;
            filteredTrendLine = timeChart.data.datasets[1].data;
        } else {
            // Filter by year
            const year = parseInt(selectedValue);
            
            // Filter the data for the selected year
            const yearData = timeSeriesData.filter(item => {
                const dateObj = new Date(item.date);
                return dateObj.getFullYear() === year;
            });
            
            if (yearData.length === 0) {
                console.warn('No data found for year:', year);
                return;
            }
            
            filteredDates = yearData.map(item => item.date);
            filteredValues = yearData.map(item => item[keyword]);
            
            // Recalculate moving average
            const movingAverageWindow = Math.min(12, Math.floor(yearData.length / 2));
            
            for (let i = 0; i < filteredValues.length; i++) {
                if (i < movingAverageWindow - 1) {
                    filteredMovingAverages.push(null);
                } else {
                    const windowValues = filteredValues.slice(i - movingAverageWindow + 1, i + 1);
                    const average = windowValues.reduce((sum, val) => sum + val, 0) / movingAverageWindow;
                    filteredMovingAverages.push(average);
                }
            }
            
            // Recalculate trend line
            const xValues = Array.from({ length: filteredValues.length }, (_, i) => i);
            const xMean = xValues.reduce((sum, val) => sum + val, 0) / xValues.length;
            const yMean = filteredValues.reduce((sum, val) => sum + val, 0) / filteredValues.length;
            
            let numerator = 0;
            let denominator = 0;
            
            for (let i = 0; i < filteredValues.length; i++) {
                numerator += (xValues[i] - xMean) * (filteredValues[i] - yMean);
                denominator += Math.pow(xValues[i] - xMean, 2);
            }
            
            const slope = numerator / denominator;
            const intercept = yMean - slope * xMean;
            
            filteredTrendLine = xValues.map(x => slope * x + intercept);
        }
        
        // Update chart with filtered data
        timeChart.data.labels = filteredDates;
        timeChart.data.datasets[0].data = filteredValues;
        timeChart.data.datasets[1].data = filteredTrendLine;
        timeChart.data.datasets[2].data = filteredMovingAverages;
        timeChart.update();
    }
    
    // Make the function available globally
    window.updateActiveFilterButton = updateActiveFilterButton;
    window.showSeasonalPattern = showSeasonalPatternImplementation;
    window.filterByTimeRange = filterByTimeRangeImplementation;
    
    // Call setup function immediately
    setupChartFilterButtons();
    
    // Also set up a fallback to ensure it's called after trends-charts.js loads
    if (document.readyState === 'complete') {
        console.log('Document already complete, setting up buttons immediately');
        setupChartFilterButtons();
    } else {
        window.addEventListener('load', function() {
            console.log('Window load event, setting up buttons');
            setupChartFilterButtons();
        });
    }
    
    // Add a check after a delay to ensure buttons are set up
    setTimeout(() => {
        console.log('Checking if chart filter buttons are properly set up');
        setupChartFilterButtons();
    }, 2000);
});