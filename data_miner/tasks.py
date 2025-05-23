import logging
import os
import time
import json
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pandas as pd
import traceback

from .models import MiningHistory, BackgroundTask
# Import the run_web_scraper_task function directly
from .web_scrapper import run_web_scraper_task

# Configure logging
logger = logging.getLogger(__name__)

@shared_task(name="data_miner.tasks.test_redis_connection")
def test_redis_connection():
    """
    Simple task to test if Celery can connect to Redis
    
    Returns:
        dict: Connection status information
    """
    logger.info("Testing Redis connection from Celery")
    
    # Report information about the environment
    import sys
    import platform
    import os
    
    # Test Redis connection directly if possible
    redis_info = {"status": "unknown"}
    try:
        import redis
        
        # Get Redis connection settings from Django
        redis_url = getattr(settings, 'CELERY_BROKER_URL', None)
        if not redis_url:
            redis_url = getattr(settings, 'BROKER_URL', 'redis://localhost:6379/0')
        
        # Try to connect and ping Redis
        redis_client = redis.from_url(redis_url)
        redis_ping = redis_client.ping()
        redis_info = {
            "status": "connected" if redis_ping else "unreachable",
            "url": redis_url.replace(":@", ":****@"),  # Mask password if present
            "ping": redis_ping
        }
        
        # Try to get Redis info
        try:
            redis_server_info = redis_client.info()
            redis_info["version"] = redis_server_info.get('redis_version', 'unknown')
            redis_info["used_memory"] = redis_server_info.get('used_memory_human', 'unknown')
            redis_info["connected_clients"] = redis_server_info.get('connected_clients', 'unknown')
        except Exception as e:
            redis_info["info_error"] = str(e)
            
    except Exception as e:
        redis_info = {
            "status": "error",
            "error": str(e)
        }
    
    # Return environment and connection info
    return {
        "status": "success",
        "message": "Redis connection test completed",
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "redis": redis_info,
        "environment": {k: v for k, v in os.environ.items() if k.startswith(('DJANGO', 'CELERY', 'REDIS'))}
    }

@shared_task(bind=True, name="data_miner.tasks.test_task_status")
def test_task_status(self, user_id=None):
    """
    Test task that updates its status periodically
    to verify that status updates are working correctly.
    
    Args:
        user_id: Optional user ID to associate with the task
    
    Returns:
        dict: Task result information
    """
    task_id = self.request.id
    logger.info(f"Starting test_task_status task {task_id}")
    
    # Create task record if user_id is provided
    task_record = None
    if user_id:
        try:
            from django.utils import timezone
            from .models import BackgroundTask
            
            task_record, created = BackgroundTask.objects.get_or_create(
                task_id=task_id,
                defaults={
                    'user_id': user_id,
                    'task_name': 'Test Task Status Updates',
                    'status': 'processing',
                    'parameters': {'test': True},
                    'progress': 0,
                    'created_at': timezone.now()
                }
            )
            logger.info(f"Created test task record: {task_record.id}")
        except Exception as e:
            logger.error(f"Error creating test task record: {e}")
    
    # Simulate work with status updates
    total_steps = 5
    for step in range(1, total_steps + 1):
        # Update progress
        progress = int((step / total_steps) * 100)
        message = f"Processing step {step}/{total_steps}"
        
        logger.info(f"Task {task_id}: {message} - {progress}%")
        
        # Update task record if available
        if task_record:
            try:
                task_record.progress = progress
                task_record.message = message
                task_record.save()
                logger.info(f"Updated task record {task_record.id} progress to {progress}%")
            except Exception as e:
                logger.error(f"Error updating task record: {e}")
        
        # Simulate work
        time.sleep(2)
    
    # Mark as completed
    if task_record:
        try:
            from django.utils import timezone
            task_record.status = 'completed'
            task_record.progress = 100
            task_record.message = "Test completed successfully"
            task_record.completed_at = timezone.now()
            task_record.save()
            logger.info(f"Marked task record {task_record.id} as completed")
        except Exception as e:
            logger.error(f"Error completing task record: {e}")
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Test task completed successfully",
        "steps_completed": total_steps
    }

