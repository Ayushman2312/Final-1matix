import logging
import os
import json
import traceback
import socket
from datetime import datetime
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from celery.result import AsyncResult
from matrix.celery import app as celery_app
from redis.exceptions import ConnectionError as RedisConnectionError
from .models import MiningHistory, BackgroundTask
from .web_scrapper import ContactScraper
from .tasks import  test_redis_connection, test_task_status
from .services import service_manager  # Original service manager
from .direct_services import *
import pandas as pd
import uuid
import asyncio
from django.db.utils import OperationalError as DjangoOperationalError
from requests.exceptions import ConnectionError as RequestsConnectionError
from django.contrib.auth.mixins import LoginRequiredMixin
# Celery/kombu imports for error handling
try:
    from kombu.exceptions import OperationalError as KombuOperationalError
    from kombu.exceptions import ConnectionError as KombuConnectionError
except ImportError:
    KombuOperationalError = None
    KombuConnectionError = None

# Configure logging
logger = logging.getLogger('django.request')

def ensure_services_running():
    """
    Check if required background services (Redis, Celery) are running
    and start them if needed.
    
    Returns:
        bool: True if services are running, False otherwise
    """
    try:
        # First check if Redis is accessible directly
        try:
            from redis import Redis
            from django.conf import settings
            
            # Get Redis URL from settings or use default
            broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            if broker_url.startswith('redis://'):
                # Parse Redis connection details
                redis_host = broker_url.split('@')[-1].split(':')[0] or 'localhost'
                redis_port = int(broker_url.split(':')[-1].split('/')[0] or 6379)
                
                # Test connection with timeout
                redis_client = Redis(host=redis_host, port=redis_port, socket_timeout=2)
                redis_running = redis_client.ping()
                
                logger.info(f"Direct Redis connection check: {'successful' if redis_running else 'failed'}")
                
                if redis_running:
                    return True
            else:
                logger.warning(f"Unsupported broker URL format: {broker_url}")
        except Exception as redis_check_error:
            logger.warning(f"Error checking Redis directly: {redis_check_error}")
        
        # If direct check failed, try using the service manager
        try:
            from .direct_services import check_services, start_services
            
            # Check if services are running
            services = check_services()
            redis_running = services.get('redis', False)
            celery_running = services.get('celery', False)
            
            logger.info(f"Service check - Redis: {redis_running}, Celery: {celery_running}")
            
            # If Redis is not running, try to start it
            if not redis_running:
                logger.info("Redis is not running. Attempting to start...")
                start_result = start_services()
                
                if start_result.get('success', False):
                    logger.info("Successfully started Redis service")
                    return True
                else:
                    logger.warning(f"Failed to start Redis: {start_result.get('message', 'Unknown error')}")
                    return False
            
            return redis_running
            
        except ImportError:
            logger.warning("direct_services module could not be imported. Cannot check or start services.")
            return False
            
    except Exception as e:
        logger.error(f"Error checking/starting services: {str(e)}")
        logger.error(traceback.format_exc())
        return False

