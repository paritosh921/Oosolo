"""
Task queue for OllamaSonar.
Handles asynchronous processing of research requests.
"""

from celery import Celery
import os
import json
from .sonar import OllamaSonar
import time
from celery.signals import worker_ready
import redis
import tiktoken

# Initialize the tokenizer for counting tokens
tokenizer = tiktoken.get_encoding("cl100k_base")

# Configure Redis connection with retry logic
def get_redis_connection(max_retries=3, retry_delay=2):
    """Attempt to connect to Redis with retries"""
    for attempt in range(max_retries):
        try:
            # Test the connection
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            print(f"✅ Successfully connected to Redis on localhost:6379")
            return True
        except redis.ConnectionError as e:
            print(f"⚠️ Redis connection attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    return False

# Configure Celery with connection retry
redis_connected = get_redis_connection()
if not redis_connected:
    print("⚠️ Warning: Could not connect to Redis. Tasks will be executed synchronously.")

# Create Celery app
celery_app = Celery('sonar_tasks',
                   broker='redis://localhost:6379/0',
                   backend='redis://localhost:6379/0')

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    worker_concurrency=4,  # Process 4 tasks concurrently per worker
    worker_prefetch_multiplier=1  # Don't prefetch more tasks than can be processed
)

@celery_app.task(bind=True, name='sonar.tasks.research_task', rate_limit='10/m')
def research_task(self, query, model="gemma2:2b", num_sources=6, priority=5):
    """Process a research query asynchronously with priority"""
    try:
        # Set task priority based on user plan (if supported by broker)
        self.request.delivery_info['priority'] = priority
        
        print(f"🔍 Starting research task for query: {query}")
        
        # Initialize OllamaSonar
        sonar = OllamaSonar(model=model)
        
        # Perform research
        result = sonar.search_and_answer(query, num_sources=num_sources)
        
        # Save result to a file for backup
        task_id = self.request.id
        result_file = f"database/task_results/{task_id}.json"
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'query': query,
                'result': result,
                'task_id': task_id
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Research task completed. Result length: {len(result)} characters")
        
        return result
    except Exception as e:
        print(f"❌ Error in research task: {str(e)}")
        # Save error to file
        try:
            task_id = self.request.id
            error_file = f"database/task_errors/{task_id}.json"
            os.makedirs(os.path.dirname(error_file), exist_ok=True)
            
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'query': query,
                    'error': str(e),
                    'task_id': task_id
                }, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        # Re-raise the exception to mark the task as failed
        raise

@worker_ready.connect
def at_start(sender, **k):
    """Log when worker is ready"""
    print("🚀 Celery worker is ready to process tasks")