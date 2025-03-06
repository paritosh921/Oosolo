"""
Main OllamaSonar module.
Integrates search, scraping, and LLM components.
"""

import time
import os
from datetime import datetime
from tqdm import tqdm
from .search import GoogleSearch, DuckDuckGoSearch
from .scraper import WebScraper
from .llm import LLMProcessor
import json  # Add this import
import asyncio  # Add async support
import functools
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading
import concurrent.futures  # Add this import
import concurrent.futures  # Add this import

# Global thread pool for reuse across requests
THREAD_POOL = ThreadPoolExecutor(max_workers=20)
# Global request limiter
MAX_CONCURRENT_REQUESTS = 50
request_semaphore = threading.Semaphore(MAX_CONCURRENT_REQUESTS)
# Simple in-memory cache
CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 3600  # Cache time-to-live in seconds

class OllamaSonar:
    """Main class that integrates all components for web research"""
    
    def __init__(self, model="gemma2:2b"):
        # Common headers for all HTTP requests
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        }
        
        # Initialize components
        self.google_search = GoogleSearch(self.headers)
        self.duckduckgo_search = DuckDuckGoSearch(self.headers)
        self.web_scraper = WebScraper(self.headers)
        self.llm_processor = LLMProcessor(model)
        
        # Create database folder
        self.database_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
        os.makedirs(self.database_folder, exist_ok=True)
        
    def _save_intermediate_data(self, query, data_type, content):
        """Save intermediate data to a file for debugging and analysis"""
        # Create database folder if it doesn't exist
        os.makedirs("database", exist_ok=True)
        
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database/{data_type}_{timestamp}.txt"
        
        # Write the data to the file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"QUERY: {query}\n")
            f.write(f"TYPE: {data_type}\n")
            f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            # Convert content to string if it's a dictionary
            if isinstance(content, dict):
                f.write(json.dumps(content, indent=2))
            else:
                f.write(content)
        
        return filename

    def _generate_cache_key(self, query, num_sources):
        """Generate a cache key for a query"""
        cache_key = f"{query}:{num_sources}:{time.strftime('%Y%m%d')}"
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    def _check_cache(self, query, num_sources):
        """Check if result exists in cache"""
        cache_key = self._generate_cache_key(query, num_sources)
        with CACHE_LOCK:
            if cache_key in CACHE:
                result, timestamp = CACHE[cache_key]
                if time.time() - timestamp < CACHE_TTL:
                    return result
                else:
                    # Remove expired cache entry
                    del CACHE[cache_key]
        return None
    
    def _update_cache(self, query, num_sources, result):
        """Update cache with new result"""
        cache_key = self._generate_cache_key(query, num_sources)
        with CACHE_LOCK:
            CACHE[cache_key] = (result, time.time())
    
    async def search_and_answer_async(self, query, num_sources=6):
        """Asynchronous version of search_and_answer"""
        # Check cache first
        cached_result = self._check_cache(query, num_sources)
        if cached_result:
            print("🔄 Returning cached result")
            return cached_result
            
        # Use semaphore to limit concurrent requests
        with request_semaphore:
            # Run the synchronous method in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                THREAD_POOL, 
                functools.partial(self.search_and_answer, query, num_sources)
            )
            
            # Cache the result
            self._update_cache(query, num_sources, result)
            return result
    
    def search_and_answer(self, query, num_sources=6):
        """Main function to search, scrape, summarize, and synthesize the answer"""
        print(f"🔍 Searching for information about: {query}")
        
        # Setup progress bar for overall process
        overall_steps = 4  # search, scrape, summarize, synthesize
        overall_progress = tqdm(total=overall_steps, desc="Overall Progress", position=0)
        
        # Enhance query with more specific parameters
        current_year = time.strftime("%Y")
        enhanced_query = f"{query} {current_year} research analysis latest information -pinterest -youtube"
        
        # Try Google search first with more results
        urls = self.google_search.search(enhanced_query, num_results=num_sources+5)  # Increased buffer
        
        # If Google search fails, try DuckDuckGo
        if not urls:
            print("Google search returned no results. Trying DuckDuckGo...")
            urls = self.duckduckgo_search.search(enhanced_query, num_results=num_sources+3)
            
        if not urls:
            overall_progress.close()
            return "Sorry, I couldn't find any relevant information from the search engines."
        
        # Save search results
        self._save_intermediate_data(query, "search_results", "\n".join(urls))
        overall_progress.update(1)  # Update progress bar
        
        print(f"📚 Found {len(urls)} sources. Gathering live data...")
        # Scrape webpages with progress bar
        source_data = []
        urls_to_scrape = urls[:num_sources+2]
        
        # We'll handle the progress bar manually since we're using ThreadPoolExecutor
        scrape_progress = tqdm(total=len(urls_to_scrape), desc="Scraping Webpages", position=1, leave=False)
        
        # Use the existing scrape_multiple_pages but track progress
        source_data = self.web_scraper.scrape_multiple_pages(urls_to_scrape, progress_bar=scrape_progress)
        scrape_progress.close()
        
        if not source_data:
            overall_progress.close()
            return "Sorry, I couldn't extract information from the sources."
        
        # Save scraped content
        scraped_content = "\n\n" + "="*80 + "\n\n".join(
            f"SOURCE: {data['title']} ({data['url']})\n\n{data['content'][:1000]}..."
            for data in source_data
        )
        self._save_intermediate_data(query, "scraped_content", scraped_content)
        overall_progress.update(1)  # Update progress bar
        
        print(f"📝 Analyzing {len(source_data)} sources...")
        source_summaries = []
        
        # Add progress bar for summarization
        summarize_progress = tqdm(total=len(source_data), desc="Summarizing Sources", position=1, leave=False)
        
        # Run summarization concurrently with more workers
        def summarize_source(data):
            summary = self.llm_processor.summarize_source(data)
            summarize_progress.update(1)
            print(f"✓ Analyzed: {data['title']}")
            return summary
        
        # Increase max_workers for better parallelism
        with ThreadPoolExecutor(max_workers=min(len(source_data), 8)) as executor:
            # Submit all summarization tasks
            future_to_data = {executor.submit(summarize_source, data): data for data in source_data}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_data):
                summary = future.result()
                source_summaries.append(summary)
        summarize_progress.close()
        
        # Save summaries
        summaries_content = "\n\n" + "="*80 + "\n\n".join(
            f"SOURCE: {s['title']} ({s['url']})\n\n{s['summary']}"
            for s in source_summaries
        )
        self._save_intermediate_data(query, "summaries", summaries_content)
        overall_progress.update(1)  # Update progress bar
        
        print("🧠 Synthesizing information...")
        # Add progress bar for synthesis (indeterminate since we don't know how long it will take)
        synthesis_progress = tqdm(total=100, desc="Synthesizing Information", position=1, leave=False)
        
        # Start a background updater for the synthesis progress bar
        def update_synthesis_progress():
            for i in range(100):
                time.sleep(0.1)
                synthesis_progress.update(1)
                if synthesis_progress.n >= 100:
                    synthesis_progress.reset()
        
        # We'll simulate progress since we don't know exactly how long synthesis will take
        import threading
        updater = threading.Thread(target=update_synthesis_progress)
        updater.daemon = True
        updater.start()
        
        final_answer = self.llm_processor.synthesize_information(query, source_summaries)
        
        # Close the synthesis progress bar
        synthesis_progress.close()
        
        # Save final synthesis
        self._save_intermediate_data(query, "synthesis", final_answer)
        overall_progress.update(1)  # Update progress bar
        overall_progress.close()  # Close the overall progress bar
        
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        sources_list = "\n".join([
            f"- {s['title']}: {s['url']} (Retrieved: {s.get('retrieved', 'Unknown')})"
            for s in source_summaries
        ])
        
        response = f"""
# Answer to: {query}
*Information as of {current_time}*

{final_answer}

## Sources
{sources_list}
        """
        return response