class TaskStatusView(View):
    """View for checking the status of background tasks"""
    
    def get(self, request, task_id):
        """Get the status of a background task"""
        if not task_id:
            return JsonResponse({"error": "No task ID provided"}, status=400)
        
        task_name = None
        history_id = None
        parameters = None
            
        # First check if we have a database record for this task
        try:
            task_record = BackgroundTask.objects.get(task_id=task_id)
            task_name = task_record.task_name
            history_id = task_record.mining_history_id if task_record.mining_history else None
            parameters = task_record.parameters
        except BackgroundTask.DoesNotExist:
            # If no database record, try to get info from the request user's stored tasks
            if request.user.is_authenticated:
                try:
                    # Check if this task was started by the current user and create a record
                    from celery.result import AsyncResult
                    task_result = AsyncResult(task_id)
                    
                    # If the task exists in Celery and is for the current user, create a database record
                    if task_result.state != 'PENDING':
                        try:
                            # Try to get the task info from Celery
                            task_info = task_result.info if hasattr(task_result, 'info') else {}
                            user_id = None
                            
                            # If task_info is a dict, try to extract user_id
                            if isinstance(task_info, dict):
                                user_id = task_info.get('user_id')
                            
                            # Create a background task record if this is the user's task
                            if user_id == request.user.id or request.user.is_staff:
                                from django.utils import timezone
                                task_record = BackgroundTask(
                                    task_id=task_id,
                                    user=request.user,
                                    task_name="Data Mining Task",
                                    status='completed' if task_result.state == 'SUCCESS' else 'processing',
                                    progress=100 if task_result.state == 'SUCCESS' else 50,
                                    created_at=timezone.now()
                                )
                                
                                # Save the record to the database
                                task_record.save()
                                
                                # Update variables for the response
                                task_name = task_record.task_name
                        except Exception as e:
                            logger.error(f"Error creating task record: {e}")
                except Exception as e:
                    logger.error(f"Error checking Celery task: {e}")
            
            # If we still don't have a task_name, use a default
            if not task_name:
                task_name = "Data Mining Task"
            
        # Check if task status file exists
        status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
        if os.path.exists(status_file_path):
            try:
                with open(status_file_path, 'r') as f:
                    status_data = json.load(f)
                # Add task name and history ID if available
                if task_name:
                    status_data["task_name"] = task_name
                if history_id:
                    status_data["history_id"] = history_id
                if parameters:
                    status_data["parameters"] = parameters
                return JsonResponse(status_data)
            except Exception as e:
                logger.error(f"Error reading task status file: {e}")
                return JsonResponse({"error": "Error reading task status"}, status=500)
        
        # If no status file, check Celery task status
        try:
            from celery.result import AsyncResult
            task_result = AsyncResult(task_id)
            
            try:
                # Try to safely get the state
                state = task_result.state
            except AttributeError:
                # Handle the case where _get_task_meta_for is missing
                logger.error("Backend error: AttributeError in AsyncResult.state")
                return JsonResponse({
                    "status": "unknown",
                    "message": "Task status could not be determined",
                    "progress": 0,
                    "task_name": task_name,
                    "history_id": history_id,
                    "parameters": parameters
                })
                
            if state == 'PENDING':
                return JsonResponse({
                    "status": "pending",
                    "message": "Task is pending",
                    "progress": 0,
                    "task_name": task_name,
                    "history_id": history_id,
                    "parameters": parameters
                })
            elif state == 'SUCCESS':
                try:
                    result = task_result.result
                    # For dictionary results, extract relevant information
                    if isinstance(result, dict):
                        # Extract results data if available
                        results_data = {}
                        if 'emails' in result:
                            results_data['emails'] = result['emails']
                        if 'phones' in result:
                            results_data['phones'] = result['phones']
                        
                        response_data = {
                            "status": "completed",
                            "message": "Task completed successfully",
                            "progress": 100,
                            "results_count": result.get('results_count', 0),
                            "history_id": result.get('history_id', history_id),
                            "task_name": task_name,
                            "parameters": parameters
                        }
                        
                        # Add results data if available
                        if results_data:
                            response_data["results"] = results_data
                            
                        return JsonResponse(response_data)
                    else:
                        return JsonResponse({
                            "status": "completed",
                            "message": "Task completed successfully",
                            "progress": 100,
                            "task_name": task_name,
                            "history_id": history_id,
                            "parameters": parameters
                        })
                except Exception as e:
                    logger.error(f"Error getting task result: {e}")
                    return JsonResponse({
                        "status": "completed",
                        "message": "Task completed but result could not be retrieved",
                        "progress": 100,
                        "task_name": task_name,
                        "history_id": history_id,
                        "parameters": parameters
                    })
            elif state == 'FAILURE':
                error_msg = str(task_result.result) if hasattr(task_result, 'result') else "Unknown error"
                return JsonResponse({
                    "status": "error",
                    "message": f"Task failed: {error_msg}",
                    "progress": 0,
                    "task_name": task_name,
                    "history_id": history_id,
                    "parameters": parameters
                })
            else:
                # Try to get current results for STARTED/PROGRESS states
                current_results = None
                try:
                    # If the task has a get_progress method or info attribute, try to get current results
                    if hasattr(task_result, 'info') and isinstance(task_result.info, dict):
                        task_info = task_result.info
                        current_progress = task_info.get('progress', 50)
                        
                        # Check for partial results data
                        if 'partial_results' in task_info:
                            current_results = task_info['partial_results']
                        elif 'emails' in task_info or 'phones' in task_info:
                            current_results = {
                                'emails': task_info.get('emails', []),
                                'phones': task_info.get('phones', [])
                            }
                except Exception as e:
                    logger.error(f"Error getting current results: {e}")
                
                response_data = {
                    "status": state.lower(),
                    "message": f"Task is {state}",
                    "progress": 50,  # Default progress for unknown states
                    "task_name": task_name,
                    "history_id": history_id,
                    "parameters": parameters
                }
                
                # Add current results if available
                if current_results:
                    response_data["results"] = current_results
                
                return JsonResponse(response_data)
        except Exception as e:
            logger.error(f"Error checking task status: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Error checking task status: {str(e)}",
                "progress": 0,
                "task_name": task_name,
                "history_id": history_id,
                "parameters": parameters
            })


