# Redis Setup for 1Matrix Data Mining

This document explains how to set up and use Redis as the message broker for Celery in the 1Matrix project.

## Automatic Service Management

The data mining app now includes automatic service management! The application will **automatically start Redis and Celery** when needed, so you don't have to manually start these services anymore.

### How It Works

1. When a user submits a data mining request (keyword search for emails or phone numbers)
2. The application automatically checks if Redis is running
3. If Redis is not running, it starts the Redis server in the background
4. It then checks if a Celery worker is available 
5. If no worker is running, it starts a Celery worker
6. Finally, it submits the task to the worker

All of this happens seamlessly without user intervention.

## Manual Service Management (Optional)

If you prefer to manually control the services, you can still use the management commands or batch files.

### Using Django Management Commands

Start both services:
```
python manage.py vices start
```

Check service status:
```
python manage.py manage_services status
```

Stop services:
```
python manage.py manage_services stop
```

You can also specify which service to manage:
```
python manage.py manage_services start --service=redis
python manage.py manage_services start --service=celery
```

### Using Batch Files (Legacy)

1. Double-click the `start_redis.bat` file in the project root directory
2. Double-click the `start_celery.bat` file in the project root directory

## Configuration

The automatic service management can be configured in `settings.py`:

```python
# Auto-start Redis and Celery when needed
DATA_MINER_AUTOSTART_SERVICES = True
```

Set this to `False` if you want to disable automatic service management.

## Troubleshooting

If you encounter issues with the automatic service management:

1. Check the application logs for error messages
2. Ensure Redis is properly installed in your user profile directory
3. Make sure the `psutil` package is installed (`pip install psutil`)
4. Try starting the services manually to check for any errors

## Requirements

- Python 3.6+
- Redis for Windows (installed in your user profile)
- Celery 5.x
- psutil package (`pip install psutil`)

## Verifying the Setup

1. Start the Django development server:
   ```
   python manage.py runserver
   ```

2. Navigate to http://127.0.0.1:8000/data_miner/ in your browser
3. Enter a keyword and select "phone" or "email" as the data type
4. Click "Get" to start a data mining task
5. You should see the task start processing without any connection errors

## Advanced Configuration

The Redis server is configured with default settings from `redis.windows.conf`. You can modify these settings if needed:

- Default port: 6379
- Default host: localhost
- No password authentication enabled

Both the Celery broker URL and result backend are configured in `matrix/settings.py`:

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
``` 