# Google Trends Analyzer with AI Insights

A Django application for analyzing Google Trends data with AI-powered insights using Google's Generative AI.

## Features

- Interactive visualization of Google Trends data
- Time series analysis with moving averages and trend lines
- Geographic analysis of search interest by state/province and city
- Seasonal pattern detection and visualization
- AI-powered insights and recommendations using Google Generative AI
- Enhanced AI insights with trending analysis, future scope, ad recommendations, and keyword usage tips

## Setup

### Requirements

- Python 3.8+
- Django 3.2+
- pytrends library
- Google Generative AI API key

### Installation

1. Clone the repository
2. Install the requirements:

```bash
pip install -r requirements.txt
```

3. Set up the Google API key:

```bash
# On Windows
set GOOGLE_API_KEY=your_api_key_here

# On macOS/Linux
export GOOGLE_API_KEY=your_api_key_here
```

4. Make migrations and migrate:

```bash
python manage.py makemigrations
python manage.py migrate
```

5. Run the development server:

```bash
python manage.py runserver
```

### Setting up Google Generative AI

1. Visit the [Google AI Studio](https://makersuite.google.com/app/apikey) to create an API key
2. Set the API key as an environment variable:

```bash
# On Windows
set GOOGLE_API_KEY=your_api_key_here

# On macOS/Linux
export GOOGLE_API_KEY=your_api_key_here

# For permanent setup on Windows, add to System Variables
```

3. For production, add the API key to your server environment variables or use a secrets management solution.

## Usage

1. Navigate to the Trends page
2. Enter a search term in the input field
3. Select the desired analysis option:
   - Time trends only (default)
   - Time trends + State/Province analysis
   - Time trends + City analysis
   - Complete analysis (Time trends + States + Cities + Related queries)
   - State/Province analysis only (faster)
   - City analysis only (faster)
4. View the interactive charts and visualizations
5. Access the enhanced AI-powered insights:
   - Trend Analysis: Detailed analysis of search interest patterns over time
   - Future Scope: Assessment of potential success and future trends for the keyword
   - Advertising Recommendations: Specific guidance for creating effective ads
   - Keyword Usage Tips: Practical tips for using the keyword effectively in marketing

## Enhanced AI Insights

The application now provides more comprehensive AI-powered insights using Google's Generative AI. When viewing trends for a keyword, you'll see:

1. **Trend Analysis**: In-depth analysis of search patterns, user interest over time, and factors influencing these trends
2. **Future Scope Assessment**: Evaluation of the keyword's potential for success based on current and historical trends
3. **Advertising Recommendations**: Strategic guidance for creating effective ads targeting this keyword, including timing, messaging, and targeting strategies
4. **Keyword Usage Tips**: Practical advice for leveraging the keyword in marketing, content creation, and sales strategies

These insights are generated in real-time using Google's Gemini model and are based on the specific trend data for your keyword.

## Troubleshooting

### Charts not displaying
- Ensure Chart.js is properly loaded
- Check browser console for JavaScript errors
- Verify that the API is returning valid data structure

### AI Insights not working
- Verify that the GOOGLE_API_KEY environment variable is properly set
- Check the logs for API errors
- Ensure you have sufficient quota for the Google Generative AI API

### Rate limiting from Google Trends
- Use different analysis options to reduce API calls
- Add delays between requests
- Consider using a proxy service for high-volume usage

## License

This project is licensed under the MIT License - see the LICENSE file for details. 