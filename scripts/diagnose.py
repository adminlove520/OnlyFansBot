
import asyncio
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crawlers.onlyfans import OnlyFansCrawler

logging.basicConfig(level=logging.INFO)
crawler = OnlyFansCrawler()

async def test():
    print("Testing Adapter Integration...")
    info = await crawler.fetch_creator_info("skybrixo")
    if info:
        print(f"✅ Success! Found user: {info}")
    else:
        print("❌ Failed to fetch user info")
        
    print("\nTesting Posts Fetch...")
    posts = await crawler.crawl_posts("skybrixo", limit=5)
    print(f"Post count: {len(posts)}")
    if posts:
        print(f"✅ First post: {posts[0]['post_id']}")
    else:
        print("❌ No posts found")

if __name__ == "__main__":
    asyncio.run(test())