@shared_task(bind=True, name="data_miner.tasks.scrape_contacts")
def scrape_contacts(self, keyword, data_type, country, user_id, max_results=30, max_runtime_minutes=15):
    """
    Run the contact scraping process in the background
    
    Args:
        keyword (str): Search keyword
        data_type (str): Type of data to extract ('phone' or 'email')
        country (str): Country code (e.g., 'IN', 'US')
        user_id (int): User ID
        max_results (int): Maximum number of results to retrieve
        max_runtime_minutes (int): Maximum runtime in minutes
        
    Returns:
        dict: Results of the scraping process
    """
    task_id = self.request.id
    logger.info(f"Starting scrape_contacts task {task_id} for keyword '{keyword}', data_type '{data_type}'")
    
    # Create or update background task record
    try:
        from django.utils import timezone
        task_record, created = BackgroundTask.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user_id': user_id,
                'task_name': f"Mining {data_type}s for '{keyword}'",
                'status': 'processing',
                'parameters': {
                    'keyword': keyword,
                    'data_type': data_type,
                    'country': country,
                    'max_results': max_results,
                    'max_runtime_minutes': max_runtime_minutes
                },
                'progress': 0
            }
        )
        
        if not created:
            task_record.status = 'processing'
            task_record.progress = 0
            task_record.error_message = None
            task_record.save()
        
        logger.info(f"Created/updated task record for task {task_id}: {task_record.id}")
    except Exception as e:
        logger.error(f"Error creating/updating task record: {e}")
        logger.error(traceback.format_exc())
        task_record = None
    
    # Create a status file to track progress
    status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
    os.makedirs(os.path.dirname(status_file_path), exist_ok=True)
    
    # Initialize status
    status = {
        "status": "processing",
        "progress": 0,
        "message": "Initializing scraper...",
        "start_time": datetime.now().isoformat(),
        "keyword": keyword,
        "data_type": data_type,
        "country": country,
        "task_id": task_id,
        "results_count": 0,
        "elapsed_time": 0
    }
    
    # Save initial status
    with open(status_file_path, 'w') as f:
        json.dump(status, f)
    
    start_time = time.time()
    
    try:
        # Update status
        status["progress"] = 5
        status["message"] = "Searching for websites..."
        _update_status(status_file_path, status)
        
        # Update task record
        if task_record:
            task_record.progress = 5
            task_record.save()
        
        # Execute the scraping using the enhanced function
        logger.info(f"Executing web scraper for task {task_id}")
        scraper_results = run_web_scraper_task(
            keyword=keyword,
            num_results=max_results,
            max_runtime_minutes=max_runtime_minutes,
            task_id=task_id,
            task_record=task_record,
            use_browser=True
        )
        
        # Calculate elapsed time
        elapsed_time = (time.time() - start_time) / 60.0  # in minutes
        
        # Extract relevant data based on data_type
        if data_type == 'phone':
            items = scraper_results.get('phones', [])
        else:  # email
            items = scraper_results.get('emails', [])
        
        # Clean up items (convert dictionaries to strings if needed)
        cleaned_items = []
        for item in items:
            if isinstance(item, dict):
                if data_type == 'phone' and 'phone' in item:
                    cleaned_items.append(item['phone'])
                else:
                    # Use string representation as fallback
                    cleaned_items.append(str(item))
            else:
                cleaned_items.append(str(item))
        
        # Create a proper DataFrame and save as Excel
        df = pd.DataFrame({data_type.capitalize(): cleaned_items})
        
        # Generate unique filename
        filename = f"mining_results_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_path = os.path.join('mining_results', filename)
        
        # Save to Excel in memory
        excel_content = ContentFile(b'')
        df.to_excel(excel_content, index=False)
        excel_content.seek(0)
        
        # Save to MiningHistory
        history = MiningHistory(
            user_id=user_id,
            keyword=keyword,
            country=country,
            data_type=data_type,
            results_count=len(cleaned_items)
        )
        
        # Save Excel file to storage
        history.excel_file.save(excel_path, excel_content)
        history.save()
        
        logger.info(f"Task {task_id} completed successfully with {len(cleaned_items)} results. History ID: {history.id}")
        
        # Update status to complete
        status["status"] = "completed"
        status["progress"] = 100
        status["message"] = f"Found {len(cleaned_items)} {data_type}s"
        status["results_count"] = len(cleaned_items)
        status["results"] = cleaned_items[:10]  # Include preview of first 10 results
        status["elapsed_time"] = elapsed_time
        status["history_id"] = history.id
        _update_status(status_file_path, status)
        
        # Update task record
        if task_record:
            from django.utils import timezone
            task_record.status = 'completed'
            task_record.progress = 100
            task_record.mining_history = history
            task_record.completed_at = timezone.now()
            task_record.save()
            logger.info(f"Updated task record {task_record.id} as completed")
        
        return {
            "success": True,
            "history_id": history.id,
            "results_count": len(cleaned_items),
            "elapsed_time": elapsed_time,
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Error scraping contacts for task {task_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Update status to error
        status["status"] = "error"
        status["message"] = f"Error: {str(e)}"
        status["elapsed_time"] = (time.time() - start_time) / 60.0
        _update_status(status_file_path, status)
        
        # Update task record
        if task_record:
            try:
                task_record.status = 'failed'
                task_record.error_message = str(e)
                from django.utils import timezone
                task_record.completed_at = timezone.now()
                task_record.save()
                logger.info(f"Updated task record {task_record.id} as failed")
            except Exception as e2:
                logger.error(f"Error updating task record on failure: {e2}")
        
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": (time.time() - start_time) / 60.0,
            "task_id": task_id
        }

def _update_status(status_file_path, status_data):
    """Update the status file with the latest status"""
    status_data["updated_at"] = datetime.now().isoformat()
    with open(status_file_path, 'w') as f:
        json.dump(status_data, f)
        
    # Also update the task record if task_id is present
    if "task_id" in status_data:
        try:
            task = BackgroundTask.objects.get(task_id=status_data["task_id"])
            task.progress = status_data.get("progress", task.progress)
            
            # Update status if it's provided
            status_mapping = {
                "processing": "processing",
                "completed": "completed", 
                "error": "failed",
                "cancelled": "cancelled"
            }
            if "status" in status_data and status_data["status"] in status_mapping:
                task.status = status_mapping[status_data["status"]]
                
            # Update error message if there's an error
            if status_data.get("status") == "error" and "message" in status_data:
                task.error_message = status_data["message"]
                
            task.save()
        except Exception as e:
            logger.error(f"Error updating task record from status: {e}") 