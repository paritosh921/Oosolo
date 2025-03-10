# Start all OllamaSonar services

# Create necessary directories
if (-not (Test-Path "database")) {
    New-Item -ItemType Directory -Path "database" | Out-Null
}
if (-not (Test-Path "database\task_results")) {
    New-Item -ItemType Directory -Path "database\task_results" | Out-Null
}
if (-not (Test-Path "database\task_errors")) {
    New-Item -ItemType Directory -Path "database\task_errors" | Out-Null
}

# Check if Ollama is running
$ollamaRunning = $false
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -ErrorAction SilentlyContinue
    $ollamaRunning = $true
    Write-Host "✅ Ollama is running"
    
    # Check if gemma2:2b model is available
    $gemmaAvailable = $false
    foreach ($model in $ollamaResponse) {
        if ($model.name -eq "gemma2:2b") {
            $gemmaAvailable = $true
            Write-Host "✅ gemma2:2b model is available"
            break
        }
    }
    
    if (-not $gemmaAvailable) {
        Write-Host "⚠️ gemma2:2b model is not available. Pulling it now..."
        Start-Process -FilePath "ollama" -ArgumentList "pull gemma2:2b" -NoNewWindow -Wait
    }
} catch {
    Write-Host "❌ Ollama is not running. Please start Ollama first."
    Write-Host "   Run: ollama serve"
    exit
}

# Start Redis
Write-Host "🔄 Starting Redis..."
python start_redis.py

# Start API server
Write-Host "🔄 Starting API server..."
Start-Process -FilePath "powershell" -ArgumentList "-Command python ollama_test_1.py --mode api" -NoNewWindow

# Start worker
Write-Host "🔄 Starting worker..."
Start-Process -FilePath "powershell" -ArgumentList "-Command python ollama_test_1.py --mode worker" -NoNewWindow

# Start multiple Celery workers for concurrent processing

# Start Redis server if not already running
Write-Host "Starting Redis server..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList "start_redis.py" -NoNewWindow

# Wait for Redis to start
Start-Sleep -Seconds 5

# Start FastAPI server
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "-m uvicorn sonar.api:app --host 0.0.0.0 --port 8000 --reload" -NoNewWindow

# Start multiple Celery workers
Write-Host "Starting Celery workers..." -ForegroundColor Yellow
Start-Process -FilePath "celery" -ArgumentList "-A sonar.tasks worker --loglevel=info --concurrency=4 -n worker1@%h" -NoNewWindow
Start-Process -FilePath "celery" -ArgumentList "-A sonar.tasks worker --loglevel=info --concurrency=4 -n worker2@%h" -NoNewWindow

Write-Host "✅ All services started!"
Write-Host "📝 You can now run: python test_research.py 'your research query'"
Write-Host "API is available at http://localhost:8000" -ForegroundColor Magenta
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Red

# Keep the script running
try {
    while ($true) {
        Start-Sleep -Seconds 10
    }
}
finally {
    # This block will execute when Ctrl+C is pressed
    Write-Host "Stopping services..." -ForegroundColor Red
    
    # Add commands to gracefully stop services
    # For example, you might want to send SIGTERM to the processes
}