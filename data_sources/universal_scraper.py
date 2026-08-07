import requests
import re
import io
import time
import sqlite3
from typing import Optional, Callable, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import PyPDF2
import logging

logger = logging.getLogger(__name__)

class UniversalScraper:
    def __init__(self, max_pages=1500, max_pdf_pages=50):
        self.max_pages = max_pages
        self.max_pdf_pages = max_pdf_pages
        self.visited = set()
        self.corpus = []
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        
        with sqlite3.connect("scraper_cache.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS page_cache (url TEXT PRIMARY KEY, text_content TEXT, links TEXT)")

    def scrape_urls(self, urls: List[str], expected_domain: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
        self.visited = set()
        self.corpus = []
        pages_scraped = 0
        total_urls = len(urls)

        for url in urls:
            if url in self.visited:
                continue
                
            self.visited.add(url)
            
            try:
                # Check Database Cache
                with sqlite3.connect("scraper_cache.db") as conn:
                    row = conn.execute("SELECT text_content FROM page_cache WHERE url = ?", (url,)).fetchone()
                    
                if row:
                    cached_text = row[0]
                    if cached_text:
                        self.corpus.append(cached_text)
                        pages_scraped += 1
                        if status_callback:
                            status_callback(f"Cache Hit ({pages_scraped}/{total_urls}): {url}")
                    continue
                    
                # Live Scrape
                msg = f"Downloading Target URL ({pages_scraped+1}/{total_urls}): {url}"
                logger.info(msg)
                if status_callback:
                    status_callback(msg)
                time.sleep(0.5)
                
                if expected_domain not in urlparse(url).netloc:
                    continue
                    
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    continue
                    
                ctype = response.headers.get('Content-Type', '').lower()
                text_cache = ""
                
                if 'application/pdf' in ctype or url.lower().endswith('.pdf'):
                    text = self._parse_pdf(response.content)
                    if text:
                        text_cache = f"--- SOURCE (PDF): {url} ---\n{text}\n"
                        self.corpus.append(text_cache)
                        pages_scraped += 1
                elif 'text/html' in ctype:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text = self._extract_text(soup)
                    if text:
                        text_cache = f"--- SOURCE (HTML): {url} ---\n{text}\n"
                        self.corpus.append(text_cache)
                        pages_scraped += 1
                                
                # Save to Cache 
                with sqlite3.connect("scraper_cache.db") as conn:
                    conn.execute("INSERT OR REPLACE INTO page_cache (url, text_content, links) VALUES (?, ?, ?)",
                                 (url, text_cache, "[]"))
                                 
            except Exception as e:
                logger.warning(f"Failed {url}: {e}")
                
        logger.info(f"Target multi-url download complete. Ingested {pages_scraped} highly targeted pages.")
        return "\n".join(self.corpus)

    def _extract_text(self, soup: BeautifulSoup) -> str:
        for script in soup(["script", "style", "svg"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_pdf(self, pdf_bytes) -> str:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            return " ".join([reader.pages[i].extract_text() or "" for i in range(min(len(reader.pages), self.max_pdf_pages))])
        except Exception:
            return ""
