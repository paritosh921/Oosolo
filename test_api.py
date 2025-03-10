"""
Simple script to test if the API is working correctly
"""
import requests
import time
import json

# API configuration
API_URL = "http://127.0.0.1:8000"
DEFAULT_API_KEY = "sk-57c2154e-c950-4314-9536-27ad3e48b09b"  # Default key from api.py

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

def test_research_endpoint():
    """Test the research endpoint"""
    print("Testing research endpoint...")
    
    try:
        # Submit research request
        response = requests.post(
            f"{API_URL}/api/research",
            headers={"api-key": DEFAULT_API_KEY},
            json={
                "query": "What is a simple test query?",
                "model": "gemma2:2b",
                "num_sources": 2  # Use fewer sources for a quicker test
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Research request failed: {response.text}")
            return False
        
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ Research task submitted with ID: {task_id}")
        
        # Poll for results (just a few times for testing)
        print("⏳ Checking if task was accepted...")
        max_attempts = 3
        for attempt in range(max_attempts):
            time.sleep(1)  # Wait 1 second between polls
            
            try:
                status_response = requests.get(
                    f"{API_URL}/api/task/{task_id}",
                    headers={"api-key": DEFAULT_API_KEY}
                )
                
                if status_response.status_code != 200:
                    print(f"❌ Error checking task status: {status_response.text}")
                    continue
                
                status_data = status_response.json()
                print(f"✅ Task status: {status_data['status']}")
                
                # We don't need to wait for completion for this test
                return True
            except Exception as e:
                print(f"❌ Exception when checking status: {str(e)}")
        
        return False
    except Exception as e:
        print(f"❌ Exception during test: {str(e)}")
        return False

def main():
    """Main function to test the API"""
    print("🧪 OllamaSonar API Test")
    print("----------------------")
    
    # Check if API is running
    if not check_health():
        print("❌ API is not available. Please start the API server first.")
        print("   Run: python ollama_test_1.py --mode api")
        return
    
    # Test research endpoint
    if test_research_endpoint():
        print("✅ API test successful!")
    else:
        print("❌ API test failed.")

if __name__ == "__main__":
    main() 