class BackgroundTasksView(TemplateView):
    """View for managing background tasks"""
    template_name = 'data miner/background_tasks.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Background Tasks'
        context['app_name'] = 'Welcome to the LeadX!'
        
        # Get all background tasks for the current user, including any from Celery that might not be in the database
        tasks = list(BackgroundTask.objects.filter(user=self.request.user).order_by('-created_at'))
        
        # Check if we need to add any missing tasks from Celery
        try:
            # Try to get the Celery inspect instance
            try:
                # Get the inspect instance from the current app
                inspect = celery_app.control.inspect()
                logger.info("Successfully obtained Celery inspector from current app")
            except Exception as e:
                logger.warning(f"Could not get Celery inspector from current app: {e}")
                inspect = None
            
            if inspect is None:
                logger.warning("Celery inspector is None, checking stored tasks from cookies")
                all_celery_tasks = {}
            else:
                try:
                    # Try to connect with timeout to avoid hanging
                    from kombu.exceptions import OperationalError, ConnectionError as KombuConnectionError
                    
                    # Set up all_celery_tasks before any potential exception
                    all_celery_tasks = {}
                    
                    # First test Redis connection (only if using Redis)
                    broker_url = getattr(settings, 'CELERY_BROKER_URL', '')
                    if broker_url.startswith('redis://'):
                        try:
                            from redis import Redis
                            from redis.exceptions import ConnectionError as RedisConnectionError
                            
                            redis_host = broker_url.split('@')[-1].split(':')[0] or 'localhost'
                            redis_port = int(broker_url.split(':')[-1].split('/')[0] or 6379)
                            
                            # Test connection with timeout
                            redis_client = Redis(host=redis_host, port=redis_port, socket_timeout=3)
                            if not redis_client.ping():
                                logger.warning("Redis ping failed, skipping Celery task checks")
                                raise RedisConnectionError("Redis ping failed") from e
                        except (RedisConnectionError, socket.gaierror) as e:
                            logger.warning(f"Redis connection error: {e}")
                            raise KombuConnectionError("Redis connection failed") from e
                    
                    # Get list of active tasks from Celery with timeout
                    socket.setdefaulttimeout(5)  # 5 second timeout for network operations
                    
                    active_tasks = inspect.active() or {}
                    scheduled_tasks = inspect.scheduled() or {}
                    reserved_tasks = inspect.reserved() or {}
                    
                    # Combine all tasks
                    for worker_tasks in [active_tasks, scheduled_tasks, reserved_tasks]:
                        if worker_tasks:  # Ensure worker_tasks is not None
                            for worker, tasks_list in worker_tasks.items():
                                for task_info in tasks_list:
                                    if task_info.get('name', '').startswith('data_miner.tasks.'):
                                        all_celery_tasks[task_info['id']] = task_info
                    
                    logger.info(f"Found {len(all_celery_tasks)} active Celery tasks for data_miner")
                    
                except (KombuConnectionError, OperationalError) as e:
                    # Handle connection errors gracefully
                    logger.warning(f"Could not connect to message broker: {e}")
                    
                except socket.timeout:
                    # Handle timeout errors
                    logger.warning("Timeout connecting to message broker")
                    
                except Exception as e:
                    logger.error(f"Error getting task information from Celery: {e}")
                    logger.error(traceback.format_exc())
            
            # Find any tasks in Celery but not in our database
            db_task_ids = {t.task_id for t in tasks}
            
            for task_id, task_info in all_celery_tasks.items():
                if task_id not in db_task_ids:
                    # Task exists in Celery but not in our database
                    # Try to reconstruct task for the current user
                    args = task_info.get('args', [])
                    kwargs = task_info.get('kwargs', {})
                    
                    # Check if this task belongs to the current user
                    task_user_id = kwargs.get('user_id')
                    if not task_user_id and len(args) >= 4:
                        task_user_id = args[3]
                    
                    if task_user_id == self.request.user.id:
                        # This task belongs to the current user, create a record for it
                        keyword = kwargs.get('keyword', '') if kwargs else (args[0] if args else '')
                        data_type = kwargs.get('data_type', '') if kwargs else (args[1] if len(args) > 1 else '')
                        
                        # Create a BackgroundTask record
                        new_task = BackgroundTask(
                            task_id=task_id,
                            user=self.request.user,
                            task_name=f"Mining {data_type}s for '{keyword}'",
                            status='processing',
                            progress=0,
                            created_at=timezone.now(),
                            parameters={
                                'keyword': keyword,
                                'data_type': data_type,
                                'country': kwargs.get('country', '') if kwargs else (args[2] if len(args) > 2 else ''),
                                'max_results': kwargs.get('max_results', 30),
                                'max_runtime_minutes': kwargs.get('max_runtime_minutes', 15)
                            }
                        )
                        # Save the task to the database
                        new_task.save()
                        logger.info(f"Created new BackgroundTask record for Celery task {task_id}")
                        
                        # Add it to our tasks list
                        tasks.append(new_task)
                    
        except Exception as e:
            logger.error(f"Error checking Celery for missing tasks: {e}")
            logger.error(traceback.format_exc())
            
            # Fallback: Check localStorage saved tasks from browser
            # Get any task IDs from the user's request cookies
            stored_tasks_cookie = self.request.COOKIES.get('dataMinerTasks', '')
            if stored_tasks_cookie:
                try:
                    import json
                    # Try to parse saved task IDs - handle both quoted and unquoted strings
                    stored_tasks_cookie = stored_tasks_cookie.strip()
                    
                    # Try to handle both quoted and unquoted JSON
                    if stored_tasks_cookie.startswith('"') and stored_tasks_cookie.endswith('"'):
                        # Remove the outer quotes and handle escaped content
                        stored_tasks_cookie = stored_tasks_cookie[1:-1].replace('\\"', '"')
                    
                    # Try to parse the JSON
                    stored_task_ids = json.loads(stored_tasks_cookie)
                    
                    if isinstance(stored_task_ids, list):
                        db_task_ids = {t.task_id for t in tasks}
                        
                        # Check each stored task ID
                        for task_id in stored_task_ids:
                            if task_id and task_id not in db_task_ids:
                                # Try to get task info from Celery
                                try:
                                    task_result = AsyncResult(task_id)
                                    if task_result.state != 'PENDING':
                                        # Create a proper BackgroundTask record
                                        task_record = BackgroundTask(
                                            task_id=task_id,
                                            user=self.request.user,
                                            task_name="Mining task (from browser storage)",
                                            status='processing' if task_result.state == 'STARTED' else 
                                                  'completed' if task_result.state == 'SUCCESS' else
                                                  'failed' if task_result.state == 'FAILURE' else 'processing',
                                            progress=100 if task_result.state == 'SUCCESS' else 0,
                                            created_at=timezone.now()
                                        )
                                        task_record.save()
                                        tasks.append(task_record)
                                        logger.info(f"Created BackgroundTask record for task {task_id} from cookie")
                                    else:
                                        # Add a temporary task
                                        temp_task = BackgroundTask(
                                            task_id=task_id,
                                            user=self.request.user,
                                            task_name="Mining task (pending)",
                                            status='pending',
                                            progress=0,
                                            created_at=timezone.now()
                                        )
                                        tasks.append(temp_task)
                                except Exception as e:
                                    logger.error(f"Error checking task {task_id} from cookie: {e}")
                                    # Create a temporary task anyway
                                    temp_task = BackgroundTask(
                                        task_id=task_id,
                                        user=self.request.user,
                                        task_name="Mining task (reconstructed)",
                                        status='processing',
                                        progress=0,
                                        created_at=timezone.now()
                                    )
                                    tasks.append(temp_task)
                except Exception as cookie_error:
                    logger.error(f"Error processing stored tasks cookie: {cookie_error}")
        
        # Filter by search keyword if provided
        search_keyword = self.request.GET.get('search', '').strip()
        if search_keyword:
            # Filter tasks where keyword appears in parameters.keyword or task_name
            # Using list comprehension since some tasks might be temporary objects
            tasks = [
                task for task in tasks 
                if search_keyword.lower() in task.task_name.lower() 
                or (task.parameters and 'keyword' in task.parameters and search_keyword.lower() in task.parameters['keyword'].lower())
            ]
            context['search_keyword'] = search_keyword
            
        context['tasks'] = tasks
        
        # Get running tasks
        running_tasks = [task for task in tasks if task.status in ['pending', 'processing']]
        context['running_tasks'] = running_tasks
        
        # Get completed tasks
        completed_tasks = [task for task in tasks if task.status in ['completed', 'failed', 'cancelled']]
        context['completed_tasks'] = completed_tasks
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests for task management"""
        action = request.POST.get('action')
        task_id = request.POST.get('task_id')
        
        if not task_id:
            return JsonResponse({"error": "No task ID provided"}, status=400)
            
        if action == 'cancel':
            return self.cancel_task(request, task_id)
        elif action == 'delete':
            return self.delete_task(request, task_id)
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)
    
    def cancel_task(self, request, task_id):
        """Cancel a running task"""
        try:
            logger.info(f"Received cancel request for task {task_id}")
            
            # Get the task
            task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
            logger.info(f"Found task record for {task_id}, current status: {task.status}")
            
            # Only cancel tasks that are pending or processing
            if task.status not in ['pending', 'processing']:
                logger.warning(f"Cannot cancel task {task_id} as it is not running (status: {task.status})")
                return JsonResponse({"error": "Task is not running"}, status=400)
            
            # Attempt to revoke the Celery task with a timeout to prevent hanging
            try:
                # Set a short socket timeout to prevent hanging
                import socket
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(5)  # 5 second timeout
                
                try:
                    celery_task = AsyncResult(task_id)
                    celery_task.revoke(terminate=True)
                    logger.info(f"Successfully revoked Celery task {task_id}")
                except (socket.timeout, socket.error) as sock_error:
                    # Socket timeout - log and continue
                    logger.warning(f"Socket timeout while revoking task {task_id}: {sock_error}")
                except Exception as celery_error:
                    # Log the error but continue - we'll still mark it as cancelled in our DB
                    logger.error(f"Error revoking Celery task {task_id}: {celery_error}")
                finally:
                    # Reset socket timeout
                    socket.setdefaulttimeout(old_timeout)
            except ImportError:
                logger.warning("Could not set socket timeout - module not available")
                try:
                    celery_task = AsyncResult(task_id)
                    celery_task.revoke(terminate=True)
                except Exception as e:
                    logger.error(f"Error revoking task without timeout protection: {e}")
            
            # Update the task record regardless of Celery revoke success
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save()
            logger.info(f"Successfully updated task {task_id} status to cancelled")
            
            # Update status file if it exists
            status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
            if os.path.exists(status_file_path):
                try:
                    with open(status_file_path, 'r') as f:
                        status_data = json.load(f)
                    
                    status_data["status"] = "cancelled"
                    status_data["message"] = "Task was cancelled by user"
                    
                    with open(status_file_path, 'w') as f:
                        json.dump(status_data, f)
                    logger.info(f"Successfully updated status file for task {task_id}")
                except Exception as file_error:
                    logger.error(f"Error updating task status file: {file_error}")
            
            return JsonResponse({
                "success": True,
                "message": "Task cancelled successfully"
            })
        except BackgroundTask.DoesNotExist:
            logger.warning(f"Task {task_id} not found when attempting to cancel")
            return JsonResponse({"error": "Task not found"}, status=404)
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({"error": f"Error cancelling task: {str(e)}"}, status=500)
    
    def delete_task(self, request, task_id):
        """Delete a task"""
        try:
            logger.info(f"Received delete request for task {task_id}")
            
            # Get the task
            task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
            logger.info(f"Found task record for {task_id}, current status: {task.status}")
            
            # For running tasks, try to revoke them first
            if task.status in ['pending', 'processing']:
                try:
                    # Set a short socket timeout to prevent hanging
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(5)  # 5 second timeout
                    
                    try:
                        celery_task = AsyncResult(task_id)
                        celery_task.revoke(terminate=True)
                        logger.info(f"Successfully revoked Celery task {task_id} before deletion")
                    except (socket.timeout, socket.error) as sock_error:
                        logger.warning(f"Socket timeout while revoking task {task_id} before deletion: {sock_error}")
                    except Exception as celery_error:
                        logger.error(f"Error revoking Celery task {task_id} before deletion: {celery_error}")
                    finally:
                        # Reset socket timeout
                        socket.setdefaulttimeout(old_timeout)
                except ImportError:
                    logger.warning("Could not set socket timeout - module not available")
            
            # Delete the task record
            task.delete()
            logger.info(f"Successfully deleted task record for {task_id}")
            
            # Delete status file if it exists
            status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
            if os.path.exists(status_file_path):
                try:
                    os.remove(status_file_path)
                    logger.info(f"Successfully deleted status file for task {task_id}")
                except Exception as e:
                    logger.error(f"Error deleting task status file: {e}")
            
            return JsonResponse({
                "success": True,
                "message": "Task deleted successfully"
            })
        except BackgroundTask.DoesNotExist:
            logger.warning(f"Task {task_id} not found when attempting to delete")
            return JsonResponse({"error": "Task not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({"error": f"Error deleting task: {str(e)}"}, status=500)


# Create your views here.
class DataMinerView(TemplateView):
    template_name = 'data miner/miner.html'
    login_url = '/accounts/login/'  # Specify the login URL to match Django-allauth
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Data Mining Tool'
        
        # Get recent mining history for the current user
        context['recent_minings'] = MiningHistory.objects.filter(user=self.request.session.get('user_id')).order_by('-created_at')[:5]
        
        # Get running background tasks
        context['running_tasks'] = BackgroundTask.objects.filter(
            user=self.request.session.get('user_id'),
            status__in=['pending', 'processing']
        ).order_by('-created_at')

        # If this is a GET request with search parameters, perform the search
        if self.request.method == 'GET' and 'keyword' in self.request.GET:
            try:
                keyword = self.request.GET.get('keyword', '').strip()
                data_type = self.request.GET.get('data_type', 'phone')
                country = self.request.GET.get('country', 'IN')
                
                if keyword and len(keyword) >= 3:
                    # Initialize improved ContactScraper
                    scraper = ContactScraper(
                        use_browser=True,
                        debug_mode=False
                    )
                    
                    try:
                        results = scraper.scrape(
                            keyword=keyword,
                            num_results=30,
                            max_runtime_minutes=5  # Keep initial search short
                        )
                        
                        if results and ('error' not in results or not results['error']):
                            if data_type == 'phone':
                                phones = results.get('phones', [])
                                # Convert phone dictionaries to strings if needed
                                cleaned_phones = []
                                for phone in phones:
                                    if isinstance(phone, dict) and 'phone' in phone:
                                        cleaned_phones.append(phone['phone'])
                                    else:
                                        cleaned_phones.append(str(phone))
                                
                                context['initial_results'] = {
                                    'success': True,
                                    'data': {'phones': cleaned_phones},
                                    'message': f"Found {len(cleaned_phones)} phone numbers"
                                }
                            else:  # email
                                context['initial_results'] = {
                                    'success': True,
                                    'data': {'emails': results.get('emails', [])},
                                    'message': f"Found {len(results.get('emails', []))} emails"
                                }
                        else:
                            context['initial_results'] = {
                                'error': results.get('error', 'No results found')
                            }
                    finally:
                        # Ensure browser is closed
                        try:
                            # Create a new event loop for cleanup and make sure it gets closed properly
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(scraper.close_browser())
                            except Exception as e:
                                logger.error(f"Error during browser cleanup: {e}")
                            finally:
                                try:
                                    # Make sure to close the loop to release resources
                                    loop.close()
                                except Exception as e:
                                    logger.error(f"Error closing cleanup loop: {e}")
                        except Exception as e:
                            logger.error(f"Error in cleanup: {e}")
                        
            except Exception as e:
                logger.error(f"Error in GET request search: {e}")
                logger.error(traceback.format_exc())
                context['initial_results'] = {
                    'error': 'An error occurred during the search'
                }
        
        return context

    def generate_excel(self, results, keyword, data_type):
        # Create a DataFrame
        df = pd.DataFrame(results, columns=[data_type.capitalize()])
        
        # Generate unique filename
        filename = f"mining_results_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(settings.MEDIA_ROOT, 'mining_results', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save to Excel
        df.to_excel(filepath, index=False)
        
        # Return relative path from MEDIA_ROOT
        return os.path.join('mining_results', filename)


    def post(self, request):
        """Handle POST request for initiating a scraping task."""
        try:
            keyword = request.POST.get('keyword', '')
            data_type = request.POST.get('data_type', 'phone')
            country = request.POST.get('country', 'IN')
            
            logger.info(f"Starting SerpAPI scraping for keyword: {keyword}, data type: {data_type}, country: {country}")
            
            # Initialize the SerpAPI scraper for real-time processing
            from .scrap import scrape_with_serpapi
            
            try:
                # Create a task ID for tracking
                task_id = str(uuid.uuid4())
                
                # Create a background task record
                task_record = BackgroundTask.objects.create(
                    user=request.user,
                    task_id=task_id,
                    task_name=f"Mining {data_type}s for '{keyword}'",
                    status='processing',
                    parameters={
                        'keyword': keyword,
                        'data_type': data_type,
                        'country': country
                    },
                    progress=0
                )
                
                # Execute SerpAPI scraping
                results = scrape_with_serpapi(
                    keyword=keyword,
                    data_type=data_type,
                    country=country,
                    task_id=task_id,
                    max_results=30
                )
                
                if results and results.get('success', False):
                    # Get the results list based on data type
                    result_items = results.get('results', [])
                    
                    # Save the mining history
                    excel_path = self.generate_excel(
                        result_items,
                        keyword,
                        data_type
                    )
                    
                    mining_history = MiningHistory.objects.create(
                        user=request.user,
                        keyword=keyword,
                        data_type=data_type,
                        country=country,
                        results_count=len(result_items),
                        excel_file=excel_path
                    )
                    
                    # Link the task record to the history
                    task_record.mining_history = mining_history
                    task_record.status = 'completed'
                    task_record.progress = 100
                    task_record.save()
                    
                    # Prepare context for rendering
                    context = {
                        'success': True,
                        'data': {data_type + 's': result_items},
                        'message': f"Found {len(result_items)} {data_type}s",
                        'history_id': mining_history.id
                    }
                    
                    # Get additional context data
                    additional_context = self.get_context_data()
                    context.update(additional_context)
                    
                    return render(request, self.template_name, context)
                else:
                    # Handle error case
                    error_msg = results.get('error', 'No results found or an error occurred')
                    logger.error(f"Error in SerpAPI search: {error_msg}")
                    
                    # Update task record
                    task_record.status = 'failed'
                    task_record.error_message = error_msg
                    task_record.save()
                    
                    # Prepare error context
                    context = self.get_context_data()
                    context.update({
                        'error': error_msg
                    })
                    
                    return render(request, self.template_name, context)
            
            except Exception as inner_e:
                logger.error(f"Error during SerpAPI scraping: {inner_e}")
                logger.error(traceback.format_exc())
                
                # Prepare error context
                context = self.get_context_data()
                context.update({
                    'error': f"Error during scraping: {str(inner_e)}"
                })
                
                return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in POST request: {e}")
            logger.error(traceback.format_exc())
            
            # Prepare error context
            context = self.get_context_data()
            context.update({
                'error': f"An error occurred: {str(e)}"
            })
            
            return render(request, self.template_name, context)

    def get_excel(self, request, history_id):
        """Download Excel file for a specific mining history"""
        try:
            # Get the mining history
            mining = MiningHistory.objects.get(id=history_id, user=request.user)
            
            # Check if file exists
            if not mining.excel_file or not os.path.exists(mining.excel_file.path):
                return JsonResponse({'error': 'Excel file not found'}, status=404)
                
            # Serve the file
            response = FileResponse(
                open(mining.excel_file.path, 'rb'),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename={os.path.basename(mining.excel_file.name)}'
            
            return response
            
        except MiningHistory.DoesNotExist:
            return JsonResponse({'error': 'Mining history not found'}, status=404)
        except Exception as e:
            logger.error(f"Error downloading Excel file: {e}")
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
            
    def cancel_task(self, request, task_id):
        """Cancel a running task"""
        if not task_id:
            return JsonResponse({"error": "No task ID provided"}, status=400)
            
        try:
            # Get the task from our database if it exists
            task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
            # Update the task record
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save()
            
            # Attempt to revoke the Celery task
            celery_task = AsyncResult(task_id)
            celery_task.revoke(terminate=True)
            
            # Update status file if it exists
            status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
            if os.path.exists(status_file_path):
                try:
                    with open(status_file_path, 'r') as f:
                        status_data = json.load(f)
                    
                    status_data["status"] = "cancelled"
                    status_data["message"] = "Task was cancelled by user"
                    
                    with open(status_file_path, 'w') as f:
                        json.dump(status_data, f)
                except Exception as e:
                    logger.error(f"Error updating task status file: {e}")
            
            return JsonResponse({
                "success": True,
                "message": "Task cancelled successfully"
            })
        except BackgroundTask.DoesNotExist:
            # If the task doesn't exist in our DB, we can still try to revoke it in Celery
            celery_task = AsyncResult(task_id)
            celery_task.revoke(terminate=True)
            return JsonResponse({
                "success": True, 
                "message": "Task not found in database, but cancellation requested in Celery."
            })
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return JsonResponse({
                "error": f"Error cancelling task: {str(e)}"
            }, status=500)


class TestCeleryView(View):
    """View for testing Celery task creation and execution"""
    
    def get(self, request):
        """Run a simple test Celery task and return its ID"""
        try:
            # Run a test task that will update its status
            if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
                task = test_task_status.delay(user_id=request.user.id)
                
                # Create a BackgroundTask record
                try:
                    task_record = BackgroundTask.objects.create(
                        task_id=task.id,
                        user=request.user,
                        task_name="Test Task Status Updates",
                        status='processing',
                        progress=0,
                        parameters={'test': True},
                        created_at=timezone.now()
                    )
                    logger.info(f"Created test task record: {task_record.id}")
                except Exception as e:
                    logger.error(f"Error creating test task record: {e}")
                
                return JsonResponse({
                    'success': True,
                    'task_id': task.id,
                    'message': "Started test task. Check the background tasks page for progress."
                })
            else:
                # For anonymous users, just return a quick status
                task = test_redis_connection.delay()
                return JsonResponse({
                    'success': True,
                    'task_id': task.id,
                    'message': "Started Redis test. This will not be tracked in the UI."
                })
        except Exception as e:
            logger.error(f"Error testing Celery: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': f"Error testing Celery: {str(e)}"
            }, status=500)
