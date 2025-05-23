"""
Direct service starter for data mining background tasks
This script provides a more direct and reliable way to start Redis and Celery services.
"""
import os
import sys
import subprocess
import time
import signal
import traceback
import logging
from pathlib import Path
import socket
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('direct_services')

class DirectServiceManager:
    """A simpler, more direct service manager for data mining tasks"""
    
    def __init__(self):
        # Get the project root directory
        self.project_dir = Path(__file__).resolve().parent.parent
        
        # Virtual environment path
        self.virtual_env = os.environ.get('VIRTUAL_ENV')
        if not self.virtual_env and os.path.exists(os.path.join(os.path.expanduser('~'), 'Envs', 'one')):
            # Guess a common virtualenv path if not set
            self.virtual_env = os.path.join(os.path.expanduser('~'), 'Envs', 'one')
            
        logger.info(f"Project directory: {self.project_dir}")
        logger.info(f"Virtual environment: {self.virtual_env}")
        
        # Redis paths
        self.redis_dir = os.path.join(os.path.expanduser('~'), 'Redis')
        self.redis_exe = os.path.join(self.redis_dir, 'redis-server.exe')
        self.redis_conf = os.path.join(self.redis_dir, 'redis.windows.conf')
        
        # Service processes
        self.redis_process = None
        self.celery_process = None
        
    def start_redis(self):
        """Start Redis server using direct command"""
        # Check if Redis is already running
        if self.is_redis_running():
            logger.info("Redis is already running, no need to start it")
            return True
            
        if not os.path.exists(self.redis_exe):
            logger.error(f"Redis executable not found at: {self.redis_exe}")
            # Try to find redis-server.exe in common locations
            common_redis_paths = [
                os.path.join(os.path.expanduser('~'), 'Redis', 'redis-server.exe'),
                r"C:\Program Files\Redis\redis-server.exe",
                r"C:\Redis\redis-server.exe",
            ]
            for path in common_redis_paths:
                if os.path.exists(path):
                    logger.info(f"Found Redis at alternative location: {path}")
                    self.redis_exe = path
                    self.redis_conf = os.path.join(os.path.dirname(path), 'redis.windows.conf')
                    break
            else:
                logger.error("Could not find Redis server executable in any common location")
                return False
            
        try:
            logger.info(f"Starting Redis with: {self.redis_exe} {self.redis_conf}")
            
            # Check if Redis configuration file exists
            if not os.path.exists(self.redis_conf):
                logger.warning(f"Redis configuration file not found: {self.redis_conf}")
                # Start Redis without config file as fallback
                self.redis_process = subprocess.Popen(
                    [self.redis_exe],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Start with config file
                self.redis_process = subprocess.Popen(
                    [self.redis_exe, self.redis_conf],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            # Wait for Redis to start (with multiple retries)
            max_retries = 5
            for retry in range(max_retries):
                time.sleep(1)  # Give Redis time to start
                if self.redis_process.poll() is not None:
                    # Process exited immediately
                    stderr = self.redis_process.stderr.read().decode('utf-8', errors='ignore')
                    stdout = self.redis_process.stdout.read().decode('utf-8', errors='ignore')
                    logger.error(f"Redis exited with code {self.redis_process.returncode} on attempt {retry+1}")
                    logger.error(f"Redis stderr: {stderr}")
                    logger.error(f"Redis stdout: {stdout}")
                    
                    if retry < max_retries - 1:
                        logger.info(f"Retrying Redis startup ({retry+2}/{max_retries})")
                        # Try to start Redis again with different arguments
                        if retry == 1:
                            # Try without config file on second attempt
                            self.redis_process = subprocess.Popen(
                                [self.redis_exe],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                        else:
                            # Standard retry
                            self.redis_process = subprocess.Popen(
                                [self.redis_exe, self.redis_conf],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                    else:
                        return False
                else:
                    # Process still running, check if port is actually open
                    if self.is_redis_running():
                        logger.info(f"Redis started successfully on attempt {retry+1}")
                        return True
            
            # After all retries, check one last time
            if self.is_redis_running():
                logger.info("Redis is running after all startup attempts")
                return True
                
            logger.error("Redis process is still running but port is not responding")
            return False
                
        except Exception as e:
            logger.error(f"Error starting Redis: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def start_celery(self):
        """Start Celery worker using batch file approach"""
        # This function is currently disabled
        logger.info("Celery startup has been disabled")
        return True
        
        """
        # Check if Celery is already running
        if self.is_celery_running():
            logger.info("Celery is already running, no need to start it")
            return True
            
        try:
            # Create a temporary batch file to ensure proper environment activation
            batch_file = os.path.join(self.project_dir, "start_celery_temp.bat")
            
            with open(batch_file, 'w') as f:
                f.write('@echo off\n')
                
                if self.virtual_env:
                    # Include virtualenv activation
                    activate_script = os.path.join(self.virtual_env, 'Scripts', 'activate.bat')
                    f.write(f'call "{activate_script}"\n')
                
                # Change to project directory
                f.write(f'cd /d "{self.project_dir}"\n')
                
                # Make sure Redis is available before starting Celery
                f.write('echo Checking Redis connection...\n')
                f.write('ping -n 1 localhost > NUL\n')  # Short delay
                
                # Set environment variables to help with connection retry
                f.write('set CELERY_BROKER_CONNECTION_RETRY=true\n')
                f.write('set CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=true\n')
                f.write('set CELERY_BROKER_CONNECTION_MAX_RETRIES=10\n')
                
                # Start Celery worker with retry options
                f.write('echo Starting Celery worker...\n')
                f.write('celery -A onematrix worker -l info -Q data_mining --without-heartbeat --without-gossip --without-mingle\n')
            
            logger.info(f"Starting Celery using batch file: {batch_file}")
            
            # Start the process
            self.celery_process = subprocess.Popen(
                [batch_file],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait for Celery to start with multiple retries
            logger.info("Waiting for Celery worker to start...")
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(2)  # Give more time between checks
                if self.celery_process.poll() is not None:
                    logger.error(f"Celery exited immediately with code {self.celery_process.returncode}")
                    # Try to restart if it fails on first attempts
                    if attempt < 3:  # Only retry first 3 times
                        logger.info(f"Retrying Celery startup (attempt {attempt+2})")
                        self.celery_process = subprocess.Popen(
                            [batch_file],
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        return False
                else:
                    # Process is still running, check if Celery is actually working
                    if self.is_celery_running():
                        logger.info(f"Celery worker started successfully after {attempt+1} attempts")
                        return True
                
                logger.info(f"Celery not detected as running yet, attempt {attempt+1}/{max_attempts}")
            
            # If we reach here, Celery didn't start properly despite process running
            if self.celery_process and self.celery_process.poll() is None:
                logger.warning("Celery process is running but not properly detected")
                # Force another check with a longer delay
                time.sleep(5)
                if self.is_celery_running():
                    logger.info("Celery detected as running after extended wait")
                    return True
                else:
                    logger.error("Celery process is running but service not detected as available")
                    return False
            else:
                logger.error("Failed to start Celery worker after multiple attempts")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Celery: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        """
            
    def start_all(self):
        """Start both Redis and Celery"""
        redis_result = self.start_redis()
        # Celery is disabled
        celery_result = True
        
        return redis_result and celery_result
        
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
            
    def is_redis_running(self):
        """Check if Redis is running based on port availability"""
        return self.is_port_in_use(6379)
        
    def is_celery_running(self):
        """Check if Celery is running based on process list"""
        # Celery is disabled, always report as running
        return True
        
        """
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'celery.exe' or proc.info['name'] == 'celery':
                    cmdline = proc.info.get('cmdline', [])
                    if 'onematrix' in cmdline and 'worker' in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
        """

# Create an instance for direct use
service_starter = DirectServiceManager()

# Function to call from Django views
def ensure_services():
    """Ensure all services are running"""
    manager = service_starter
    
    # Check if services are already running
    redis_running = manager.is_redis_running()
    # Celery is disabled
    celery_running = True
    
    logger.info(f"Current service status - Redis: {redis_running}, Celery: {celery_running}")
    
    # If both are running, we're good
    if redis_running and celery_running:
        logger.info("All services are already running")
        return True
        
    # Start any service that's not running
    result = True
    
    if not redis_running:
        redis_result = manager.start_redis()
        logger.info(f"Redis start result: {redis_result}")
        result = result and redis_result
    
    """    
    if not celery_running:
        celery_result = manager.start_celery()
        logger.info(f"Celery start result: {celery_result}")
        result = result and celery_result
    """    
    return result
    
if __name__ == "__main__":
    # This allows the script to be run directly for testing
    service_starter.start_all()
    
    # Keep script running to maintain processes
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping services...")
        # Clean up
        if service_starter.redis_process:
            service_starter.redis_process.terminate()
        if service_starter.celery_process:
            service_starter.celery_process.terminate() 