from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional
import logging

from app.scraper import scrape_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Universal Website Scraper")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


class ScrapeRequest(BaseModel):
    url: HttpUrl


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the frontend"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    """Scrape a URL and return structured JSON"""
    try:
        url_str = str(request.url)
        
        # Validate URL scheme
        if not url_str.startswith(('http://', 'https://')):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid URL scheme. Only http:// and https:// are supported.",
                    "result": None
                }
            )
        
        logger.info(f"Scraping URL: {url_str}")
        result = await scrape_url(url_str)
        
        return {"result": result}
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "error": str(e),
                "result": None
            }
        )
    except Exception as e:
        logger.error(f"Error scraping URL: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Internal server error: {str(e)}",
                "result": None
            }
        )
