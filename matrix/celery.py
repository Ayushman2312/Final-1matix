"""
import os
# from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')

# Create the Celery app
# app = Celery('matrix')

# Load config from Django settings, using a namespace to prevent clashes
# app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
# app.autodiscover_tasks()

# Configure task routing
"""

"""
app.conf.update(
    task_routes={
        # High priority queue for data mining tasks
        'data_miner.tasks.*': {'queue': 'data_mining'},
        # Specific routing for the scrape_contacts task
        'data_miner.tasks.scrape_contacts': {'queue': 'high_priority'},
    },
    task_time_limit=3600,  # 1 hour time limit per task
    worker_max_tasks_per_child=500,  # Restart worker after 500 tasks to prevent memory leaks
    worker_prefetch_multiplier=1,  # Process one task at a time
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,  # Retry connecting to broker if connection fails
    broker_connection_max_retries=None,  # Retry forever
    task_acks_late=True,  # Only acknowledge tasks after they are completed
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies
    worker_concurrency=2,  # Number of concurrent worker processes/threads
)
"""

"""
@app.task(bind=True)
def debug_task(self):
    '''Basic debugging task'''
    return {
        'task_id': self.request.id,
        'args': self.request.args,
        'kwargs': self.request.kwargs,
        'status': 'Debugging task executed successfully'
    } 
"""

# Dummy app for imports that expect a Celery app
# class DummyApp:
#     def task(self, *args, **kwargs):
#         def decorator(func):
#             return func
#         return decorator
    
#     def autodiscover_tasks(self, *args, **kwargs):
#         pass
    
#     def config_from_object(self, *args, **kwargs):
#         pass

# app = DummyApp() 