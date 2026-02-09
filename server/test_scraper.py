import asyncio
from scraper import scraper
import sys

# Windows/event loop policy fix if needed, but we are on Mac
# if sys.platform == 'win32':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test():
    print("Initializing scraper...")
    await scraper.initialize()
    
    keywords = ["MOFLS-18", "MOFWP-03"]
    
    # Original loop for keywords
    for kw in keywords:
        print(f"\nSearching for {kw}...")
        result = await scraper.search_product(kw)
        print(f"Result for {kw}:")
        print(result)

    # Added search for '레깅스'
    print("\nSearching for '레깅스'...")
    try:
        result = await scraper.search_product("레깅스")
        print(f"Result for '레깅스':")
        print(result)
    except Exception as e:
        print(f"Error searching for '레깅스': {e}")
    
    await scraper.close()

if __name__ == "__main__":
    asyncio.run(test())
