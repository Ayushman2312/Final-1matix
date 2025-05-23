from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse, FileResponse
from .scrapper import EnhancedContactScraper
from .web_scrapper import ContactScraper, run_web_scraper_task
from .models import MiningHistory, BackgroundTask
from .tasks import scrape_contacts, test_redis_connection, test_task_status
from .services import service_manager  # Original service manager
from .direct_services import ensure_services  # Direct service starter
import pandas as pd
import logging
import os
from django.conf import settings
import uuid
from datetime import datetime
import json
from openpyxl import Workbook
import asyncio
import time
import traceback
from celery.result import AsyncResult
from celery import current_app as celery_app
import threading
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Q

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatusView(View):
    """View for checking the status of background tasks"""
    
    def get(self, request, task_id):
        """Get the status of a background task"""
        if not task_id:
            return JsonResponse({"error": "No task ID provided"}, status=400)
        
        task_name = None
        history_id = None
            
        # First check if we have a database record for this task
        try:
            task_record = BackgroundTask.objects.get(task_id=task_id)
            task_name = task_record.task_name
            history_id = task_record.mining_history_id if task_record.mining_history else None
        except BackgroundTask.DoesNotExist:
            # If no database record, try to get info from the request user's stored tasks
            if request.user.is_authenticated:
                try:
                    # Check if this task was started by the current user and create a record
                    task_result = AsyncResult(task_id)
                    
                    # If the task exists in Celery and is for the current user, create a database record
                    if task_result.state != 'PENDING':
                        try:
                            # Try to get the task info from Celery
                            task_info = task_result.info
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
                return JsonResponse(status_data)
            except Exception as e:
                logger.error(f"Error reading task status file: {e}")
                return JsonResponse({"error": "Error reading task status"}, status=500)
        
        # If no status file, check Celery task status
        task_result = AsyncResult(task_id)
        if task_result.state == 'PENDING':
            return JsonResponse({
                "status": "pending",
                "message": "Task is pending",
                "progress": 0,
                "task_name": task_name,
                "history_id": history_id
            })
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            # For dictionary results, extract relevant information
            if isinstance(result, dict):
                return JsonResponse({
                    "status": "completed",
                    "message": "Task completed successfully",
                    "progress": 100,
                    "results_count": result.get('results_count', 0),
                    "history_id": result.get('history_id', history_id),
                    "task_name": task_name
                })
            else:
                return JsonResponse({
                    "status": "completed",
                    "message": "Task completed successfully",
                    "progress": 100,
                    "task_name": task_name,
                    "history_id": history_id
                })
        elif task_result.state == 'FAILURE':
            return JsonResponse({
                "status": "error",
                "message": f"Task failed: {str(task_result.result)}",
                "progress": 0,
                "task_name": task_name,
                "history_id": history_id
            })
        else:
            return JsonResponse({
                "status": task_result.state.lower(),
                "message": f"Task is {task_result.state}",
                "progress": 50,  # Default progress for unknown states
                "task_name": task_name,
                "history_id": history_id
            })


