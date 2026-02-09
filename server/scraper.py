import asyncio
from playwright.async_api import async_playwright, BrowserContext, Page
import traceback

class PlaywrightScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initializes the browser and context once."""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            # Launch simple chromium (lightweight)
            self.browser = await self.playwright.chromium.launch(headless=True)
            
            # Create a persistent context with Desktop User Agent
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            
            # Pre-create a page to keep ready
            self.page = await self.context.new_page()

    async def close(self):
        """Clean up resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def search_product(self, model_no: str):
        """
        Searches for a product by model number and scrapes the first result using API interception.
        """
        async with self._lock:
            if not self.page:
                await self.initialize()
            
            # Ensure model_no is clean
            clean_model_no = model_no.strip().upper()
            
            # Variable to store captured data
            search_data = {"products": []}

            # Define response handler
            async def handle_response(response):
                try:
                    if "dalpha" in response.url and "response" in response.url:
                        if "json" in response.headers.get("content-type", ""):
                            json_data = await response.json()
                            # print(f"Captured Dalpha JSON from {response.url}: {str(json_data)[:100]}...")
                            if "payload" in json_data and "products" in json_data["payload"]:
                                new_products = json_data["payload"]["products"]
                                if new_products:
                                    search_data["products"].extend(new_products)
                except:
                    pass

            async def handle_request(request):
                # if "dalpha" in request.url and request.method == "POST":
                #      print(f"Request to {request.url}: {request.post_data}")
                pass

            # Attach handler
            self.page.on("response", handle_response)
            self.page.on("request", handle_request)
            
            # Candidate URLs to try
            candidate_urls = [
                f"https://andar.co.kr/product/search.html?keyword={clean_model_no}&order_by=recommend",
                f"https://andar.co.kr/product/search.html?keyword={clean_model_no}&order_by=recent",
                f"https://andar.co.kr/product/search.html?keyword={clean_model_no}&order_by=price",
                f"https://andar.co.kr/product/search.html?keyword={clean_model_no}" # Fallback
            ]

            final_url = candidate_urls[0]
            
            try:
                for target_url in candidate_urls:
                    if search_data["products"]:
                        break
                    
                    print(f"Navigating to {target_url}")
                    final_url = target_url
                    try:
                        await self.page.goto(target_url, wait_until="networkidle", timeout=15000)
                        
                        # Wait for data
                        for _ in range(6):
                            if search_data["products"]:
                                break
                            await self.page.wait_for_timeout(500)
                    except Exception as e:
                        print(f"Navigation failed for {target_url}: {e}")
                
                # Remove handler
                try:
                    self.page.remove_listener("response", handle_response)
                    self.page.remove_listener("request", handle_request)
                except:
                    pass

                if not search_data["products"]:
                     return {
                        "status": "fail",
                        "message": "Not found",
                        "keyword": clean_model_no,
                        "product_url": final_url
                    }

                # Parse up to top 3 products
                results = []
                for product in search_data["products"][:3]:
                    # Extract fields
                    product_name = product.get("name", "Unknown Product")
                    price = product.get("price", "N/A")
                    retail_price = product.get("retail_price", "N/A")
                    product_link = product.get("link", final_url)
                    
                    def format_price(p):
                        if not p or p == '0': return "N/A"
                        try:
                            return f"{int(p):,}원"
                        except:
                            return p

                    sale_price_fmt = format_price(price)
                    if retail_price and retail_price != '0' and retail_price != price:
                        original_price_fmt = format_price(retail_price)
                    else:
                        original_price_fmt = sale_price_fmt # Fallback

                    results.append({
                        "product_name": product_name.strip(),
                        "original_price": original_price_fmt,
                        "sale_price": sale_price_fmt,
                        "product_url": product_link
                    })

                return {
                    "status": "success",
                    "data": results,
                    "keyword": clean_model_no
                }

            except Exception as e:
                print(f"Scraping error: {e}")
                import traceback
                traceback.print_exc()
                # Clean up listener if exception
                try:
                    self.page.remove_listener("response", handle_response)
                except:
                    pass
                    
                return {
                    "status": "error",
                    "message": str(e),
                    "keyword": clean_model_no
                }

# Singleton instance
scraper = PlaywrightScraper()
