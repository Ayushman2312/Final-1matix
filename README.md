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

# Contact Scraper

A robust web scraper for extracting Indian mobile numbers and email addresses from Google and Bing search results based on user-provided keywords.

## Features

- Scrapes email addresses and Indian mobile numbers from search engine results
- Uses proxies to avoid detection and IP blocking
- Validates Indian mobile numbers (starting with 6, 7, 8, or 9)
- Multi-threaded processing for faster scraping
- Saves results to CSV files

## Requirements

- Python 3.6+
- Required packages (install via `pip install -r requirements.txt`):
  - requests
  - beautifulsoup4
  - lxml

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script from the command line:

```
python data_miner/web_scrapper.py
```

You will be prompted to:
1. Enter a search keyword - this will be used to search for relevant websites
2. Enter the number of results to scrape (between 10-100)

The scraper will:
1. Search Google and Bing for the keyword
2. Visit each result page
3. Extract and validate Indian phone numbers and email addresses
4. Save the results to a CSV file in the `scraped_data` directory

## Customization

- To add more proxies, edit the `proxy_list` in the `ContactScraper` class
- To adjust the number of concurrent threads, modify the `max_workers` parameter in the `ThreadPoolExecutor`

## Note

This tool is for educational purposes only. Please respect website terms of service and robots.txt directives when scraping. Use responsibly and ethically.

# 1Matrix Data Mining Tool

An advanced web scraping tool for extracting contact information (emails and phone numbers) from websites.

## Features

- Extract phone numbers and email addresses from websites based on keywords
- Background processing with Celery for handling long-running tasks
- Real-time progress monitoring
- Advanced validation rules for Indian phone numbers
- Results export to Excel
- Task history tracking

## Setup

### Requirements

- Python 3.8+
- Django 4.2+
- Redis (for Celery)
- Playwright (for browser automation)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
python -m playwright install chromium
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Start the Redis server (if not already running):
```bash
# On Windows:
redis-server

# On Unix/Linux:
redis-server /etc/redis/redis.conf
```

### Running the Application

1. Start the Django development server:
```bash
python manage.py runserver
```

2. Start Celery worker(s):
```bash
# Start a worker for background tasks
celery -A onematrix worker -l info -Q data_mining
```

## Usage

1. Navigate to `/data_miner/` in your browser
2. Enter a keyword to search for (e.g., "Digital Marketing Company in Mumbai")
3. Select the type of data to extract (phone numbers or email addresses)
4. Select the target country (default: India)
5. Click "Get" to start the mining process
6. Monitor the progress in real-time
7. Download the results as an Excel file

## Architecture

- `data_miner/web_scrapper.py`: Main scraping engine with browser automation
- `data_miner/tasks.py`: Celery tasks for background processing
- `data_miner/views.py`: Django views for handling requests and displaying results
- `data_miner/improved_validators.py`: Validation rules for phone numbers and emails

## Troubleshooting

- If browser automation fails, try reinstalling Playwright:
```bash
python -m playwright install --force chromium
```

- If Celery tasks are not running, check Redis connection:
```bash
redis-cli ping
```
Should return `PONG`

- If tasks are starting but not completing, check Celery worker logs for errors 