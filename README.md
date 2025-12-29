# Universal Website Scraper

A full-stack web scraping application that can handle both static and JavaScript-rendered websites, with support for interactive elements like tabs, pagination, and infinite scroll.

## Features

- ✅ Static HTML scraping using httpx and selectolax
- ✅ JavaScript rendering with Playwright
- ✅ Automatic fallback from static to JS rendering
- ✅ Click flow handling (tabs, "Load More" buttons)
- ✅ Pagination and infinite scroll support (depth ≥ 3)
- ✅ Section-aware content extraction
- ✅ Noise filtering (cookie banners, overlays)
- ✅ Interactive JSON viewer frontend
- ✅ Full JSON export functionality

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Static Scraping**: httpx + selectolax
- **JS Rendering**: Playwright (Chromium)
- **Frontend**: Jinja2 templates with vanilla JavaScript
- **Language**: Python 3.10+

## Setup and Run

### Prerequisites

- Python 3.10 or higher
- Bash shell (Git Bash on Windows, or native on Linux/Mac)

### Quick Start

1. Clone the repository and navigate to the project directory

2. Make the run script executable and run it:

```bash
chmod +x run.sh
./run.sh
```

The script will:
- Create a virtual environment
- Install all dependencies
- Install Playwright browsers (Chromium)
- Start the server on http://localhost:8000

### Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. Enter a URL in the input field
3. Click "Scrape" and wait for results
4. Explore sections by clicking on them
5. Download the full JSON using the "Download JSON" button

### API Endpoints

#### Health Check
```bash
GET /healthz
```

Response:
```json
{
  "status": "ok"
}
```

#### Scrape URL
```bash
POST /scrape
Content-Type: application/json

{
  "url": "https://example.com"
}
```

Response includes:
- Page metadata (title, description, language, canonical)
- Structured sections with content
- Interaction details (clicks, scrolls, pages visited)
- Any errors encountered

## Test URLs

The following URLs were used for testing and validation:

1. **https://en.wikipedia.org/wiki/Artificial_intelligence** — Static page
   - Tests static HTML parsing
   - Multiple sections with tables and lists
   - Rich structured content

2. **https://vercel.com/** — JS-heavy marketing page
   - Tests JavaScript rendering
   - Interactive tabs and content sections
   - Lazy-loaded images

3. **https://news.ycombinator.com/** — Pagination
   - Tests pagination to depth ≥ 3
   - Simple static structure with "More" link
   - Demonstrates multi-page scraping

Additional test URLs:
- **https://developer.mozilla.org/en-US/docs/Web/JavaScript** — Mixed static/dynamic
- **https://infinite-scroll.com/demo/full-page/** — Infinite scroll testing

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── scraper.py           # Main scraping coordinator
│   ├── static_scraper.py    # Static HTML scraping
│   ├── js_renderer.py       # Playwright JS rendering
│   └── templates/
│       └── index.html       # Frontend UI
├── run.sh                   # Setup and run script
├── requirements.txt         # Python dependencies
├── capabilities.json        # Feature capabilities
├── design_notes.md          # Design decisions
└── README.md               # This file
```

## Known Limitations

1. **Anti-bot Protection**: Some websites with aggressive anti-bot measures (Cloudflare, etc.) may block the scraper
2. **Same-Origin**: Currently optimized for single-domain scraping
3. **Performance**: JS rendering adds 10-30 seconds per page depending on complexity
4. **Memory**: Large pages with many images may consume significant memory
5. **Rate Limiting**: No built-in rate limiting (use responsibly)

## Timeouts and Limits

- HTTP request timeout: 30 seconds
- Page load timeout: 30 seconds
- Maximum scrolls: 3
- Maximum pagination depth: 3 pages
- Maximum tabs clicked: 3
- HTML truncation: 5000 characters per section

## Error Handling

The scraper includes comprehensive error handling:
- Invalid URLs are rejected gracefully
- Timeout errors are reported with partial data
- Network errors trigger fallback strategies
- All errors are captured in the `errors` array with phase information

## Development

To run in development mode with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## License

This project is created for the Lyftr AI Full-Stack Assignment.
