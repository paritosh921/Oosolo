"""
Command-line interface for OllamaSonar.
"""

import time
import os
from datetime import datetime, timedelta
from .sonar import OllamaSonar

def save_interaction(query, answer, folder="database"):
    """Save the query and answer to a text file in the database folder"""
    # Create database folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}/query_{timestamp}.txt"
    
    # Write the query and answer to the file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"QUERY: {query}\n\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"ANSWER:\n{answer}\n")
    
    print(f"Interaction saved to {filename}")
    return filename

def format_time(seconds):
    """Format seconds into a readable time string"""
    return str(timedelta(seconds=int(seconds)))

def main():
    """Main CLI entry point"""
    sonar = OllamaSonar(model="gemma2:2b")
    
    # Create database folder
    database_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
    os.makedirs(database_folder, exist_ok=True)
    
    print("🌐 Ollama Sonar - Live Web Research Assistant")
    print("----------------------------------------")
    
    while True:
        query = input("\n🔍 Enter your research question (or 'exit' to quit): ")
        if query.lower() in ['exit', 'quit', 'q']:
            break
            
        start_time = time.time()
        
        # Display a timer while processing
        timer_thread = None
        timer_running = True
        
        def update_timer():
            elapsed = 0
            while timer_running:
                elapsed = time.time() - start_time
                print(f"\rTime elapsed: {format_time(elapsed)}", end="", flush=True)
                time.sleep(1)
        
        # We don't need to start a timer thread since tqdm will show progress
        
        answer = sonar.search_and_answer(query)
        timer_running = False
        elapsed_time = time.time() - start_time
        
        # Clear the timer line
        print("\r" + " " * 30 + "\r", end="")
        
        print("\n" + "="*80)
        print(answer)
        print("="*80)
        print(f"\n⏱️ Research completed in {elapsed_time:.2f} seconds ({format_time(elapsed_time)})")
        
        # Save the interaction to a file
        save_interaction(query, answer, database_folder)


if __name__ == "__main__":
    main()