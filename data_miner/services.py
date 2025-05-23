import os
import subprocess
import signal
import psutil
import logging
import time
import traceback
from django.conf import settings
import socket

logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Manages Redis and Celery services for the data mining application.
    Ensures services are running when needed and can be started/stopped programmatically.
    """
    
    _instance = None
    _redis_process = None
    _celery_process = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._redis_path = os.path.expanduser("~/Redis/redis-server.exe")
            self._redis_conf = os.path.expanduser("~/Redis/redis.windows.conf")
            
            # Get virtual environment path
            virtual_env = os.environ.get('VIRTUAL_ENV')
            
            if virtual_env:
                # If running in a virtual environment, use the Python executable from that environment
                python_path = os.path.join(virtual_env, 'Scripts', 'python.exe')
                celery_path = os.path.join(virtual_env, 'Scripts', 'celery.exe')
                self._celery_cmd = ["celery", "-A", "matrix", "worker", "--loglevel", "info"]
            else:
                # Fallback to using the system PATH
                self._celery_cmd = ["celery", "-A", "matrix", "worker", "--loglevel", "info"]

                
            self._project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._initialized = True
    
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def is_redis_running(self):
        """Check if Redis server is running"""
        return self.is_port_in_use(6379)
    
    def is_celery_running(self):
        """Check if Celery workers are running for the project"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'celery.exe' or proc.info['name'] == 'celery':
                    cmdline = proc.info.get('cmdline', [])
                    if 'onematrix' in cmdline and 'worker' in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    
    def start_redis(self):
        """Start Redis server if not already running"""
        if self.is_redis_running():
            logger.info("Redis is already running")
            return True
        
        try:
            # Start Redis as a detached process
            if os.name == 'nt':  # Windows
                self._redis_process = subprocess.Popen(
                    [self._redis_path, self._redis_conf],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:  # Unix/Linux
                self._redis_process = subprocess.Popen(
                    [self._redis_path, self._redis_conf],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait for Redis to start
            max_attempts = 5
            for attempt in range(max_attempts):
                if self.is_redis_running():
                    logger.info("Redis server started successfully")
                    return True
                time.sleep(1)
            
            logger.error("Failed to start Redis server after multiple attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error starting Redis: {str(e)}")
            return False
    
    def start_celery(self):
        """Start Celery worker if not already running"""
        if self.is_celery_running():
            logger.info("Celery worker is already running")
            return True
        
        try:
            # Activate the virtual environment in the subprocess
            env = os.environ.copy()
            virtual_env = os.environ.get('VIRTUAL_ENV')
            logger.info(f"Current virtual environment: {virtual_env}")
            
            # Get current Python executable - assuming we're in the right virtualenv
            python_executable = os.sys.executable
            logger.info(f"Using Python executable: {python_executable}")
            
            # Log the Celery command for debugging
            cmd_str = " ".join(self._celery_cmd)
            logger.info(f"Attempting to start Celery with command: {cmd_str}")
            logger.info(f"Working directory: {self._project_path}")
            
            # Start Celery as a detached process
            if os.name == 'nt':  # Windows
                try:
                    self._celery_process = subprocess.Popen(
                        self._celery_cmd,
                        cwd=self._project_path,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # Check if process immediately failed
                    time.sleep(1)
                    if self._celery_process.poll() is not None:
                        stderr = self._celery_process.stderr.read().decode('utf-8', errors='ignore')
                        stdout = self._celery_process.stdout.read().decode('utf-8', errors='ignore')
                        logger.error(f"Celery process exited immediately with code {self._celery_process.returncode}")
                        logger.error(f"STDERR: {stderr}")
                        logger.error(f"STDOUT: {stdout}")
                except Exception as e:
                    logger.error(f"Exception during Celery startup: {str(e)}")
                    logger.error(traceback.format_exc())
            else:  # Unix/Linux
                self._celery_process = subprocess.Popen(
                    self._celery_cmd,
                    cwd=self._project_path,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait for Celery to start (this is approximate)
            logger.info("Waiting for Celery worker to start...")
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(1)
                if self.is_celery_running():
                    logger.info(f"Celery worker started successfully after {attempt+1} attempts")
                    return True
                logger.info(f"Celery not running yet, attempt {attempt+1}/{max_attempts}")
            
            # If we get here, Celery didn't start properly
            logger.error("Failed to start Celery worker after multiple attempts")
            
            # Check if the process is still running but not detected
            if self._celery_process and self._celery_process.poll() is None:
                logger.info("Celery process is still running but not detected by is_celery_running()")
                return True
            else:
                # Try to capture any error output
                if self._celery_process:
                    stderr = self._celery_process.stderr.read().decode('utf-8', errors='ignore')
                    stdout = self._celery_process.stdout.read().decode('utf-8', errors='ignore')
                    logger.error(f"Celery process stderr: {stderr}")
                    logger.error(f"Celery process stdout: {stdout}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Celery: {str(e)}")
            return False
    
    def ensure_services_running(self):
        """Ensure both Redis and Celery are running"""
        redis_status = self.is_redis_running() or self.start_redis()
        celery_status = self.is_celery_running() or self.start_celery()
        
        return redis_status and celery_status
    
    def stop_services(self):
        """Stop both Redis and Celery services"""
        stopped_redis = self.stop_redis()
        stopped_celery = self.stop_celery()
        
        return stopped_redis and stopped_celery
    
    def stop_redis(self):
        """Stop the Redis server"""
        try:
            if self._redis_process and self._redis_process.poll() is None:
                if os.name == 'nt':  # Windows
                    self._redis_process.terminate()
                else:  # Unix/Linux
                    self._redis_process.send_signal(signal.SIGTERM)
                self._redis_process.wait(timeout=5)
            
            # Also try to find and kill any other Redis processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'redis-server.exe' or proc.info['name'] == 'redis-server':
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Error stopping Redis: {str(e)}")
            return False
    
    def stop_celery(self):
        """Stop the Celery worker"""
        try:
            if self._celery_process and self._celery_process.poll() is None:
                if os.name == 'nt':  # Windows
                    self._celery_process.terminate()
                else:  # Unix/Linux
                    self._celery_process.send_signal(signal.SIGTERM)
                self._celery_process.wait(timeout=5)
            
            # Also try to find and kill any other Celery processes for this project
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'celery.exe' or proc.info['name'] == 'celery':
                        cmdline = proc.info.get('cmdline', [])
                        if 'onematrix' in cmdline and 'worker' in cmdline:
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Error stopping Celery: {str(e)}")
            return False

# Create a singleton instance
service_manager = ServiceManager() 