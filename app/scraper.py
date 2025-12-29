from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

from app.static_scraper import StaticScraper, fetch_static_html
from app.js_renderer import render_with_js

logger = logging.getLogger(__name__)


async def scrape_url(url: str) -> Dict[str, Any]:
    """
    Main scraping function that coordinates static and JS rendering
    """
    errors = []
    interactions = {
        "clicks": [],
        "scrolls": 0,
        "pages": [url]
    }
    
    # Initialize result structure
    result = {
        "url": url,
        "scrapedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "title": "",
            "description": "",
            "language": "en",
            "canonical": None
        },
        "sections": [],
        "interactions": interactions,
        "errors": errors
    }
    
    try:
        # Step 1: Try static scraping first
        logger.info("Attempting static scraping...")
        html = await fetch_static_html(url)
        
        if not html:
            errors.append({
                "message": "Failed to fetch HTML content",
                "phase": "fetch"
            })
            # Try JS rendering as fallback
            logger.info("Static fetch failed, trying JS rendering...")
            html, clicks, pages, scrolls = await render_with_js(url)
            interactions["clicks"] = clicks
            interactions["pages"] = pages
            interactions["scrolls"] = scrolls
            
            if not html:
                errors.append({
                    "message": "Failed to render page with JavaScript",
                    "phase": "render"
                })
                return result
        
        # Parse with static scraper
        scraper = StaticScraper(url, html)
        
        # Check if static content is sufficient
        is_sufficient = scraper.is_sufficient()
        
        if not is_sufficient:
            logger.info("Static content insufficient, using JS rendering...")
            try:
                html, clicks, pages, scrolls = await render_with_js(url)
                interactions["clicks"] = clicks
                interactions["pages"] = pages
                interactions["scrolls"] = scrolls
                
                if html:
                    # Re-parse with JS-rendered HTML
                    scraper = StaticScraper(url, html)
                else:
                    errors.append({
                        "message": "JS rendering returned empty HTML",
                        "phase": "render"
                    })
            except Exception as e:
                logger.error(f"JS rendering failed: {e}")
                errors.append({
                    "message": f"JS rendering failed: {str(e)}",
                    "phase": "render"
                })
        
        # Extract metadata
        result["meta"] = scraper.extract_meta()
        
        # Extract sections
        sections = scraper.extract_sections()
        
        # Update sourceUrl for all sections if we visited multiple pages
        if len(interactions["pages"]) > 1:
            # For simplicity, keep the original URL as sourceUrl
            # In a more complex implementation, you'd track which section came from which page
            pass
        
        result["sections"] = sections
        
        logger.info(f"Successfully scraped {url}: {len(sections)} sections")
        
    except Exception as e:
        logger.error(f"Error in scrape_url: {e}", exc_info=True)
        errors.append({
            "message": f"Unexpected error: {str(e)}",
            "phase": "parse"
        })
    
    return result
