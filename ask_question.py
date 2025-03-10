"""
Script to run a single research query
"""
import requests
import time
import json
import os
import sys
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
        print("⏳ Waiting for results...")
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
                    print("✅ Research completed!")
                    return status_data
                elif status_data["status"] == "failed":
                    print(f"❌ Research task failed: {status_data.get('message', 'Unknown error')}")
                    return None
                else:
                    print(f"⏳ Status: {status_data['status']} (attempt {attempt+1}/{max_attempts})")
            except Exception as e:
                print(f"❌ Exception when checking status: {str(e)}")
        
        print("❌ Timed out waiting for results")
        return None
    except Exception as e:
        print(f"❌ Exception during research: {str(e)}")
        return None

def main():
    """Main function to run a research query"""
    print("🌐 OllamaSonar Research Test")
    print("---------------------------")
    
    # Check if API is running
    if not check_health():
        print("❌ API is not available. Please start the API server first.")
        print("   Run: python ollama_test_1.py --mode api")
        return
    
    # Create API key
    api_key = create_api_key()
    
    # Get query from command line or prompt
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter research query: ")
    
    if not query:
        print("❌ No query provided. Exiting.")
        return
    
    # Run research
    result = ask_question(query, api_key)
    
    if result:
        print("\n📊 Research Results:")
        print("-------------------")
        print(result.get("answer", "No answer found"))
        
        # Save result to file
        save_result(query, result)

if __name__ == "__main__":
    main() 