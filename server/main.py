from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from scaper import scraper
import time
import asyncio

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Initializing Playwright Scraper...")
    await scraper.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Playwright Scraper...")
    await scraper.close()

@app.get("/api/search")
async def search_product(keyword: str = Query(..., description="Base model number or product name to search")):
    """
    Search for a product by its base model number or name.
    """
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")
    
    start_time = time.time()
    try:
        result = await scraper.search_product(keyword)
        # Calculate processing time
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)
        
        # In a real app, we might want to return 404 for "status": "fail"
        # but for this hybrid app, a 200 OK with status="fail" is easier for the client to handle
        # and immediately trigger the fallback flow.
        
        return result
    except Exception as e:
        print(f"Error searching for {keyword}: {e}")
        # Return a structured error so client can handle it gracefully
        return {
            "status": "error",
            "message": str(e),
            "keyword": keyword
        }
