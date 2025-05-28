"""
Import the main Celery app to avoid having multiple Celery app instances.
"""
from matrix.celery import app

# Export the app
__all__ = ['app']

# Register tasks with the main app
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Note: Task routing and other Celery configurations are defined in the main matrix/celery.py file 