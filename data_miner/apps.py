from django.apps import AppConfig


class DataMinerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_miner'
    
    def ready(self):
        """
        Called when the app is ready.
        Check if services should be started automatically.
        """
        import os
        # Don't run this when Django is doing migrations or collecting static files
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        # Import and check auto-start setting
        from django.conf import settings
        auto_start = getattr(settings, 'DATA_MINER_AUTOSTART_SERVICES', False)
        
        if auto_start:
            # Import in the ready method to avoid circular imports
            from .services import service_manager
            import threading
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info("Checking data miner services on startup...")
            
            # Start services in a background thread to avoid blocking app startup
            def start_services():
                try:
                    service_manager.ensure_services_running()
                    logger.info("Data mining services started successfully")
                except Exception as e:
                    logger.error(f"Error starting data mining services: {e}")
                    
            # Start the thread
            services_thread = threading.Thread(target=start_services)
            services_thread.daemon = True
            services_thread.start()
