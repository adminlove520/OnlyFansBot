import asyncio
import logging
from crawlers.onlyfans import OnlyFansCrawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_onlyfans():
    crawler = OnlyFansCrawler()
    
    # Placeholder for test auth (user needs to provide real ones for 200 OK)
    test_auth = {
        "sess": "test_sess",
        "auth_id": "test_id",
        "x_bc": "test_bc",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    crawler.set_auth(test_auth)
    
    print("Testing Signature Generation...")
    sign = crawler.create_sign("/api2/v2/users/me")
    print(f"Sign: {sign}")
    
    print("\nTesting API Call (Expected 401 with fake auth)...")
    result = await crawler.fetch_api("/users/me")
    print(f"Result: {result}")
    
    await crawler.close()

if __name__ == "__main__":
    asyncio.run(test_onlyfans())
