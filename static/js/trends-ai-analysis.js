/**
 * Trends AI Analysis - Integration with Google Generative AI
 * Generates insights and recommendations based on trends data
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Trends AI Analysis JS loaded');

    // Initialize global variables
    window.aiAnalysisGenerated = false;

    // Function to initialize AI analysis features after chart is rendered
    window.initializeAIAnalysis = function() {
        console.log('Initializing AI Analysis');
        
        // Check if chart data exists
        if (!window.trendsData) {
            console.warn('No trends data available for AI analysis');
            return;
        }
        
        // Begin analysis generation
        generateAnalysis(window.trendsData, window.lastFetchedKeyword);
    };

    // Function to generate analysis from trends data
    async function generateAnalysis(data, keyword) {
        console.log('Generating analysis for:', keyword);
        
        if (!data || !keyword) {
            console.error('Missing data or keyword for analysis');
            return;
        }
        
        // Get DOM elements
        const analysisContent = document.getElementById('analysisContent');
        const recommendationContent = document.getElementById('recommendationContent');
        
        if (!analysisContent || !recommendationContent) {
            console.error('Analysis or recommendation containers not found');
            return;
        }
        
        try {
            // Show loading indicators with improved animation
            analysisContent.innerHTML = '<div class="flex items-center justify-center p-4"><div class="animate-pulse flex flex-col items-center"><div class="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div><p>Generating intelligent analysis...</p></div></div>';
            recommendationContent.innerHTML = '<div class="flex items-center justify-center p-4"><div class="animate-pulse flex flex-col items-center"><div class="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-2"></div><p>Generating personalized recommendations...</p></div></div>';
            
            // Format data for AI analysis - ensure we send all relevant data
            const processedData = prepareDataForAnalysis(data, keyword);
            
            // Get business intent value if available
            const businessIntentElement = document.getElementById('business_intent');
            const businessIntent = businessIntentElement ? businessIntentElement.value : '';
            console.log('Using business_intent for AI analysis:', businessIntent);
            
            // Prepare request payload
            const requestPayload = {
                keyword: keyword,
                data: processedData,
                business_intent: businessIntent
            };
            
            // Add business details if business intent is 'no'
            if (businessIntent === 'no') {
                const brandName = document.getElementById('brandName').value;
                const businessWebsite = document.getElementById('businessWebsite').value;
                
                // Get all selected marketplace options from checkboxes
                const marketplaceCheckboxes = document.querySelectorAll('.marketplace-checkbox:checked');
                const selectedMarketplaces = Array.from(marketplaceCheckboxes).map(checkbox => checkbox.value);
                const marketplace = selectedMarketplaces.join(', ');
                
                // Add business details to the request payload
                requestPayload.brand_name = brandName;
                requestPayload.user_website = businessWebsite;
                requestPayload.marketplaces_selected = marketplace;
            }
            
            // Make API request to backend for AI analysis
            const response = await fetch('/trends/ai-analysis/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(requestPayload),
                // Add timeout to prevent long waiting times
                signal: AbortSignal.timeout(30000) // 30 seconds timeout
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const aiResponse = await response.json();
            console.log('AI Analysis response:', aiResponse);
            
            // Check for successful response
            if (aiResponse.status === 'error') {
                throw new Error(aiResponse.message || 'Failed to generate AI analysis');
            }
            
            // Update the UI with the AI-generated content
            if (aiResponse.analysis) {
                analysisContent.innerHTML = formatAIContent(aiResponse.analysis);
                // Add a subtle animation to highlight new content
                fadeInContent(analysisContent);
            } else {
                analysisContent.innerHTML = generateFallbackAnalysis(data, keyword);
            }
            
            if (aiResponse.recommendations) {
                recommendationContent.innerHTML = formatRecommendations(aiResponse.recommendations);
                // Add a subtle animation to highlight new content
                fadeInContent(recommendationContent);
            } else {
                recommendationContent.innerHTML = generateFallbackRecommendations(data, keyword);
            }
            
            // Set flag indicating analysis was generated
            window.aiAnalysisGenerated = true;
            
            // Dispatch event to show AI indicator badges if AI was used
            if (aiResponse.isAi) {
                document.dispatchEvent(new CustomEvent('aiAnalysisComplete', {
                    detail: { isAi: true }
                }));
            }
            
            // Trigger event to adjust scrollable content
            document.dispatchEvent(new CustomEvent('contentUpdated'));
            
        } catch (error) {
            console.error('Error generating AI analysis:', error);
            
            // Show a more helpful error message in the UI
            analysisContent.innerHTML = `
                <div class="p-4 text-left">
                    <p class="font-medium text-red-600 mb-2">Analysis generation encountered an issue:</p>
                    <p class="text-gray-700">${error.message || 'Unable to generate analysis at this time.'}</p>
                    <p class="text-gray-600 mt-2">Using alternative analysis method:</p>
                    ${generateFallbackAnalysis(data, keyword)}
                </div>
            `;
            
            recommendationContent.innerHTML = `
                <div class="p-4 text-left">
                    <p class="text-gray-600 mb-2">Using alternative recommendation method:</p>
                    ${generateFallbackRecommendations(data, keyword)}
                </div>
            `;
            
            // Trigger event to adjust scrollable content
            document.dispatchEvent(new CustomEvent('contentUpdated'));
        }
    }
    
    // Function to add fade-in animation
    function fadeInContent(element) {
        element.style.opacity = '0';
        element.style.transition = 'opacity 0.5s ease-in-out';
        
        // Trigger the animation after a small delay
        setTimeout(() => {
            element.style.opacity = '1';
        }, 100);
    }
    
    // Function to prepare data for analysis
    function prepareDataForAnalysis(data, keyword) {
        // If data is not in expected format, return original
        if (!Array.isArray(data) && typeof data !== 'object') {
            return data;
        }
        
        try {
            // Extract key trend patterns
            let processedData = {};
            
            // Check for SERP API data format
            if (data.metadata && data.metadata.source === 'serp_api') {
                console.log('Processing SERP API data for analysis');
                
                // Check if it's raw SERP API data
                if (data.interest_over_time && data.interest_over_time.timeline_data) {
                    processedData.timeSeriesData = data.interest_over_time.timeline_data.map(point => {
                        const valueObj = point.values.find(v => v.query === keyword) || point.values[0];
                        return {
                            date: point.date,
                            value: valueObj ? (valueObj.extracted_value || valueObj.value) : 0
                        };
                    });
                    
                    // Calculate trends
                    processedData.trends = calculateTrendData(processedData.timeSeriesData);
                } 
                // Check if it's already been transformed to our standard format
                else if (data.data && data.data.time_trends) {
                    processedData.timeSeriesData = data.data.time_trends;
                    processedData.trends = calculateTrendData(processedData.timeSeriesData);
                }
                
                return processedData;
            }
            
            // Handle different data formats
            if (Array.isArray(data)) {
                // Time series data
                processedData.timeSeriesData = data.map(point => {
                    // Format depends on the structure returned by the API
                    if (point.date && point[keyword] !== undefined) {
                        return {
                            date: point.date,
                            value: point[keyword]
                        };
                    } else if (point.time && point.value !== undefined) {
                        return {
                            date: point.time,
                            value: point.value
                        };
                    }
                    return point;
                });
                
                // Calculate trends
                processedData.trends = calculateTrendData(processedData.timeSeriesData);
            } else if (data.data && data.data.time_trends) {
                // Backend API format
                processedData.timeSeriesData = data.data.time_trends.map(point => {
                    if (point.date && point[keyword] !== undefined) {
                        return {
                            date: point.date,
                            value: point[keyword]
                        };
                    }
                    return point;
                });
                
                // Include regional data if available
                if (data.data.region_data && data.data.region_data.length > 0) {
                    processedData.regionData = data.data.region_data;
                }
                
                // Calculate trends
                processedData.trends = calculateTrendData(processedData.timeSeriesData);
            } else {
                // Try to intelligently extract from other formats
                if (data.time_trends) {
                    processedData.timeSeriesData = data.time_trends;
                } else if (data.data && typeof data.data === 'object') {
                    // Look for arrays that might contain the time series
                    for (const key in data.data) {
                        if (Array.isArray(data.data[key]) && data.data[key].length > 0) {
                            processedData.timeSeriesData = data.data[key];
                            break;
                        }
                    }
                }
                
                // Include all other data as-is
                processedData = { ...processedData, ...data };
            }
            
            return processedData;
        } catch (error) {
            console.error('Error preparing data for analysis:', error);
            return data; // Return original data on error
        }
    }
    
    // Function to format AI content with proper styling
    function formatAIContent(content) {
        if (!content) return '';
        
        // First, check if the content already has HTML formatting
        if (content.includes('<p>') || content.includes('<h') || content.includes('<li>')) {
            // Content already has HTML - just sanitize it for safety
            const sanitizedContent = content
                .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
            
            return sanitizedContent;
        }
        
        // Format paragraphs (split by double newlines)
        let formatted = content
            .split('\n\n')
            .filter(para => para.trim() !== '')
            .map(para => `<p>${para.replace(/\n/g, '<br>')}</p>`)
            .join('');
        
        // Format headers (markdown style)
        formatted = formatted.replace(/<p>#+\s+(.*?)<\/p>/g, (match, header) => {
            return `<h3 class="text-lg font-semibold mb-2">${header}</h3>`;
        });
        
        // Format bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/__(.*?)__/g, '<strong>$1</strong>');
        
        // Format emphasis
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        formatted = formatted.replace(/_(.*?)_/g, '<em>$1</em>');
        
        // Add extra styling
        formatted = `<div class="ai-analysis">${formatted}</div>`;
            
        return formatted;
    }
    
    // Function to format recommendations with better styling
    function formatRecommendations(content) {
        if (!content) return '';
        
        // Check if it's already in numbered list format
        const hasNumberedList = /^\d+\./.test(content.trim());
        
        if (hasNumberedList) {
            // Split by line and process each item
            const items = content.split('\n')
                .filter(line => line.trim() !== '')
                .map(line => {
                    // Check if this line starts with a number
                    if (/^\d+\./.test(line.trim())) {
                        // This is a new list item
                        const title = line.trim();
                        return `<li class="mb-4"><div class="font-medium text-purple-700">${title}</div>`;
                    } else {
                        // This is explanation text
                        return line;
                    }
                })
                .join('</li>');
            
            return `<ol class="list-decimal pl-5 space-y-2">${items}</li></ol>`;
        } else {
            // Fall back to paragraph formatting
            return formatAIContent(content);
        }
    }
    
    // Function to calculate trend data (growth, volatility, etc.)
    function calculateTrendData(timeSeriesData) {
        if (!Array.isArray(timeSeriesData) || timeSeriesData.length < 2) {
            return {};
        }
        
        try {
            const values = timeSeriesData.map(point => 
                typeof point.value === 'number' ? point.value : 0
            );
            
            // Filter out non-numeric or zero values
            const validValues = values.filter(val => val > 0);
            
            if (validValues.length < 2) {
                return { insufficient: true };
            }
            
            // Calculate basic statistics
            const min = Math.min(...validValues);
            const max = Math.max(...validValues);
            const avg = validValues.reduce((sum, val) => sum + val, 0) / validValues.length;
            
            // Calculate growth metrics
            const first = validValues[0];
            const last = validValues[validValues.length - 1];
            const overallGrowth = ((last - first) / first) * 100;
            
            // Calculate volatility (standard deviation)
            const squaredDiffs = validValues.map(val => Math.pow(val - avg, 2));
            const avgSquaredDiff = squaredDiffs.reduce((sum, val) => sum + val, 0) / validValues.length;
            const stdDev = Math.sqrt(avgSquaredDiff);
            const volatility = (stdDev / avg) * 100;
            
            // Identify peaks and troughs
            const peaks = [];
            const troughs = [];
            
            for (let i = 1; i < validValues.length - 1; i++) {
                if (validValues[i] > validValues[i-1] && validValues[i] > validValues[i+1]) {
                    peaks.push({
                        index: i,
                        value: validValues[i],
                        date: timeSeriesData[i].date
                    });
                }
                if (validValues[i] < validValues[i-1] && validValues[i] < validValues[i+1]) {
                    troughs.push({
                        index: i,
                        value: validValues[i],
                        date: timeSeriesData[i].date
                    });
                }
            }
            
            // Limit to top 3 peaks and troughs
            const topPeaks = peaks.sort((a, b) => b.value - a.value).slice(0, 3);
            const bottomTroughs = troughs.sort((a, b) => a.value - b.value).slice(0, 3);
            
            return {
                min,
                max,
                avg,
                overallGrowth,
                volatility,
                topPeaks,
                bottomTroughs,
                dataPoints: validValues.length
            };
        } catch (error) {
            console.error('Error calculating trend data:', error);
            return {};
        }
    }
    
    // Fallback function to generate analysis if API fails
    function generateFallbackAnalysis(data, keyword) {
        console.log('Generating fallback analysis');
        
        if (!Array.isArray(data) || data.length === 0) {
            return '<p>Unable to generate analysis for the provided data.</p>';
        }
        
        try {
            // Process data to extract insights
            const processedData = prepareDataForAnalysis(data, keyword);
            const trends = processedData.trends || {};
            
            // Generate basic analysis
            let analysis = `<p>Analysis of search trends for "${keyword}":</p>`;
            
            if (trends.insufficient) {
                return analysis + '<p>Insufficient data points to provide a meaningful analysis.</p>';
            }
            
            // Overall trend direction
            if (trends.overallGrowth !== undefined) {
                const direction = trends.overallGrowth > 0 ? 'increasing' : 'decreasing';
                analysis += `<p>The overall trend is ${direction} with a change of ${Math.abs(trends.overallGrowth).toFixed(2)}% over the analyzed period.</p>`;
            }
            
            // Volatility
            if (trends.volatility !== undefined) {
                const volatilityLevel = trends.volatility < 20 ? 'low' : trends.volatility < 50 ? 'moderate' : 'high';
                analysis += `<p>The interest has shown ${volatilityLevel} volatility (${trends.volatility.toFixed(2)}%), indicating ${volatilityLevel === 'low' ? 'stable' : volatilityLevel === 'moderate' ? 'somewhat fluctuating' : 'significantly fluctuating'} interest over time.</p>`;
            }
            
            // Peaks analysis
            if (trends.topPeaks && trends.topPeaks.length > 0) {
                analysis += '<p>Notable peak(s) in interest were observed';
                if (trends.topPeaks[0].date) {
                    const peakDates = trends.topPeaks.map(p => {
                        const date = new Date(p.date);
                        return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short' });
                    }).join(', ');
                    analysis += ` during ${peakDates}`;
                }
                analysis += '.</p>';
            }
            
            return analysis;
        } catch (error) {
            console.error('Error generating fallback analysis:', error);
            return '<p>Analysis is currently unavailable. Please try again later.</p>';
        }
    }
    
    // Fallback function to generate recommendations if API fails
    function generateFallbackRecommendations(data, keyword) {
        console.log('Generating fallback recommendations');
        
        if (!Array.isArray(data) || data.length === 0) {
            return '<p>Unable to generate recommendations based on the provided data.</p>';
        }
        
        try {
            // Process data to extract insights
            const processedData = prepareDataForAnalysis(data, keyword);
            const trends = processedData.trends || {};
            
            // Generate basic recommendations
            let recommendations = `<p>Recommendations based on "${keyword}" trends:</p>`;
            
            if (trends.insufficient) {
                return recommendations + '<p>Insufficient data points to provide meaningful recommendations.</p>';
            }
            
            // Based on overall trend
            if (trends.overallGrowth !== undefined) {
                if (trends.overallGrowth > 10) {
                    recommendations += `<p>With a strong upward trend of ${trends.overallGrowth.toFixed(2)}%, consider increasing investment in this area as interest is growing.</p>`;
                } else if (trends.overallGrowth > 0) {
                    recommendations += `<p>With a modest growth of ${trends.overallGrowth.toFixed(2)}%, maintain current strategy while monitoring for changes in the trend.</p>`;
                } else if (trends.overallGrowth > -10) {
                    recommendations += `<p>With a slight decline of ${Math.abs(trends.overallGrowth).toFixed(2)}%, consider refreshing your approach to stimulate new interest.</p>`;
                } else {
                    recommendations += `<p>With a significant decline of ${Math.abs(trends.overallGrowth).toFixed(2)}%, consider pivoting or diversifying your focus to more promising areas.</p>`;
                }
            }
            
            // Based on volatility
            if (trends.volatility !== undefined) {
                if (trends.volatility < 20) {
                    recommendations += '<p>The stable interest pattern suggests a consistent audience. Focus on deepening engagement rather than expanding reach.</p>';
                } else if (trends.volatility < 50) {
                    recommendations += '<p>The moderate fluctuations suggest seasonal or event-driven interest. Plan content and campaigns around these patterns.</p>';
                } else {
                    recommendations += '<p>The high volatility indicates unpredictable interest. Diversify your approach and be ready to capitalize quickly on upward trends.</p>';
                }
            }
            
            return recommendations;
        } catch (error) {
            console.error('Error generating fallback recommendations:', error);
            return '<p>Recommendations are currently unavailable. Please try again later.</p>';
        }
    }
    
    // Helper function to get CSRF token from cookies
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
}); 