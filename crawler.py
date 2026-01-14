import asyncio
import logging
from crawlers.missav import MissavCrawler as Missav
from crawlers.jable import JableCrawler as Jable
from crawlers.hohoj import HohoJCrawler as HohoJ
from crawlers.memo import MemoCrawler as Memo

logger = logging.getLogger(__name__)

from crawlers.onlyfans import OnlyFansCrawler
from crawlers.twitter import TwitterCrawler

logger = logging.getLogger(__name__)

class CrawlerManager:
    def __init__(self, db):
        self.db = db
        self.crawlers = {
            "onlyfans": OnlyFansCrawler(),
            "twitter": TwitterCrawler()
        }

    async def init_sessions(self):
        # Load auth from DB for each platform
        for platform, crawler in self.crawlers.items():
            auth_data = self.db.get_auth(platform)
            if auth_data:
                logger.info("Initializing %s with stored auth", platform)
                crawler.set_auth(auth_data)

    async def get_crawler(self, platform):
        return self.crawlers.get(platform.lower())

    async def close(self):
        for crawler in self.crawlers.values():
            await crawler.close()
