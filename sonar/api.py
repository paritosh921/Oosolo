"""
API module for OllamaSonar.
Provides RESTful endpoints for the web research assistant.
"""

import time
import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import tiktoken
import jwt
from .sonar import OllamaSonar
import asyncio
from .tasks import research_task
import redis

# Initialize the tokenizer for counting tokens
tokenizer = tiktoken.get_encoding("cl100k_base")  # Using OpenAI's tokenizer as a standard

# Create FastAPI app
app = FastAPI(
    title="OllamaSonar API",
    description="Live Web Research Assistant API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Secret (in production, store this securely)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

# API key storage (in production, use a database)
# Initialize with a default API key for testing
API_KEYS = {
    "sk-57c2154e-c950-4314-9536-27ad3e48b09b": {
        "name": "Default User",
        "email": "default@example.com",
        "plan": "basic",
        "api_key": "sk-57c2154e-c950-4314-9536-27ad3e48b09b",
        "user_id": "default-user",
        "created_at": datetime.now().isoformat()
    }
}

# Usage tracking
USAGE_TRACKING = {}

# Request models
class ResearchRequest(BaseModel):
    query: str = Field(..., description="The research question to answer")
    model: Optional[str] = Field("gemma2:2b", description="LLM model to use")
    num_sources: Optional[int] = Field(6, description="Number of sources to use")

class ApiKeyRequest(BaseModel):
    name: str = Field(..., description="Name for the API key")
    email: str = Field(..., description="Email associated with the API key")
    plan: str = Field("basic", description="Subscription plan (basic, pro, enterprise)")

class TokenResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float

# Helper functions
def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string"""
    return len(tokenizer.encode(text))

def calculate_cost(input_tokens: int, output_tokens: int = 0, plan: str = "basic") -> float:
    """Calculate cost based on tokens and plan"""
    # Example pricing (adjust as needed)
    rates = {
        "basic": {"input": 0.0001, "output": 0.0002},
        "pro": {"input": 0.00008, "output": 0.00016},
        "enterprise": {"input": 0.00006, "output": 0.00012}
    }
    
    plan_rates = rates.get(plan, rates["basic"])
    return (input_tokens * plan_rates["input"]) + (output_tokens * plan_rates["output"])

def update_user_usage(user_id, input_tokens, output_tokens, cost):
    """Update user usage statistics"""
    if user_id not in USAGE_TRACKING:
        USAGE_TRACKING[user_id] = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0,
            "history": []
        }
    
    USAGE_TRACKING[user_id]["total_requests"] += 1
    USAGE_TRACKING[user_id]["total_input_tokens"] += input_tokens
    USAGE_TRACKING[user_id]["total_output_tokens"] += output_tokens
    USAGE_TRACKING[user_id]["total_cost"] += cost
    
    # Add to history
    USAGE_TRACKING[user_id]["history"].append({
        "timestamp": datetime.now().isoformat(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost
    })

def get_api_key(api_key: str = Header(...)) -> Dict:
    """Validate API key and return user info"""
    # Debug output to help diagnose issues
    print(f"Received API key: {api_key}")
    print(f"Available keys: {list(API_KEYS.keys())}")
    
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return API_KEYS[api_key]

# Improved Redis availability check
def is_redis_available():
    """Check if Redis is available with better error handling"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except (redis.ConnectionError, NameError) as e:
        print(f"❌ Redis connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Redis error: {str(e)}")
        return False

# API endpoints
@app.post("/api/research", response_model=Dict[str, Any])
async def research(
    request: ResearchRequest, 
    background_tasks: BackgroundTasks,
    user: Dict = Depends(get_api_key)
):
    """Submit a research query to the task queue"""
    # Count input tokens
    input_tokens = count_tokens(request.query)
    
    # Generate a task ID
    task_id = str(uuid.uuid4())
    
    # Check if Redis is available
    redis_available = is_redis_available()
    
    if redis_available:
        try:
            # Submit task to Celery queue
            task = research_task.delay(
                request.query,
                request.model,
                request.num_sources
            )
            task_id = task.id
            print(f"✅ Task submitted to Celery with ID: {task_id}")
        except Exception as e:
            print(f"❌ Error submitting task to Celery: {str(e)}")
            print("⚠️ Falling back to synchronous processing")
            return await process_research_synchronously(request, task_id, user, input_tokens)
    else:
        # Redis is not available, process synchronously
        print("⚠️ Redis is not available. Processing research synchronously.")
        return await process_research_synchronously(request, task_id, user, input_tokens)
    
    # Record the task in the database
    user_id = user.get("user_id", "anonymous")
    
    # Update user's usage statistics
    update_user_usage(user_id, input_tokens, 0, 0.0)
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Research query submitted successfully"
    }

