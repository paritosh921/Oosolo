"""
Script to run multiple research queries concurrently
"""
import requests
import threading
import time
import json
import os
from datetime import datetime

# API configuration
API_URL = "http://127.0.0.1:8000"
DEFAULT_API_KEY = "sk-57c2154e-c950-4314-9536-27ad3e48b09b"  # Default key from api.py

def create_api_key():
    """Create a new API key using admin access"""
    admin_key = "admin-secret-key"  # Default admin key
    
    try:
        response = requests.post(
            f"{API_URL}/api/keys",
            headers={"admin-key": admin_key},
            json={
                "name": "Test User",
                "email": "test@example.com",
                "plan": "basic"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Created API key: {data['api_key']}")
            return data["api_key"]
        else:
            print(f"❌ Error creating API key: {response.text}")
            print("Using default API key instead.")
            return DEFAULT_API_KEY
    except Exception as e:
        print(f"❌ Exception when creating API key: {str(e)}")
        print("Using default API key instead.")
        return DEFAULT_API_KEY

def check_health():
    """Check API health status"""
    try:
        response = requests.get(f"{API_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Status: {data['status']}")
            print(f"✅ Redis Status: {data['redis']}")
            return True
        else:
            print(f"❌ API health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception during health check: {str(e)}")
        return False

def save_result(query, result):
    """Save result to a file"""
    # Create database folder if it doesn't exist
    os.makedirs("database/results", exist_ok=True)
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"database/results/query_{timestamp}.json"
    
    # Write the result to the file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "query": query,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Result saved to {filename}")
    return filename

def ask_question(query, api_key):
    """Send a research query and wait for results"""
    print(f"🔍 Researching: {query}")
    
    try:
        # Submit research request
        response = requests.post(
            f"{API_URL}/api/research",
            headers={"api-key": api_key},
            json={
                "query": query,
                "model": "gemma2:2b",
                "num_sources": 6
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Research request failed: {response.text}")
            return None
        
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ Research task submitted with ID: {task_id}")
        
        # Poll for results
        print(f"⏳ Waiting for results for: {query}")
        max_attempts = 60  # Increased from 30 to 60
        for attempt in range(max_attempts):
            time.sleep(2)  # Wait 2 seconds between polls
            
            try:
                status_response = requests.get(
                    f"{API_URL}/api/task/{task_id}",
                    headers={"api-key": api_key}
                )
                
                if status_response.status_code != 200:
                    print(f"❌ Error checking task status: {status_response.text}")
                    continue
                
                status_data = status_response.json()
                
                if status_data["status"] == "completed":
                    print(f"✅ Research completed for: {query}")
                    print(f"Answer: {status_data.get('answer', 'No answer found')[:200]}...")
                    
                    # Save result to file
                    save_result(query, status_data)
                    
                    return status_data
                elif status_data["status"] == "failed":
                    print(f"❌ Research task failed: {status_data.get('message', 'Unknown error')}")
                    return None
                else:
                    print(f"⏳ Status for '{query}': {status_data['status']} (attempt {attempt+1}/{max_attempts})")
            except Exception as e:
                print(f"❌ Exception when checking status: {str(e)}")
        
        print(f"❌ Timed out waiting for results for: {query}")
        return None
    except Exception as e:
        print(f"❌ Exception during research: {str(e)}")
        return None

def main():
    """Main function to run multiple research queries concurrently"""
    print("🌐 OllamaSonar Multi-Query Test")
    print("------------------------------")
    
    # Check if API is running
    if not check_health():
        print("❌ API is not available. Please start the API server first.")
        print("   Run: python ollama_test_1.py --mode api")
        return
    
    # Create API key
    api_key = create_api_key()
    
    # List of questions to ask
    questions = [
        "What are the latest developments in quantum computing?",
        "How does climate change affect marine ecosystems?",
        "What are the benefits of intermittent fasting?",
        "How is AI being used in healthcare?"
    ]
    
    # Ask for custom questions
    custom_question = input("Enter a custom question (or press Enter to use default questions): ")
    if custom_question:
        questions = [custom_question]
        
        # Ask for more questions
        while True:
            another = input("Add another question? (y/n): ")
            if another.lower() != 'y':
                break
            question = input("Enter question: ")
            if question:
                questions.append(question)
    
    print(f"\n🔍 Running {len(questions)} research queries concurrently...")
    
    # Create threads for each question
    threads = []
    for question in questions:
        thread = threading.Thread(target=ask_question, args=(question, api_key))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("\n✅ All research tasks completed!")

if __name__ == "__main__":
    main() 