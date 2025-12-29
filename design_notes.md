# Design Notes

## Static vs JS Fallback

**Strategy**: The scraper implements a two-stage approach with intelligent fallback:

1. **Initial Static Attempt**: First, fetch and parse the HTML using httpx. This is fast and efficient for traditional server-rendered pages.

2. **Sufficiency Check**: After parsing, we evaluate if the static content is sufficient by:
   - Checking if the body has at least 200 characters of text content
   - Looking for JS framework indicators (React root, Next.js, Angular, Vue directives)
   - If insufficient or JS indicators found → trigger Playwright rendering

3. **JS Fallback**: Use Playwright to:
   - Load the page with full browser context
   - Wait for network idle and content to render
   - Execute all interactions (clicks, scrolls, pagination)
   - Extract the final rendered HTML

This approach minimizes unnecessary browser automation while ensuring JS-heavy sites are properly rendered.

## Wait Strategy for JS

- [x] Network idle
- [x] Fixed sleep
- [x] Wait for selectors

**Details**: The implementation uses a multi-layered wait strategy:
- Primary: `wait_until='networkidle'` on page.goto() to ensure dynamic resources load
- Secondary: Fixed 2-second sleep after page load for delayed JavaScript execution
- Tertiary: After each interaction (click/scroll), we wait 1-2 seconds and attempt `wait_for_load_state('networkidle')` with a 3-second timeout to catch any triggered network requests

This combination ensures we capture content from immediate renders, delayed scripts, and user-triggered dynamic loads.

## Click & Scroll Strategy

**Click flows implemented**:
- **Tabs**: Detect `[role="tab"]`, `button[aria-selected]`, and common tab class patterns. Click up to 3 tabs per page to reveal hidden content.
- **Load More**: Identify "Load more", "Show more", "View more" buttons using text matching and aria-labels. Attempt up to 3 clicks, stopping when no more buttons are found.

**Scroll / pagination approach**:
- **Infinite Scroll**: Scroll to bottom of page up to 3 times, waiting for new content to load after each scroll. Track document height to detect when no new content appears.
- **Pagination Links**: Find "Next" links using text matching, `rel="next"`, and pagination class patterns. Follow up to 3 pagination links, recording each new URL.

**Stop conditions**:
- Maximum depth: 3 (scrolls or pages)
- Timeout: 30 seconds for initial page load, 2-3 seconds per interaction
- No new content: If document height doesn't change after scroll, or no more pagination links exist

## Section Grouping & Labels

**How sections are grouped**:
1. Identify semantic HTML5 landmarks: `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, or elements with ARIA roles
2. Each landmark becomes one section
3. If no landmarks found, parse the entire `<body>` as a single section

**Section type derivation**:
- Check element tag name and ARIA role (`<header>` + `role="banner"` → "nav")
- Examine class names and IDs for keywords:
  - "hero" → hero
  - "pricing" → pricing
  - "faq" → faq
  - "grid" → grid
  - "list" → list
- Default to "section", "nav", "footer", or "unknown" based on context

**Label generation**:
1. First, try using the first `<h1>`-`<h6>` heading found in the section
2. If no heading, check for `aria-label` attribute
3. Fallback: Use first 5-7 words of the section's text content + "..."
4. Last resort: Use tag name (e.g., "Section Content")

## Noise Filtering & Truncation

**What is filtered out**:
- **Cookie Banners**: Automatically click "Accept", "Accept all", "I agree", "OK" buttons that match cookie-related selectors
- **Modal Overlays**: Detect and click close buttons using `aria-label="Close"` and common close button classes
- **Script/Style Tags**: Excluded from text extraction
- **Very Short Text**: Text snippets under 10 characters are filtered to avoid extracting meaningless fragments

**HTML truncation**:
- `rawHtml` is limited to 5000 characters per section
- When truncated: append "..." and set `truncated: true`
- If under limit: keep full HTML and set `truncated: false`
- This prevents response payloads from becoming too large while preserving enough HTML for debugging

The filtering happens in two phases:
1. **Pre-parsing**: Playwright attempts to close overlays before content extraction
2. **Post-parsing**: Content extraction logic filters out script/style tags and low-quality text
