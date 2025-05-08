"""
Google Trends data retrieval and analysis module
"""
import logging

logger = logging.getLogger(__name__)

# Try to apply urllib3 compatibility fix
try:
    from .urllib3_fix import apply_urllib3_fix
    if apply_urllib3_fix():
        logger.info("Applied urllib3 compatibility fix for Google Trends")
    else:
        logger.warning("Failed to apply urllib3 compatibility fix")
except Exception as e:
    logger.warning(f"Error applying urllib3 compatibility fix: {str(e)}")

# Import main functions
try:
    from .trends import get_trends_json
except ImportError as e:
    logger.error(f"Failed to import trends module: {str(e)}")

__all__ = ['get_trends_json']
