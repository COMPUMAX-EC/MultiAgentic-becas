from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.extraction_agent import ExtractionAgent
from config.settings import settings
from database.repository import save_scholarships
from schemas.page_schema import build_page_result
from tools.page_reader import PageReadError, read_page
from tools.text_cleaner import clean_text
from utils.logger import get_logger
from utils.url_utils import extract_domain, normalize_useful_url

logger = get_logger(__name__)

def crawl_and_extract(start_url: str, max_depth: int = 2, max_pages: int = 20, delay_seconds: float = 1.0) -> dict:
    start_url = start_url.strip()
    domain = extract_domain(start_url)
    if not domain:
        print(f"Error: Invalid start URL or domain: {start_url}")
        return {"crawled_pages": 0, "scholarships_extracted": 0, "errors": ["Invalid start URL."]}

    print(f"🚀 Starting multi-domain deep crawler on domain: {domain}")
    print(f"Parameters: Depth={max_depth}, Max Pages={max_pages}, Delay={delay_seconds}s")

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    
    total_crawled = 0
    extracted_scholarships: list[dict] = []
    errors: list[str] = []
    
    extraction_agent = ExtractionAgent()

    while queue and total_crawled < max_pages:
        current_url, depth = queue.popleft()
        
        # Normalize and clean URL
        normalized_url = normalize_useful_url(current_url)
        if not normalized_url or normalized_url in visited:
            continue
            
        visited.add(normalized_url)
        total_crawled += 1
        
        print(f"\n[{total_crawled}/{max_pages}] Crawling (depth {depth}): {normalized_url} ...")
        
        try:
            # Respectful delay
            if total_crawled > 1:
                time.sleep(delay_seconds)
                
            raw_html = read_page(normalized_url)
            cleaned = clean_text(raw_html)
            
            if not cleaned:
                print(f"⚠️ Page content was empty after cleaning: {normalized_url}")
                continue
                
            # Parse links for BFS if depth limit is not reached
            if depth < max_depth:
                soup = BeautifulSoup(raw_html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    full_url = urljoin(normalized_url, href)
                    url_domain = extract_domain(full_url)
                    
                    # Ensure same domain and not visited or queued
                    if url_domain == domain:
                        normalized_candidate = normalize_useful_url(full_url)
                        if normalized_candidate and normalized_candidate not in visited:
                            # Filter out typical non-post patterns to stay focused
                            path_lower = urlparse(normalized_candidate).path.lower()
                            if not any(bad in path_lower for bad in ["/category/", "/tag/", "/author/", "/page/", "/wp-content/"]):
                                queue.append((normalized_candidate, depth + 1))
                                
            # 3. Create PageResult and Extract structured scholarships
            source_metadata = {
                "url": normalized_url,
                "source_url": normalized_url,
                "title": f"Crawled page: {normalized_url}",
                "source_type": "official",
                "decision": "accept",
                "acceptance_status": "accepted",
                "validation_status": "accepted",
            }
            
            page_result = build_page_result(
                source=source_metadata,
                status="read_success",
                raw_text_length=len(raw_html),
                cleaned_text=cleaned,
            )
            
            print(f"🤖 Processing with ExtractionAgent using LLM model '{settings.OLLAMA_MODEL}'...")
            scholarships = extraction_agent.extract_scholarships([page_result])
            
            if scholarships:
                print(f"🎉 Successfully extracted {len(scholarships)} scholarship(s) from page!")
                for s in scholarships:
                    print(f"  - 🎓 {s.get('scholarship_name')} ({s.get('institution') or 'Unknown Institution'})")
                extracted_scholarships.extend(scholarships)
            else:
                print("ℹ️ No scholarships found on this page.")
                
        except PageReadError as exc:
            err_msg = f"Failed to read page {normalized_url}: {exc}"
            print(f"❌ {err_msg}")
            errors.append(err_msg)
        except Exception as exc:
            err_msg = f"Unexpected error on {normalized_url}: {exc}"
            print(f"❌ {err_msg}")
            errors.append(err_msg)

    # 4. Save results to the SQLite knowledge base
    saved_summary = {"inserted": 0, "updated": 0}
    if extracted_scholarships:
        print(f"\n💾 Saving {len(extracted_scholarships)} unique scholarships to database...")
        saved_summary = save_scholarships(extracted_scholarships)
        print(f"💾 Database update summary: Inserted={saved_summary['inserted']}, Updated={saved_summary['updated']}")
        
    return {
        "crawled_pages": total_crawled,
        "scholarships_extracted": len(extracted_scholarships),
        "database_inserted": saved_summary.get("inserted", 0),
        "database_updated": saved_summary.get("updated", 0),
        "errors": errors,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Domain Scholarship Deep Crawler")
    parser.add_argument("--url", required=True, help="Starting URL to crawl.")
    parser.add_argument("--depth", type=int, default=2, help="Recursion depth limit (default 2).")
    parser.add_argument("--limit", type=int, default=20, help="Maximum pages to crawl (default 20).")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default 1.0).")
    args = parser.parse_args()

    start_time = time.time()
    result = crawl_and_extract(
        start_url=args.url,
        max_depth=args.depth,
        max_pages=args.limit,
        delay_seconds=args.delay
    )
    duration = time.time() - start_time

    print("\n" + "=" * 50)
    print("CRAWLER RUN COMPLETE SUMMARY")
    print("=" * 50)
    print(f"Duration: {duration:.2f} seconds")
    print(f"Pages Crawled: {result['crawled_pages']}")
    print(f"Scholarships Extracted: {result['scholarships_extracted']}")
    print(f"Scholarships Inserted: {result['database_inserted']}")
    print(f"Scholarships Updated: {result['database_updated']}")
    print(f"Errors Encountered: {len(result['errors'])}")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
