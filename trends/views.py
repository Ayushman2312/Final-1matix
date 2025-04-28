from django.shortcuts import render
import logging
from pytrends.request import TrendReq
import matplotlib.pyplot as plt
import io
import base64
from .trends import create_retry_session, get_trends_data

logger = logging.getLogger(__name__)

def trends_view(request):
    context = {
        'graph': None,
        'error': None,
        'searched': False,
        'keyword': ''
    }
    
    if request.method == 'POST':
        keyword = request.POST.get('keyword', '').strip()
        if keyword:
            context['keyword'] = keyword
            context['searched'] = True
            
            try:
                # Create a session with retry strategy
                session = create_retry_session()
                
                # Initialize PyTrends with the session
                pytrends = TrendReq(
                    hl='en-US',
                    tz=330,
                    requests_args={'verify': True},
                    timeout=(10, 30)
                )
                
                # Get trends data using the existing function
                interest_df = get_trends_data(
                    pytrends=pytrends,
                    keywords=[keyword],
                    timeframe='today 5-y',
                    geo='IN'
                )
                
                if interest_df is not None and not interest_df.empty:
                    # Create the plot
                    plt.figure(figsize=(14, 8))
                    plt.plot(interest_df.index, interest_df[keyword], 
                            linewidth=2, 
                            color='#2E86C1')
                    
                    plt.title(f'Google Search Trends for "{keyword}" in India\nLast 5 Years', 
                             fontsize=16)
                    plt.xlabel('Time', fontsize=12)
                    plt.ylabel('Search Interest', fontsize=12)
                    
                    # Format x-axis
                    plt.xticks(rotation=45)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    # Save plot to bytes buffer
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
                    buffer.seek(0)
                    image_png = buffer.getvalue()
                    buffer.close()
                    plt.close()
                    
                    # Encode the image to base64
                    context['graph'] = base64.b64encode(image_png).decode('utf-8')
                else:
                    context['error'] = 'No data available for this keyword. Try a different search term.'
                    
            except Exception as e:
                logger.error(f"Error while generating trends data: {str(e)}")
                context['error'] = 'An unexpected error occurred. Please try again.'
            finally:
                plt.close('all')  # Clean up matplotlib resources
    
    return render(request, 'aitrends/trends.html', context)
