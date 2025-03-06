"""
Helper script to start Redis server if it's not already running
"""
import subprocess
import os
import sys
import time
import socket

def is_redis_running():
    """Check if Redis is already running by attempting to connect to it"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(('localhost', 6379))
        s.close()
        return True
    except:
        return False

def start_redis():
    """Start Redis server"""
    print("🔄 Checking if Redis is running...")
    
    if is_redis_running():
        print("✅ Redis is already running!")
        return True
    
    print("🚀 Starting Redis server...")
    
    # Try different methods to start Redis
    methods = [
        # Method 1: Try using redis-server command directly
        ["redis-server"],
        
        # Method 2: Try common installation paths
        ["C:\\Program Files\\Redis\\redis-server.exe"],
        ["C:\\Redis\\redis-server.exe"],
        
        # Method 3: Try using Docker
        ["docker", "run", "--name", "redis", "-p", "6379:6379", "-d", "redis"]
    ]
    
    for method in methods:
        try:
            # Check if the file exists for file paths
            if len(method) == 1 and method[0].endswith('.exe') and not os.path.exists(method[0]):
                continue
                
            print(f"Trying to start Redis using: {' '.join(method)}")
            
            # For Docker, check if container already exists
            if "docker" in method:
                try:
                    subprocess.run(["docker", "start", "redis"], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  check=False)
                    print("Started existing Redis Docker container")
                except:
                    # If starting fails, try running a new container
                    subprocess.run(method, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  check=False)
            else:
                # For direct Redis server commands
                subprocess.Popen(method, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
            
            # Wait for Redis to start
            for _ in range(5):
                time.sleep(1)
                if is_redis_running():
                    print("✅ Redis server started successfully!")
                    return True
                    
        except Exception as e:
            print(f"Error starting Redis: {str(e)}")
    
    print("❌ Failed to start Redis server. Will use synchronous processing instead.")
    return False

if __name__ == "__main__":
    start_redis()