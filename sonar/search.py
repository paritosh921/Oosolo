"""
Search module for OllamaSonar.
Handles web search functionality through different search engines.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import re
import random
import time

class SearchEngine:
    """Base class for search engine implementations"""

    def __init__(self, headers):
        self.headers = headers
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]

    def _get_random_headers(self):
        """Get random headers to avoid detection"""
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers

    def _is_valid_url(self, url):
        """Validate URL format and content"""
        try:
            # Check basic URL structure
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
                
            # Additional validation
            if not parsed.scheme in ['http', 'https']:
                return False
                
            # Check for common invalid patterns
            invalid_patterns = [
                'google.com/search',
                'google.com/url',
                '/search?',
                'javascript:',
                'mailto:',
                'tel:',
                '#'
            ]
            return not any(pattern in url for pattern in invalid_patterns)
            
        except Exception:
            return False
        preferred_domains = [
            '.edu', '.gov', '.org', 'research', 'science',
            'academic', 'journal', 'university', 'institute'
        ]
        blocked_domains = [
            'google.com/aclk', 'googleadservices', 'doubleclick',
            'facebook.com', 'twitter.com', 'instagram.com',
            'pinterest.com', 'youtube.com', 'tiktok.com',
            'amazon.com/gp', 'ebay.com', 'shopping'
        ]
        is_preferred = any(domain in url.lower() for domain in preferred_domains)
        if any(domain in url.lower() for domain in blocked_domains):
            return False
        blocked_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar']
        if any(url.lower().endswith(ext) for ext in blocked_extensions):
            return False
        blocked_patterns = [
            r'\/tag\/', r'\/category\/', r'\/privacy', r'\/terms',
            r'\/search', r'\/shop\/', r'\/product\/', r'\/cart\/',
            r'\/login', r'\/signup', r'\/register', r'\/account'
        ]
        if any(re.search(pattern, url.lower()) for pattern in blocked_patterns):
            return False
        return True

    def search(self, query, num_results=5):
        """Search method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement search method")

class GoogleSearch(SearchEngine):
    """Google search implementation"""

    def search(self, query, num_results=5):
        """Search Google and return top result URLs"""
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results+10}"
        try:
            time.sleep(random.uniform(0.5, 1.5))
            response = requests.get(search_url, headers=self._get_random_headers(), timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []
            selectors = [
                'div[data-header-feature] a', '.yuRUbf a', '.tF2Cxc a',
                '.N54PNb a', '.g:not(.ULSxyf) a',
                '.MjjYud:not(.ULSxyf) a'
            ]
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    if href and href.startswith('http') and "google.com" not in href and href not in search_results:
                        if self._is_valid_url(href):
                            search_results.append(href)
                            if len(search_results) >= num_results:
                                break
                if len(search_results) >= num_results:
                    break
            print(f"Google search found {len(search_results)} results: {search_results}")
            return search_results
        except Exception as e:
            print(f"Error during Google search: {str(e)}")
            return []

class DuckDuckGoSearch(SearchEngine):
    """DuckDuckGo search implementation"""

    def search(self, query, num_results=5):
        """Search DuckDuckGo and return top result URLs"""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            time.sleep(random.uniform(0.5, 1.5))
            response = requests.get(search_url, headers=self._get_random_headers(), timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []
            selectors = ['.result__a', '.result__url', '.result__snippet a']
            for selector in selectors:
                results = soup.select(selector)
                for result in results:
                    href = result.get('href')
                    if href:
                        if href.startswith('/'):
                            parsed = requests.utils.urlparse(href)
                            query_params = dict(requests.utils.parse_qsl(parsed.query))
                            url = query_params.get('uddg', href)
                        else:
                            url = href
                        if url not in search_results and self._is_valid_url(url):
                            search_results.append(url)
                            if len(search_results) >= num_results:
                                break
                if len(search_results) >= num_results:
                    break
            print(f"DuckDuckGo search found {len(search_results)} results: {search_results}")
            return search_results
        except Exception as e:
            print(f"Error during DuckDuckGo search: {str(e)}")
            return []
