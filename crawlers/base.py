import asyncio
import logging
import random
import aiohttp

logger = logging.getLogger(__name__)

class BaseCrawler:
    def __init__(self, base_url, user_agent=None):
        self.base_url = base_url
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.session = None  # Will be created in async context
        
    async def _ensure_session(self):
        """Ensure aiohttp session is created (must be called in async context)"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30.0)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                    "User-Agent": self.user_agent
                }
            )
        return self.session

    async def fetch_html(self, url, referer=None, retries=2):
        session = await self._ensure_session()
        for i in range(retries + 1):
            await asyncio.sleep(random.uniform(1.5, 3))
            try:
                headers = {"Referer": referer} if referer else {}
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning("Fetch failed (Try %d/%d): %s status %d", i+1, retries+1, url, response.status)
            except Exception as e:
                logger.error("Error fetching (Try %d/%d) %s: %s", i+1, retries+1, url, e)
                if "56" in str(e) or "reset" in str(e).lower():
                    # If connection reset, maybe change impersonation for this domain?
                    # For now just wait and retry
                    await asyncio.sleep(2)
                    continue
        return None

    def parse_video_card(self, card):
        """Parse a single video card from a list page"""
        raise NotImplementedError

    async def crawl_new_videos(self, pages=1):
        """Crawl latest videos"""
        raise NotImplementedError

    async def search(self, keyword, limit=5):
        """Search videos by keyword"""
        raise NotImplementedError

    async def crawl_video_detail(self, url):
        """Crawl full details of a video"""
        raise NotImplementedError

    async def warm_up(self):
        """Visit homepage to establish session/cookies"""
        try:
            logger.info("Warming up crawler for %s", self.base_url)
            await self.fetch_html(self.base_url)
        except Exception as e:
            logger.warning("Warm up failed for %s: %s", self.base_url, e)

    async def close(self):
        pass
