import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from scraper import scraper
import time
import asyncio

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# [수정된 부분] 프론트엔드 경로 설정 및 정적 파일 서빙
# ---------------------------------------------------------
# path calculation
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)
client_dir = os.path.join(base_dir, "client")

@app.on_event("startup")
async def startup_event():
    print("------------------------------------------------")
    print(">> Server Starting...")
    print(f">> Current Dir: {current_dir}")
    print(f">> Base Dir:    {base_dir}")
    print(f">> Client Dir:  {client_dir}")
    
    if os.path.exists(client_dir):
        print(f">> Client Dir Exists. Files: {os.listdir(client_dir)}")
    else:
        print(">> [WARNING] Client Dir NOT FOUND!")
        
    print(">> Initializing Playwright Scraper...")
    print("------------------------------------------------")
    await scraper.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Playwright Scraper...")
    await scraper.close()

# API Endpoints
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
        duration = time.time() - start_time
        result["duration_sec"] = round(duration, 2)
        return result
    except Exception as e:
        print(f"Error searching for {keyword}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "keyword": keyword
        }

# 1. Explicit Root Handler (for debugging and certainty)
@app.get("/")
async def serve_root():
    index_path = os.path.join(client_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Front-end index.html not found", "searched_at": index_path}

# 2. Static Files Mount (Catch-all for app.js, style.css, etc.)
# Must be AFTER specific routes
app.mount("/", StaticFiles(directory=client_dir, html=True), name="client")