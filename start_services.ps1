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

Write-Host "✅ All services started!"
Write-Host "📝 You can now run: python test_research.py 'your research query'"