async def process_research_synchronously(request, task_id, user, input_tokens):
    """Process research request synchronously when Redis/Celery is unavailable"""
    print(f"🔍 Processing research query synchronously: {request.query}")
    
    # Initialize OllamaSonar
    sonar = OllamaSonar(model=request.model)
    
    # Perform research
    result = sonar.search_and_answer(request.query, num_sources=request.num_sources)
    
    # Save result to a file for backup
    result_file = f"database/task_results/{task_id}.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'query': request.query,
            'result': result,
            'task_id': task_id
        }, f, ensure_ascii=False, indent=2)
    
    # Count output tokens
    output_tokens = count_tokens(result)
    total_tokens = input_tokens + output_tokens
    
    # Calculate cost with proper parameters
    cost = calculate_cost(input_tokens, output_tokens, user.get("plan", "basic"))
    
    # Update user's usage statistics
    user_id = user.get("user_id", "anonymous")
    update_user_usage(user_id, input_tokens, output_tokens, cost)
    
    print(f"✅ Research completed synchronously. Result length: {len(result)} characters")
    
    return {
        "task_id": task_id,
        "status": "completed",
        "answer": result,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens
        },
        "cost": cost
    }

# Add more API endpoints below
@app.get("/api/task/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    user: Dict = Depends(get_api_key)
):
    """Get the status of a research task"""
    # Check if Redis is available
    redis_available = is_redis_available()
    
    if redis_available:
        try:
            # Get task status from Celery
            task = research_task.AsyncResult(task_id)
            
            if task.state == 'PENDING':
                return {
                    "task_id": task_id,
                    "status": "processing",
                    "message": "Task is still processing"
                }
            elif task.state == 'SUCCESS':
                result = task.result
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "answer": result,
                    # We don't have token counts here, would need to store them
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "message": f"Task failed with state: {task.state}"
                }
        except Exception as e:
            print(f"Error getting task status: {str(e)}")
    
    # If Redis is not available or there was an error, try to get result from file
    result_file = f"database/task_results/{task_id}.json"
    if os.path.exists(result_file):
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "answer": data.get('result', 'No result found'),
                    "source": "file"
                }
        except Exception as e:
            print(f"Error reading result file: {str(e)}")
    
    # If we can't find the task
    return {
        "task_id": task_id,
        "status": "not_found",
        "message": "Task not found"
    }
@app.post("/api/keys", response_model=Dict[str, Any])
async def create_api_key(
    request: ApiKeyRequest,
    admin_key: str = Header(None)
):
    """Create a new API key (admin only)"""
    # In a real application, you would validate the admin key
    if admin_key != os.getenv("ADMIN_KEY", "admin-secret-key"):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Generate a new API key
    api_key = f"sk-{uuid.uuid4()}"
    user_id = str(uuid.uuid4())
    
    # Store the API key
    API_KEYS[api_key] = {
        "name": request.name,
        "email": request.email,
        "plan": request.plan,
        "api_key": api_key,
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    
    # Debug output
    print(f"✅ Created new API key: {api_key}")
    print(f"✅ Available keys: {list(API_KEYS.keys())}")
    
    return {
        "api_key": api_key,
        "user_id": user_id,
        "name": request.name,
        "email": request.email,
        "plan": request.plan,
        "created_at": API_KEYS[api_key]["created_at"]
    }
@app.get("/api/usage", response_model=Dict[str, Any])
async def get_usage_stats(
    user: Dict = Depends(get_api_key)
):
    """Get usage statistics for the current user"""
    user_id = user.get("user_id", "anonymous")
    
    if user_id not in USAGE_TRACKING:
        return {
            "user_id": user_id,
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0,
            "history": []
        }
    
    return {
        "user_id": user_id,
        **USAGE_TRACKING[user_id]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "available" if is_redis_available() else "unavailable"
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat()
    }