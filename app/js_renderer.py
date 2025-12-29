from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from typing import Optional, List, Dict, Any
import logging
import asyncio

from app.static_scraper import StaticScraper

logger = logging.getLogger(__name__)


class JSRenderer:
    """Renderer for JavaScript-heavy pages using Playwright"""
    
    def __init__(self, url: str):
        self.url = url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.visited_urls: List[str] = [url]
        self.clicks: List[str] = []
        self.scroll_count: int = 0
    
    async def __aenter__(self):
        """Context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        # Set viewport for consistent rendering
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def render(self) -> tuple[str, List[str], List[str], int]:
        """
        Render the page and return HTML, clicks, visited URLs, and scroll count
        """
        try:
            # Navigate to the page
            logger.info(f"Navigating to {self.url}")
            await self.page.goto(self.url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for any delayed JS to execute
            await asyncio.sleep(2)
            
            # Try to close common overlays
            await self._close_overlays()
            
            # Try to detect and handle interactions
            await self._handle_interactions()
            
            # Get the final HTML
            html = await self.page.content()
            
            return html, self.clicks, self.visited_urls, self.scroll_count
            
        except PlaywrightTimeoutError:
            logger.error(f"Timeout loading {self.url}")
            # Return partial content
            html = await self.page.content() if self.page else ""
            return html, self.clicks, self.visited_urls, self.scroll_count
        except Exception as e:
            logger.error(f"Error rendering page: {e}", exc_info=True)
            raise
    
    async def _close_overlays(self):
        """Try to close common overlays like cookie banners"""
        overlay_selectors = [
            # Cookie banners
            'button:has-text("Accept")',
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'button:has-text("OK")',
            '[aria-label*="cookie" i] button',
            '[id*="cookie" i] button',
            '[class*="cookie" i] button',
            # Close buttons
            '[aria-label="Close"]',
            'button[aria-label*="close" i]',
            '.modal-close',
            '.close-button',
        ]
        
        for selector in overlay_selectors:
            try:
                button = self.page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click(timeout=2000)
                    logger.info(f"Closed overlay: {selector}")
                    await asyncio.sleep(0.5)
                    break
            except:
                continue
    
    async def _handle_interactions(self):
        """Handle tabs, load more buttons, and scrolling"""
        # Try to click tabs
        await self._handle_tabs()
        
        # Try to handle "Load More" buttons
        await self._handle_load_more()
        
        # Try pagination
        await self._handle_pagination()
        
        # Try infinite scroll
        await self._handle_scroll()
    
    async def _handle_tabs(self):
        """Try to click through tabs"""
        tab_selectors = [
            '[role="tab"]',
            'button[aria-selected]',
            '.tab-button',
            '[class*="tab" i]:not([role="tabpanel"])',
        ]
        
        for selector in tab_selectors:
            try:
                tabs = self.page.locator(selector)
                count = await tabs.count()
                
                if count > 0:
                    logger.info(f"Found {count} tabs with selector: {selector}")
                    # Click first 3 tabs
                    for i in range(min(3, count)):
                        try:
                            tab = tabs.nth(i)
                            if await tab.is_visible(timeout=1000):
                                await tab.click(timeout=2000)
                                self.clicks.append(f"{selector}[{i}]")
                                logger.info(f"Clicked tab {i}: {selector}")
                                await asyncio.sleep(1)  # Wait for content to load
                        except:
                            continue
                    break  # Found and clicked tabs, don't try other selectors
            except:
                continue
    
    async def _handle_load_more(self):
        """Try to click 'Load More' or 'Show More' buttons"""
        load_more_selectors = [
            'button:has-text("Load more")',
            'button:has-text("Show more")',
            'button:has-text("View more")',
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            '[aria-label*="load more" i]',
            '[class*="load-more" i]',
            '[class*="show-more" i]',
        ]
        
        for _ in range(3):  # Try up to 3 times
            clicked = False
            for selector in load_more_selectors:
                try:
                    button = self.page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click(timeout=2000)
                        self.clicks.append(selector)
                        logger.info(f"Clicked load more: {selector}")
                        await asyncio.sleep(2)  # Wait for content to load
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                break  # No more buttons found
    
    async def _handle_pagination(self):
        """Try to follow pagination links"""
        pagination_selectors = [
            'a:has-text("Next")',
            'a:has-text("next")',
            '[aria-label*="next" i]',
            '[rel="next"]',
            '.pagination .next',
            '.pager .next',
        ]
        
        for _ in range(3):  # Follow up to 3 pages
            clicked = False
            for selector in pagination_selectors:
                try:
                    link = self.page.locator(selector).first
                    if await link.is_visible(timeout=2000):
                        # Get the href before clicking
                        href = await link.get_attribute('href')
                        if href:
                            await link.click(timeout=2000)
                            logger.info(f"Clicked pagination: {selector}")
                            await asyncio.sleep(2)  # Wait for page to load
                            
                            # Record new URL
                            current_url = self.page.url
                            if current_url not in self.visited_urls:
                                self.visited_urls.append(current_url)
                            
                            clicked = True
                            break
                except:
                    continue
            
            if not clicked:
                break  # No more pagination
    
    async def _handle_scroll(self):
        """Handle infinite scroll"""
        max_scrolls = 3
        previous_height = 0
        
        for i in range(max_scrolls):
            try:
                # Get current scroll height
                current_height = await self.page.evaluate('document.body.scrollHeight')
                
                if current_height == previous_height and i > 0:
                    break  # No new content loaded
                
                # Scroll to bottom
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                self.scroll_count += 1
                logger.info(f"Scroll {i + 1}/{max_scrolls}")
                
                # Wait for content to load
                await asyncio.sleep(2)
                
                # Try to wait for network idle
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=3000)
                except:
                    pass
                
                previous_height = current_height
                
            except Exception as e:
                logger.error(f"Error during scroll {i}: {e}")
                break


async def render_with_js(url: str) -> tuple[Optional[str], List[str], List[str], int]:
    """Render a page with JavaScript and return HTML, clicks, URLs, and scroll count"""
    try:
        async with JSRenderer(url) as renderer:
            return await renderer.render()
    except Exception as e:
        logger.error(f"Error in JS rendering: {e}")
        return None, [], [url], 0
