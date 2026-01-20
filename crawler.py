import asyncio
import logging

logger = logging.getLogger(__name__)

from crawlers.onlyfans import OnlyFansCrawler
from crawlers.twitter import TwitterCrawler
from crawlers.leakedzone import LeakedZoneCrawler

logger = logging.getLogger(__name__)

class CrawlerManager:
    def __init__(self, db):
        self.db = db
        self.crawlers = {
            "onlyfans": OnlyFansCrawler(),
            "twitter": TwitterCrawler(),
            "leakedzone": LeakedZoneCrawler()
        }

    async def init_sessions(self):
        # 1. 自动恢复逻辑：如果数据库为空，尝试从根目录 auth.json 恢复
        import os
        import json
        auth_file = "auth.json"
        
        # 检查 OnlyFans 是否有认证
        of_auth = self.db.get_auth("onlyfans")
        if not of_auth and os.path.exists(auth_file):
            try:
                with open(auth_file, 'r') as f:
                    local_auth = json.load(f)
                if local_auth:
                    logger.info("检测到本地 auth.json，正在自动恢复 OnlyFans 认证信息...")
                    self.db.save_auth("onlyfans", local_auth.get("auth_id", "unknown"), local_auth)
                    of_auth = local_auth
            except Exception as e:
                logger.error(f"读取本地 auth.json 失败: {e}")

        # 2. 从数据库加载所有平台的认证
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
