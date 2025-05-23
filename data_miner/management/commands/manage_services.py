from django.core.management.base import BaseCommand
from data_miner.services import service_manager

class Command(BaseCommand):
    help = 'Manages Redis services for the data mining application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'status'],
            help='Action to perform on services (start, stop, status)'
        )
        
        parser.add_argument(
            '--service',
            type=str,
            choices=['redis', 'all'],
            default='all',
            help='Which service to manage (redis or all)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        service = options['service']
        
        if action == 'start':
            self._start_services(service)
        elif action == 'stop':
            self._stop_services(service)
        elif action == 'status':
            self._check_status(service)
    
    def _start_services(self, service):
        """Start the specified service(s)"""
        if service in ('redis', 'all'):
            if service_manager.start_redis():
                self.stdout.write(self.style.SUCCESS('Redis server started successfully'))
            else:
                self.stdout.write(self.style.ERROR('Failed to start Redis server'))
        
        # Celery functionality disabled
        """
        if service in ('celery', 'all'):
            if service_manager.start_celery():
                self.stdout.write(self.style.SUCCESS('Celery worker started successfully'))
            else:
                self.stdout.write(self.style.ERROR('Failed to start Celery worker'))
        """
    
    def _stop_services(self, service):
        """Stop the specified service(s)"""
        if service in ('redis', 'all'):
            if service_manager.stop_redis():
                self.stdout.write(self.style.SUCCESS('Redis server stopped successfully'))
            else:
                self.stdout.write(self.style.ERROR('Failed to stop Redis server'))
        
        # Celery functionality disabled
        """
        if service in ('celery', 'all'):
            if service_manager.stop_celery():
                self.stdout.write(self.style.SUCCESS('Celery worker stopped successfully'))
            else:
                self.stdout.write(self.style.ERROR('Failed to stop Celery worker'))
        """
    
    def _check_status(self, service):
        """Check the status of the specified service(s)"""
        if service in ('redis', 'all'):
            is_running = service_manager.is_redis_running()
            message = 'Redis server is running' if is_running else 'Redis server is not running'
            self.stdout.write(self.style.SUCCESS(message) if is_running else self.style.WARNING(message))
        
        # Celery functionality disabled
        """
        if service in ('celery', 'all'):
            is_running = service_manager.is_celery_running()
            message = 'Celery worker is running' if is_running else 'Celery worker is not running'
            self.stdout.write(self.style.SUCCESS(message) if is_running else self.style.WARNING(message))
        """ 