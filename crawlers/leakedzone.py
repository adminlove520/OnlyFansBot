import logging
import asyncio
import os
import json
import httpx
from datetime import datetime
from bs4 import BeautifulSoup as bs
from crawlers.base import BaseCrawler
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LeakedZoneCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(base_url="https://leakedzone.com")
        self.source_name = "LeakedZone"
        self.platform = "leakedzone"
        self._session = None
        self.auth_file = "data/lz_auth.json"
        
        # 默认配置
        self.cookie_str = ""
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0"
        self._load_auth()

    def _load_auth(self):
        """加载持久化凭据"""
        # 先保存文件中的原始 Cookie，用于后续比较
        file_cookie = ""
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cookie_str = data.get("cookie", "")
                    file_cookie = self.cookie_str
                    self.user_agent = data.get("ua", self.user_agent)
            except: pass
        
        # 环境变量优先级
        ec = os.getenv("LEAKEDZONE_COOKIES", "").strip("'").strip('"')
        if ec: self.cookie_str = ec
        ua = os.getenv("LEAKEDZONE_UA", "").strip("'").strip('"')
        if ua: self.user_agent = ua
        
        # 自动同步 Env 到文件 (如果 Env 存在且与文件不同)
        if ec and ec != file_cookie:
            logger.info("检测到环境变量 Cookie 更新，正在同步到配置文件...")
            self.set_auth(ec, self.user_agent)

    def set_auth(self, cookie: str, ua: str = None):
        """更新并保存凭据"""
        self.cookie_str = cookie
        if ua: self.user_agent = ua
        os.makedirs("data", exist_ok=True)
        with open(self.auth_file, "w", encoding="utf-8") as f:
            json.dump({"cookie": self.cookie_str, "ua": self.user_agent}, f)
        self._session = None # 强制刷新 session

    async def _get_session(self) -> httpx.AsyncClient:
        if not self._session:
            # 清理 Cookie 中的非法字符
            clean_cookie = self.cookie_str
            if '…' in clean_cookie:
                clean_cookie = clean_cookie.replace('…', '')
                
            headers = {
                "User-Agent": self.user_agent,
                "Cookie": clean_cookie,
                "Referer": "https://leakedzone.com/",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            
            # 代理配置
            proxy = os.getenv("HTTP_PROXY")
            
            self._session = httpx.AsyncClient(
                headers=headers, 
                proxy=proxy, 
                http2=True,
                follow_redirects=True,
                timeout=20.0
            )
            
            if proxy: logger.info(f"已启用代理 (httpx): {proxy}")
        return self._session

    async def check_auth(self) -> bool:
        """极简连通性测试"""
        try:
            session = await self._get_session()
            res = await session.get(f"{self.base_url}/videos")
            if res.status_code != 200:
                logger.error(f"Auth check failed: Status {res.status_code}")
                # 尝试打印一点响应内容
                if res.status_code == 403: logger.error(f"403 Response: {res.text[:100]}")
                return False
            # 检查是否是 Cloudflare 盾
            if "Just a moment" in res.text or "Cloudflare" in res.text:
                logger.warning(f"Auth check warning: Cloudflare barrier detected. 尝试强制继续...")
                return True # 强制返回 True，赌一把后续请求能过
            return True
        except Exception as e:
            import traceback
            logger.error(f"Auth check error: {e}")
            logger.error(traceback.format_exc())
            return False

    async def fetch_html(self, url: str) -> Optional[str]:
        """统一下载接口"""
        session = await self._get_session()
        try:
            res = await session.get(url)
            if res.status_code == 200: return res.text
            if res.status_code == 403: logger.error(f"LZ 抓取被拒 (403)，请更新 Cookie")
        except Exception as e:
            logger.error(f"LZ 请求异常: {e}")
        return None

    def _parse_items(self, html: str, tag: str) -> List[Dict[str, Any]]:
        """极简解析器：仅提取核心元数据"""
        soup = bs(html, 'lxml')
        
        items = soup.find_all(['div', 'article'], class_=['movie-item', 'light-gallery-item', 'model-item'])
        posts = []
        
        today_str = datetime.now().strftime('%Y.%m.%d')

        for item in items:
            try:
                # 提取链接与 ID
                link_elem = item.find('a')
                if not link_elem: continue
                
                raw_href = link_elem.get('href', '').strip()
                href = raw_href.replace('https://leakedzone.com/', '').strip('/')
                
                parts = href.split('/')
                if not parts: continue
                
                # 创作者页面通常是 /onlyfans-creators 或 /username
                item_class = item.get('class', [])
                
                date_elem = item.find('span', class_='date')
                created_at = date_elem.text.strip() if date_elem else None
                
                # 日期过滤：仅针对 Videos/Photos
                if tag in ['Videos', 'Photos']:
                    if not created_at or created_at != today_str: continue

                # 用户名提取
                username = "unknown"
                # 判定是否为创作者卡片: 
                # 1. 显式包含 model-item 类
                # 2. 路径仅有一段 (例如 /onlyfans) 且不在 Videos/Photos 标签下
                is_creator_card = 'model-item' in item_class or (tag not in ['Videos', 'Photos'] and len(parts) == 1)
                
                if is_creator_card: 
                    username = parts[0]
                    post_id = f"model_{username}"
                else: # 视频/动态项
                    if len(parts) >= 2: username = parts[0]
                    post_id = parts[-1]

                if username == "https:": continue
                
                # 提取预览图
                img_elem = item.find('img')
                img_url = img_elem.get('src') if img_elem else ""
                if img_url.startswith('//'): img_url = f"https:{img_url}"
                elif img_url.startswith('/'): img_url = f"{self.base_url}{img_url}"
                elif img_url.startswith('data:image'): 
                    # 过滤 Base64 图片，避免 Webhook 400 Failed
                    img_url = ""

                posts.append({
                    "post_id": post_id,
                    "username": username,
                    "url": f"{self.base_url}/{href}",
                    "img_url": img_url,
                    "created_at": created_at,
                    "tag": tag,
                    "is_video": "video" in href or item.find('span', class_='play-icon') is not None
                })
            except: continue
            
        return posts

    async def crawl_tag(self, tag_path: str) -> List[Dict[str, Any]]:
        """抓取 /videos 或 /photos"""
        html = await self.fetch_html(f"{self.base_url}/{tag_path}")
        tag_name = "Videos" if tag_path == "videos" else "Photos"
        return self._parse_items(html, tag_name) if html else []

    async def crawl_category(self, cat_name: str) -> List[Dict[str, Any]]:
        """抓取 /creators?Category=OnlyFans 等"""
        html = await self.fetch_html(f"{self.base_url}/creators?Category={cat_name}")
        return self._parse_items(html, cat_name) if html else []