class BackgroundTasksView(LoginRequiredMixin, TemplateView):
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
                    # Get list of active tasks from Celery
                    active_tasks = inspect.active() or {}
                    scheduled_tasks = inspect.scheduled() or {}
                    reserved_tasks = inspect.reserved() or {}
                    
                    # Combine all tasks
                    all_celery_tasks = {}
                    for worker_tasks in [active_tasks, scheduled_tasks, reserved_tasks]:
                        if worker_tasks:  # Ensure worker_tasks is not None
                            for worker, tasks_list in worker_tasks.items():
                                for task_info in tasks_list:
                                    if task_info.get('name', '').startswith('data_miner.tasks.'):
                                        all_celery_tasks[task_info['id']] = task_info
                    
                    logger.info(f"Found {len(all_celery_tasks)} active Celery tasks for data_miner")
                except Exception as e:
                    logger.error(f"Error getting task information from Celery: {e}")
                    logger.error(traceback.format_exc())
                    all_celery_tasks = {}
            
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
            # Get the task
            task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
            
            # Only cancel tasks that are pending or processing
            if task.status not in ['pending', 'processing']:
                return JsonResponse({"error": "Task is not running"}, status=400)
            
            # Attempt to revoke the Celery task
            celery_task = AsyncResult(task_id)
            celery_task.revoke(terminate=True)
            
            # Update the task record
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save()
            
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
            return JsonResponse({"error": "Task not found"}, status=404)
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return JsonResponse({"error": f"Error cancelling task: {str(e)}"}, status=500)
    
    def delete_task(self, request, task_id):
        """Delete a task"""
        try:
            # Get the task
            task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
            
            # Delete the task
            task.delete()
            
            # Delete status file if it exists
            status_file_path = os.path.join(settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
            if os.path.exists(status_file_path):
                try:
                    os.remove(status_file_path)
                except Exception as e:
                    logger.error(f"Error deleting task status file: {e}")
            
            return JsonResponse({
                "success": True,
                "message": "Task deleted successfully"
            })
        except BackgroundTask.DoesNotExist:
            return JsonResponse({"error": "Task not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return JsonResponse({"error": f"Error deleting task: {str(e)}"}, status=500)


# Create your views here.
class DataMinerView(TemplateView):
    template_name = 'data miner/miner.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Data Mining Tool'
        # context['app_name'] = 'Welcome to the LeadX!'
        
        # Get recent mining history for the current user
        if self.request.user.is_authenticated:
            recent_minings = MiningHistory.objects.filter(user=self.request.user).order_by('-created_at')[:5]
            context['recent_minings'] = recent_minings
            
            # Get running background tasks
            running_tasks = BackgroundTask.objects.filter(
                user=self.request.user,
                status__in=['pending', 'processing']
            ).order_by('-created_at')
            context['running_tasks'] = running_tasks

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

    def dispatch(self, request, *args, **kwargs):
        # Check if an action is specified in kwargs
        action = kwargs.pop('action', None)
        if action:
            # Call the specified method
            if hasattr(self, action) and callable(getattr(self, action)):
                return getattr(self, action)(request, *args, **kwargs)
        # Otherwise use default dispatch
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Check if it's a download request
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                results = data.get('results', [])
                keyword = data.get('keyword', '')
                data_type = data.get('data_type', '')
                
                if not results:
                    return JsonResponse({'error': 'No results provided'}, status=400)
                if not keyword:
                    return JsonResponse({'error': 'No keyword provided'}, status=400)
                if not data_type:
                    return JsonResponse({'error': 'No data type provided'}, status=400)
                
                # Generate Excel file with the results
                excel_path = self.generate_excel(results, keyword, data_type)
                
                # Save to history if user is authenticated
                if request.user.is_authenticated:
                    history = MiningHistory(
                        user=request.user,
                        keyword=keyword,
                        country=data.get('country', 'IN'),
                        data_type=data_type,
                        results_count=len(results),
                        excel_file=excel_path
                    )
                    history.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Results saved to history',
                        'history_id': history.id
                    })
                else:
                    # For anonymous users, create a temporary download link
                    # Generate temporary file path for download
                    temp_filename = f"temp_{uuid.uuid4()}_{keyword.replace(' ', '_')}.xlsx"
                    temp_filepath = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
                    os.makedirs(os.path.dirname(temp_filepath), exist_ok=True)
                    
                    # Generate Excel directly
                    df = pd.DataFrame(results, columns=[data_type.capitalize()])
                    df.to_excel(temp_filepath, index=False)
                    
                    # Return temporary url
                    return JsonResponse({
                        'success': True,
                        'message': 'Results ready for download',
                        'temp_file': temp_filename
                    })
            except Exception as e:
                logger.error(f"Error in download request: {e}")
                logger.error(traceback.format_exc())
                return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
            
        if 'temp_file' in request.POST:
            # Handle temporary file download
            temp_filename = request.POST.get('temp_file')
            temp_filepath = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
            
            if not os.path.exists(temp_filepath):
                return JsonResponse({'error': 'File not found'}, status=404)
                
            # Open the file
            excel_file = open(temp_filepath, 'rb')
            
            # Create response
            keyword = '_'.join(temp_filename.split('_')[2:]).replace('.xlsx', '')
            
            response = HttpResponse(
                excel_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=mining_results_{keyword.replace(" ", "_")}.xlsx'
        
            # Clean up temporary file
            try:
                os.remove(temp_filepath)
            except:
                pass
                
            return response
                
        # If not a download request, proceed with the original post method
        try:
            # Get and validate input parameters
            keyword = request.POST.get('keyword', '').strip()
            data_type = request.POST.get('data_type', 'phone')  # 'phone' or 'email'
            country = request.POST.get('country', 'IN')  # Default to India
            max_results = 30  # Fixed to 30 results
            run_in_background = request.POST.get('background', 'true').lower() == 'true'  # Run in background by default

            # Validate keyword
            if not keyword:
                return JsonResponse({'error': 'Please enter a search keyword'}, status=400)
            
            if len(keyword) < 3:
                return JsonResponse({'error': 'Search keyword must be at least 3 characters long'}, status=400)

            # Validate data type
            if data_type not in ['phone', 'email']:
                return JsonResponse({'error': 'Invalid data type specified'}, status=400)

            # Check if we already have recent results for this search
            if request.user.is_authenticated:
                recent_mining = MiningHistory.objects.filter(
                    user=request.user,
                    keyword=keyword,
                    country=country,
                    data_type=data_type,
                    created_at__gte=datetime.now().replace(hour=0, minute=0, second=0)  # From today
                ).first()
                
                if recent_mining:
                    # Return cached results
                    try:
                        with open(recent_mining.excel_file.path, 'r') as f:
                            df = pd.read_excel(recent_mining.excel_file.path)
                            results = df[data_type.capitalize()].tolist()
                            return JsonResponse({
                                'success': True,
                                'data': {data_type + 's': results},
                                'message': f"Found {len(results)} results (cached)",
                                'elapsed_time': 0,
                                'history_id': recent_mining.id
                            })
                    except Exception as e:
                        logger.error(f"Error reading cached results: {e}")
                        # Continue with new search if cache read fails

            # Start a new Celery task
            logger.info(f"Starting background scraping task for keyword: {keyword}, data type: {data_type}")
            
            # Ensure Redis and Celery services are running before starting the task
            if run_in_background:
                logger.info("Ensuring background services are running...")
                
                # Use the direct services module to ensure Redis and Celery are running
                services_running = ensure_services()
                
                if not services_running:
                    logger.error("Failed to ensure background services are running")
                    return JsonResponse({
                        'error': 'Could not start background processing services. Please try again or contact support.'
                    }, status=500)
                    
                logger.info("Services are running and ready for background task")
            
            # Launch Celery task
            if request.user.is_authenticated:
                # Authenticated user - save the task
                task = scrape_contacts.delay(
                    keyword=keyword,
                    data_type=data_type,
                    country=country,
                    user_id=request.user.id,
                    max_results=max_results,
                    max_runtime_minutes=15
                )
                
                # Create a BackgroundTask record
                try:
                    task_record = BackgroundTask.objects.create(
                        task_id=task.id,
                        user=request.user,
                        task_name=f"Mining {data_type}s for '{keyword}'",
                        status='processing',
                        progress=0,
                        parameters={
                            'keyword': keyword,
                            'data_type': data_type,
                            'country': country,
                            'max_results': max_results,
                            'max_runtime_minutes': 15
                        },
                        created_at=timezone.now()
                    )
                    logger.info(f"Created BackgroundTask record {task_record.id} for task {task.id}")
                    
                    # Create the mining status directory if it doesn't exist
                    status_dir = os.path.join(settings.MEDIA_ROOT, 'mining_status')
                    os.makedirs(status_dir, exist_ok=True)
                    
                    # Create an initial status file
                    status_file_path = os.path.join(status_dir, f"{task.id}.json")
                    with open(status_file_path, 'w') as f:
                        status_data = {
                            "status": "processing",
                            "progress": 0,
                            "message": "Task started, initializing...",
                            "keyword": keyword,
                            "data_type": data_type,
                            "country": country,
                            "task_id": task.id,
                            "start_time": datetime.now().isoformat()
                        }
                        json.dump(status_data, f)
                except Exception as e:
                    logger.error(f"Error creating BackgroundTask record: {e}")
                
                return JsonResponse({
                    'success': True,
                    'task_id': task.id,
                    'message': f"Started background task for '{keyword}'",
                })
            else:
                # Anonymous user - use in-process search
                # Initialize the improved scraper
                scraper = ContactScraper(
                    use_browser=True,
                    debug_mode=False
                )
                
                # Start time for scraping
                start_time = time.time()
                
                # Run the search in a thread
                def run_search():
                    try:
                        # First attempt with fewer pages for quick results
                        logger.info(f"Starting search for {keyword} with data type {data_type}")
                        results = scraper.scrape(
                            keyword=keyword,
                            num_results=max_results,
                            max_runtime_minutes=5  # Shorter time for in-process search
                        )
                        
                        # Clean up resources (especially browser)
                        try:
                            import asyncio
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(scraper.close_browser())
                            loop.close()
                        except Exception as e:
                            logger.error(f"Error closing browser: {e}")
                    except Exception as e:
                        logger.error(f"Error in search thread: {e}")
                        logger.error(traceback.format_exc())
                
                # Start search in background thread
                search_thread = threading.Thread(target=run_search)
                search_thread.daemon = True
                search_thread.start()
                
                # Return immediate response
                return JsonResponse({
                    'success': True,
                    'message': f"Started search for '{keyword}'",
                    'in_process': True
                })
                
        except Exception as e:
            logger.error(f"Error in POST request: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

    def get_excel(self, request, history_id):
        """Download Excel file for a specific mining history"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
                
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
            task = None
            if request.user.is_authenticated:
                try:
                    task = BackgroundTask.objects.get(task_id=task_id, user=request.user)
                    # Update the task record
                    task.status = 'cancelled'
                    task.completed_at = timezone.now()
                    task.save()
                except BackgroundTask.DoesNotExist:
                    pass
            
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
            if request.user.is_authenticated:
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
