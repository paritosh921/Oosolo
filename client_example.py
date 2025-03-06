"""
Example client for OllamaSonar API.
Demonstrates how to use the API for web research.
"""

import requests
import json
import time

# API configuration
API_URL = "http://127.0.0.1:8000"
API_KEY = "your-api-key-here"  # Replace with your actual API key

def get_api_key():
    """Create a new API key"""
    response = requests.post(
        f"{API_URL}/api/keys",
        json={
            "name": "Example Client",
            "email": "client@example.com",
            "plan": "basic"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Created API key: {data['api_key']}")
        return data["api_key"]
    else:
        print(f"Error creating API key: {response.text}")
        return None

def research_query_async(query, api_key):
    """Send a research query to the API asynchronously"""
    headers = {"api-key": api_key}
    
    # Submit the request
    response = requests.post(
        f"{API_URL}/api/research",
        headers=headers,
        json={
            "query": query,
            "model": "gemma2:2b",
            "num_sources": 6
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        task_id = result["task_id"]
        
        print(f"Request submitted. Task ID: {task_id}")
        print("Checking status...")
        
        # Poll for results
        while True:
            status_response = requests.get(
                f"{API_URL}/api/research/{task_id}",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data["status"] == "completed":
                    return status_data
                elif status_data["status"] == "failed":
                    print(f"Error: {status_data['message']}")
                    return None
                else:
                    print(f"Status: {status_data['status']} - {status_data.get('message', 'Processing...')}")
                    time.sleep(5)  # Wait 5 seconds before checking again
            else:
                print(f"Error checking status: {status_response.text}")
                return None
    else:
        print(f"Error: {response.text}")
        return None
def get_usage(api_key):
    """Get usage statistics"""
    headers = {"api-key": api_key}
    
    response = requests.get(
        f"{API_URL}/api/usage",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Main function to demonstrate API usage"""
    # Get or create API key
    api_key = get_api_key()
    if not api_key:
        return
    
    # Example research query
    query = "What are the latest developments in India??"
    print(f"\n🔍 Researching: {query}")
    
    # Send query to API - use the async version
    start_time = time.time()
    result = research_query_async(query, api_key)  # Changed from research_query to research_query_async
    elapsed_time = time.time() - start_time
    
    if result:
        print("\n" + "=" * 80)
        print(result["answer"])
        print("=" * 80)
        
        # Display token usage
        tokens = result["tokens"]
        print(f"\n📊 Token Usage:")
        print(f"  Input tokens: {tokens['input']}")
        print(f"  Output tokens: {tokens['output']}")
        print(f"  Total tokens: {tokens['total']}")
        print(f"  Cost: ${tokens['cost']:.6f}")
        print(f"  Time: {elapsed_time:.2f} seconds")
        
        # Get overall usage
        print("\n📈 Overall Usage:")
        usage = get_usage(api_key)
        if usage:
            print(f"  Total requests: {usage['total_requests']}")
            print(f"  Total input tokens: {usage['total_input_tokens']}")
            print(f"  Total output tokens: {usage['total_output_tokens']}")
            print(f"  Total cost: ${usage['total_cost']:.6f}")

if __name__ == "__main__":
    main()