from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
import httpx
import logging
import re

logger = logging.getLogger(__name__)


class StaticScraper:
    """Scraper for static HTML content"""
    
    def __init__(self, url: str, html: str):
        self.url = url
        self.html = html
        self.tree = HTMLParser(html)
    
    def extract_meta(self) -> Dict[str, Any]:
        """Extract metadata from the page"""
        meta = {
            "title": "",
            "description": "",
            "language": "en",
            "canonical": None
        }
        
        # Extract title
        title_tag = self.tree.css_first('title')
        if title_tag:
            meta["title"] = title_tag.text(strip=True)
        else:
            # Try og:title
            og_title = self.tree.css_first('meta[property="og:title"]')
            if og_title and og_title.attributes.get('content'):
                meta["title"] = og_title.attributes['content']
        
        # Extract description
        desc_tag = self.tree.css_first('meta[name="description"]')
        if desc_tag and desc_tag.attributes.get('content'):
            meta["description"] = desc_tag.attributes['content']
        else:
            # Try og:description
            og_desc = self.tree.css_first('meta[property="og:description"]')
            if og_desc and og_desc.attributes.get('content'):
                meta["description"] = og_desc.attributes['content']
        
        # Extract language
        html_tag = self.tree.css_first('html')
        if html_tag and html_tag.attributes.get('lang'):
            meta["language"] = html_tag.attributes['lang']
        
        # Extract canonical URL
        canonical_tag = self.tree.css_first('link[rel="canonical"]')
        if canonical_tag and canonical_tag.attributes.get('href'):
            meta["canonical"] = urljoin(self.url, canonical_tag.attributes['href'])
        
        return meta
    
    def extract_sections(self) -> List[Dict[str, Any]]:
        """Extract sections from the page"""
        sections = []
        
        # Try to find main content area
        main = self.tree.css_first('main, [role="main"], #main, .main')
        if main:
            sections.extend(self._parse_container(main, "main"))
        
        # Extract header if exists
        header = self.tree.css_first('header, [role="banner"]')
        if header:
            sections.extend(self._parse_container(header, "nav"))
        
        # Extract navigation
        nav = self.tree.css_first('nav, [role="navigation"]')
        if nav and nav != header:
            sections.extend(self._parse_container(nav, "nav"))
        
        # Extract sections
        for section in self.tree.css('section, article, [role="region"]'):
            sections.extend(self._parse_container(section, "section"))
        
        # Extract footer
        footer = self.tree.css_first('footer, [role="contentinfo"]')
        if footer:
            sections.extend(self._parse_container(footer, "footer"))
        
        # If no sections found, parse the body
        if not sections:
            body = self.tree.css_first('body')
            if body:
                sections.extend(self._parse_container(body, "unknown"))
        
        # Ensure we have at least one section
        if not sections:
            sections.append({
                "id": "default-0",
                "type": "unknown",
                "label": "Default Section",
                "sourceUrl": self.url,
                "content": self._extract_empty_content(),
                "rawHtml": "",
                "truncated": False
            })
        
        return sections
    
    def _parse_container(self, container, default_type: str = "section") -> List[Dict[str, Any]]:
        """Parse a container element into sections"""
        sections = []
        
        # Get section type
        section_type = self._determine_section_type(container, default_type)
        
        # Extract content
        content = self._extract_content(container)
        
        # Generate label
        label = self._generate_label(container, content)
        
        # Get raw HTML (truncated)
        raw_html = container.html
        truncated = False
        if len(raw_html) > 5000:
            raw_html = raw_html[:5000] + "..."
            truncated = True
        
        # Generate unique ID
        section_id = f"{section_type}-{len(sections)}"
        
        sections.append({
            "id": section_id,
            "type": section_type,
            "label": label,
            "sourceUrl": self.url,
            "content": content,
            "rawHtml": raw_html,
            "truncated": truncated
        })
        
        return sections
    
    def _determine_section_type(self, element, default: str) -> str:
        """Determine the type of section"""
        tag_name = element.tag.lower() if hasattr(element, 'tag') else ''
        
        # Check for specific elements
        if tag_name == 'header' or element.attributes.get('role') == 'banner':
            return 'nav'
        if tag_name == 'nav' or element.attributes.get('role') == 'navigation':
            return 'nav'
        if tag_name == 'footer' or element.attributes.get('role') == 'contentinfo':
            return 'footer'
        
        # Check classes and IDs for common patterns
        class_name = element.attributes.get('class', '').lower()
        id_name = element.attributes.get('id', '').lower()
        
        if 'hero' in class_name or 'hero' in id_name:
            return 'hero'
        if 'pricing' in class_name or 'pricing' in id_name:
            return 'pricing'
        if 'faq' in class_name or 'faq' in id_name:
            return 'faq'
        if 'grid' in class_name or 'grid' in id_name:
            return 'grid'
        if 'list' in class_name or 'list' in id_name:
            return 'list'
        
        return default
    
    def _extract_content(self, element) -> Dict[str, Any]:
        """Extract content from an element"""
        content = {
            "headings": [],
            "text": "",
            "links": [],
            "images": [],
            "lists": [],
            "tables": []
        }
        
        # Extract headings
        for heading in element.css('h1, h2, h3, h4, h5, h6'):
            text = heading.text(strip=True)
            if text:
                # Clean up escape sequences and normalize whitespace
                text = text.replace('\\n', ' ').replace('\\t', ' ').replace('\n', ' ').replace('\t', ' ')
                text = ' '.join(text.split())  # Collapse multiple spaces
                content["headings"].append(text)
        
        # Extract text (excluding script and style)
        text_parts = []
        for node in element.css('p, span, div, li, td, th'):
            text = node.text(strip=True)
            if text and len(text) > 10:  # Filter out very short text
                # Clean up escape sequences and normalize whitespace
                text = text.replace('\\n', ' ').replace('\\t', ' ').replace('\n', ' ').replace('\t', ' ')
                text = ' '.join(text.split())  # Collapse multiple spaces
                text_parts.append(text)
        content["text"] = " ".join(text_parts[:50])  # Limit to first 50 text elements
        
        # Extract links
        for link in element.css('a[href]'):
            href = link.attributes.get('href', '')
            text = link.text(strip=True)
            if href and not href.startswith(('#', 'javascript:')):
                absolute_url = urljoin(self.url, href)
                # Clean up link text
                if text:
                    text = text.replace('\\n', ' ').replace('\\t', ' ').replace('\n', ' ').replace('\t', ' ')
                    text = ' '.join(text.split())
                content["links"].append({
                    "text": text or href,
                    "href": absolute_url
                })
        
        # Extract images
        for img in element.css('img[src]'):
            src = img.attributes.get('src', '')
            alt = img.attributes.get('alt', '')
            if src:
                absolute_src = urljoin(self.url, src)
                content["images"].append({
                    "src": absolute_src,
                    "alt": alt
                })
        
        # Extract lists
        for ul in element.css('ul, ol'):
            list_items = []
            for li in ul.css('li'):
                text = li.text(strip=True)
                if text:
                    list_items.append(text)
            if list_items:
                content["lists"].append(list_items)
        
        # Extract tables
        for table in element.css('table'):
            table_data = []
            for row in table.css('tr'):
                row_data = []
                for cell in row.css('td, th'):
                    row_data.append(cell.text(strip=True))
                if row_data:
                    table_data.append(row_data)
            if table_data:
                content["tables"].append(table_data)
        
        return content
    
    def _extract_empty_content(self) -> Dict[str, Any]:
        """Return empty content structure"""
        return {
            "headings": [],
            "text": "",
            "links": [],
            "images": [],
            "lists": [],
            "tables": []
        }
    
    def _generate_label(self, element, content: Dict[str, Any]) -> str:
        """Generate a label for the section"""
        # Try to use first heading
        if content["headings"]:
            return content["headings"][0]
        
        # Try to use aria-label
        aria_label = element.attributes.get('aria-label')
        if aria_label:
            return aria_label
        
        # Use first 5-7 words of text
        if content["text"]:
            words = content["text"].split()[:7]
            label = " ".join(words)
            if len(words) >= 7:
                label += "..."
            return label
        
        # Fallback
        tag_name = element.tag if hasattr(element, 'tag') else 'Section'
        return f"{tag_name.capitalize()} Content"
    
    def is_sufficient(self) -> bool:
        """Check if static content is sufficient"""
        # Check if there's enough text content
        body = self.tree.css_first('body')
        if not body:
            return False
        
        text = body.text(strip=True)
        if len(text) < 200:  # Less than 200 characters suggests JS rendering
            return False
        
        # Check for common JS framework indicators
        body_html = body.html.lower()
        js_indicators = [
            'id="root"',
            'id="app"',
            'id="__next"',
            'data-reactroot',
            'ng-app',
            'v-cloak'
        ]
        
        for indicator in js_indicators:
            if indicator in body_html:
                logger.info(f"Found JS indicator: {indicator}")
                return False
        
        return True


async def fetch_static_html(url: str) -> Optional[str]:
    """Fetch HTML content using httpx"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        return None
