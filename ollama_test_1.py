"""
OllamaSonar - Live Web Research Assistant
Main entry point for the application.
"""

import argparse
import uvicorn
from sonar.cli import main as cli_main
import os
import sys
import subprocess

def main():
    """Main entry point with CLI/API mode selection"""
    parser = argparse.ArgumentParser(description="OllamaSonar - Live Web Research Assistant")
    parser.add_argument("--mode", choices=["cli", "api", "worker"], default="cli", 
                        help="Run in CLI mode, API server mode, or as a Celery worker")
    parser.add_argument("--host", default="127.0.0.1", help="API server host (API mode only)")
    parser.add_argument("--port", type=int, default=8000, help="API server port (API mode only)")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker processes (worker mode only)")
    parser.add_argument("--no-redis", action="store_true", help="Skip Redis startup check")
    
    args = parser.parse_args()
    
    # Try to start Redis if needed (for API or worker mode)
    if args.mode in ["api", "worker"] and not args.no_redis:
        try:
            # Import and run the Redis starter
            from start_redis import start_redis
            redis_started = start_redis()
            if not redis_started and args.mode == "worker":
                print("⚠️ Warning: Redis is required for worker mode. Exiting.")
                return
        except ImportError:
            print("⚠️ Warning: Could not import start_redis module. Skipping Redis check.")
    
    if args.mode == "cli":
        # Run in CLI mode
        cli_main()
    elif args.mode == "worker":
        # Run as a Celery worker - Using a more direct approach
        import subprocess
        import sys
        import os
        
        print(f"🚀 Starting OllamaSonar worker with {args.workers} processes")
        
        # Get the Python executable path
        python_exe = sys.executable
        
        # Build the command to run celery directly as a subprocess
        cmd = [
            python_exe, "-m", "celery", 
            "-A", "sonar.tasks", 
            "worker",
            "--concurrency", str(args.workers),
            "--loglevel", "INFO",
            "--pool", "solo",  # Use solo pool to avoid multiprocessing issues
            "--without-heartbeat",  # Add this to prevent heartbeat issues
            "--without-mingle",     # Disable worker synchronization
            "--without-gossip"      # Disable gossip protocol
        ]
        
        # Run the celery worker as a subprocess
        try:
            # Set broker_connection_retry_on_startup to avoid deprecation warning
            os.environ["CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP"] = "true"
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\nCelery worker stopped")
    else:
        # Run in API server mode
        print(f"🚀 Starting OllamaSonar API server on {args.host}:{args.port}")
        print("💰 API is ready to accept requests and track token usage")
        uvicorn.run("sonar.api:app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()