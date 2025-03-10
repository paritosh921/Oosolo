"""
Web scraper module for OllamaSonar.
Handles fetching and parsing content from web pages.
"""

import time
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import re
import random
from urllib.parse import urlparse
from datetime import datetime

class WebScraper:
    """Web scraper for extracting content from web pages"""

    def __init__(self, headers):
        self.headers = headers
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'
        ]

    def _get_random_headers(self):
        """Get random headers to avoid detection"""
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        headers['Accept-Language'] = 'en-US,en;q=0.5'
        return headers

    def _clean_text(self, text):
        """Clean extracted text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'\b(?:Home|About|Contact Us|Privacy Policy|Terms of Use|Cookie Policy|Sign Up|Log In|Subscribe|Newsletter)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:\d+\s*Comments|Share this article|Download Now|Read More|Click Here|Follow Us)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:Facebook|Twitter|Instagram|LinkedIn|Pinterest|YouTube|TikTok)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:Advertisement|Sponsored|Promotion|Ad)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'©.*?\d{4}.*?reserved', '', text, flags=re.IGNORECASE)
        return text

    def _extract_paragraphs(self, soup):
        """Extract meaningful paragraphs from the page"""
        paragraphs = []
        p_elements = soup.find_all('p')
        for p in p_elements:
            text = p.get_text().strip()
            if len(text) > 40 and not self._is_navigation_text(text):
                paragraphs.append(text)
        return '\n\n'.join(paragraphs)

    def _is_navigation_text(self, text):
        """Check if text is likely navigation or UI element"""
        nav_patterns = [
            r'^(?:Home|Menu|Navigation|Search|Categories)$',
            r'^(?:Previous|Next|Page \d+)$',
            r'^(?:Share|Like|Comment|Subscribe)$'
        ]
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in nav_patterns)

    def _extract_date(self, soup):
        """Extract publication date with priority on recent content"""
        current_date = datetime.now()
        schema_date = soup.find('meta', {'property': 'article:published_time'})
        if schema_date:
            return schema_date['content']
        text = soup.get_text()
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\w+ \d{1,2}, \d{4})'
        ]
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            dates = list(matches)
            if dates:
                return max(dates, key=lambda x: x.group(1)).group(1)
        return current_date.strftime("%Y-%m-%d")

    def scrape_webpage(self, url):
        """Scrape content with focus on recent and relevant information"""
        try:
            if any(ad_domain in url for ad_domain in ['ad_domain=', 'adclick', 'googleadservices', 'doubleclick']):
                return {
                    "url": url,
                    "title": "Advertisement URL",
                    "content": "Skipped advertisement URL",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            time.sleep(random.uniform(0.5, 1.5))
            headers = self._get_random_headers()
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']):
                element.extract()
            title = soup.title.string if soup.title else url
            title = title.strip()
            date = self._extract_date(soup)
            main_content = None
            content_selectors = [
                'article', 'main', '.content', '.post', '.entry', '#content',
                '.article-content', '.post-content', '.entry-content',
                '[role="main"]', '.main-content', '.story-content',
                '.article-body', '.story-body', '.news-content',
                '.blog-post', '.page-content', '.article__content'
            ]
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    paragraphs = content.find_all('p')
                    if paragraphs:
                        main_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 40])
                    else:
                        main_content = content.get_text(separator="\n")
                    break
            if not main_content or len(main_content) < 500:
                main_content = self._extract_paragraphs(soup)
            if not main_content or len(main_content) < 500:
                main_content = soup.get_text(separator="\n")
            text = self._clean_text(main_content)
            if len(text.strip()) < 300:
                return {
                    "url": url,
                    "title": "Low Quality Content",
                    "content": "Content too short or not meaningful",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            domain = urlparse(url).netloc
            return {
                "url": url,
                "title": title,
                "date": date,
                "domain": domain,
                "content": text[:10000],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {
                "url": url,
                "title": "Error",
                "content": f"Failed to scrape: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    def scrape_multiple_pages(self, urls, progress_bar=None):
        """Scrape multiple webpages in parallel with adaptive concurrency"""
        results = []
        max_workers = min(10, len(urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_webpage, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result.get("title") not in ["Error", "Advertisement URL", "Low Quality Content"]:
                    results.append(result)
                if progress_bar is not None:
                    progress_bar.update(1)
        return results
