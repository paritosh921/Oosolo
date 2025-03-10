# OllamaSonar - Running Guide

This guide provides detailed instructions on how to run the OllamaSonar project and ask queries.

## Prerequisites

- Python 3.8 or higher
- Redis (will be automatically started by the scripts)
- Required Python packages (install using `pip install -r requirements.txt`)

## Installation

1. Clone the repository (if you haven't already)
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Project

There are several ways to run the project, depending on your needs:

### Option 1: Using the All-in-One Script

The simplest way to run the project is using the `ollama_test_1.py` script:

```bash
# Start the API server
python ollama_test_1.py --mode api

# In a separate terminal, start the worker(s)
python ollama_test_1.py --mode worker --workers 4

# In a separate terminal, run in CLI mode
python ollama_test_1.py --mode cli
```

### Option 2: Using the PowerShell Script (Windows)

If you're on Windows, you can use the PowerShell script to start all services:

```bash
.\start_services.ps1
```

This script will:
- Start the Redis server
- Launch the API server
- Start multiple Celery workers for concurrent processing

## Testing the API

Before asking queries, you can test if the API is working correctly:

```bash
python test_api.py
```

This script will:
1. Check if the API is running
2. Test the research endpoint
3. Verify that tasks are being accepted

## Asking Queries

### Method 1: Using the CLI Mode

The simplest way to ask a query is using the CLI mode:

```bash
python ollama_test_1.py --mode cli
```

This will start an interactive CLI where you can enter your research queries.

### Method 2: Using the ask_question.py Script

You can use the `ask_question.py` script to ask a single query:

```bash
# Provide the query as a command-line argument
python ask_question.py "What is quantum computing?"

# Or run without arguments to be prompted for a query
python ask_question.py
```

### Method 3: Running Multiple Queries Concurrently

To run multiple queries concurrently, use the `multi_questions.py` script:

```bash
python multi_questions.py
```

This script will:
1. Check if the API is running
2. Create an API key if needed
3. Allow you to enter custom questions or use default ones
4. Run all queries concurrently using threads
5. Save the results to files

### Method 4: Using Direct API Calls

You can also make direct API calls using tools like curl, Postman, or any HTTP client:

```bash
# Submit a research query
curl -X POST "http://localhost:8000/api/research" \
  -H "api-key: sk-57c2154e-c950-4314-9536-27ad3e48b09b" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?", "model": "gemma2:2b", "num_sources": 6}'

# Check the task status
curl -X GET "http://localhost:8000/api/task/{task_id}" \
  -H "api-key: sk-57c2154e-c950-4314-9536-27ad3e48b09b"
```

## Troubleshooting

If you encounter issues:

1. **Redis Connection Error**:
   - Make sure Redis is running: `python start_redis.py`
   - Check if Redis is accessible: `redis-cli ping` (should return PONG)

2. **API Server Not Responding**:
   - Verify the API server is running: `curl http://localhost:8000/api/health`
   - Check the API server logs for errors

3. **Celery Workers Not Processing Tasks**:
   - Ensure Celery workers are running and connected to Redis
   - Check Celery logs for errors

4. **Rate Limiting Issues**:
   - Rate limiting has been temporarily disabled to fix compatibility issues

5. **API Errors**:
   - If you see errors related to the API, check the error message in the terminal
   - Try running the `test_api.py` script to diagnose issues

## Advanced Configuration

### Adjusting Worker Concurrency

You can adjust the number of worker processes:

```bash
python ollama_test_1.py --mode worker --workers 8
```

### Running the API on a Different Host/Port

```bash
python ollama_test_1.py --mode api --host 0.0.0.0 --port 9000
```

### Skipping Redis Check

If you have Redis running separately:

```bash
python ollama_test_1.py --mode api --no-redis
```

## System Architecture

The system is designed to handle multiple concurrent requests efficiently:

1. **API Server**: Handles incoming requests and manages task queues
2. **Celery Workers**: Process research tasks asynchronously
3. **Redis**: Serves as a message broker and cache
4. **Web Scraper**: Scrapes multiple webpages concurrently
5. **LLM Processor**: Processes text using the specified LLM model

With the implemented concurrency features, the system can handle multiple users and queries simultaneously, distributing the workload across multiple workers and processes. 