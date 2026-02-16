# =============================================================================
# Gunicorn Configuration for Photo Background Check
# Production-ready settings
# =============================================================================

import multiprocessing
import os

# Server socket
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(os.environ.get('GUNICORN_THREADS', 4))
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

# Use /dev/shm for worker heartbeat (faster than disk)
worker_tmp_dir = '/dev/shm'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = '-'
accesslog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Process naming
proc_name = 'photo_background_check'

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass

def worker_exit(server, worker):
    """Called in the worker process's context when it exits."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    pass

def pre_exec(server):
    """Called just before a new master process is forked."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    pass
