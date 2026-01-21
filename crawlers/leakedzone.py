import logging
import asyncio
import os
import json
import time
from datetime import datetime
from curl_cffi.requests import AsyncSession
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
        self.platform_cache_file = "data/lz_platforms.json"
        
        # 默认配置
        self.cookie_str = ""
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.platforms_cache = {}
        
        self._load_auth()
        self._load_platforms()

    def _load_auth(self):
        """加载持久化凭据：lz_auth.json 是唯一真理来源"""
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cookie_str = data.get("cookie", "")
                    self.user_agent = data.get("ua", self.user_agent)
                    updated_at = data.get("updated_at", "未知")
                    logger.info(f"已加载持久化凭据 (更新时间: {updated_at})")
            except Exception as e:
                logger.warning(f"加载 auth_file 失败: {e}")
        
        # 兼容性检查：如果是环境变量
        ec = os.getenv("LEAKEDZONE_COOKIES", "").strip("'").strip('"')
        if ec and not self.cookie_str:
            logger.info("检测到环境变量中的旧 Cookie，正在迁移...")
            self.cookie_str = ec
            self.set_auth(ec)

    def set_auth(self, cookie: str, ua: str = None):
        """更新并保存凭据"""
        self.cookie_str = cookie
        if ua: self.user_agent = ua
        os.makedirs("data", exist_ok=True)
        data = {
            "cookie": self.cookie_str, 
            "ua": self.user_agent,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.auth_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        self._session = None # 强制刷新 session
        logger.info("✅ 授权凭据已更新并保存")

    def _load_platforms(self):
        """加载已知的创作者平台缓存"""
        if os.path.exists(self.platform_cache_file):
            try:
                with open(self.platform_cache_file, "r", encoding="utf-8") as f:
                    self.platforms_cache = json.load(f)
            except: pass

    def _save_platforms(self):
        """保存创作者平台缓存"""
        os.makedirs("data", exist_ok=True)
        with open(self.platform_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.platforms_cache, f, indent=4)

    async def get_creator_platform(self, username: str) -> str:
        """获取创作者对应的平台 (如 Reddit), 具有缓存机制"""
        if username in self.platforms_cache:
            return self.platforms_cache[username]
        
        # 如果缓存没有，则去爬一下 profile 页
        url = f"{self.base_url}/{username}"
        logger.info(f"🔍 正在抓取创作者主页以识别分类: {url}")
        html = await self.fetch_html(url)
        if not html: return "Unknown"
        
        try:
            soup = bs(html, 'lxml')
            # 方案 A: 寻找包含 Category 文字的元素
            # 常见结构: <b>Category:</b> <a href="...">OnlyFans</a>
            platform = "Unknown"
            
            # 使用精准查找
            cat_container = soup.find(string=lambda s: s and "Category:" in s)
            if cat_container:
                # 通常是 <b>Category:</b> 后面的 <a>
                parent = cat_container.parent
                cat_val = parent.find_next_sibling('a') or parent.find('a')
                if not cat_val:
                    # 尝试在父级的兄弟中找
                    cat_val = parent.find_next('a')
                
                if cat_val:
                    platform = cat_val.text.strip()
                    logger.info(f"✨ 识别到创作者 {username} 平台: {platform}")
            
            # 方案 B: 如果 A 失败，尝试 model-info 区域
            if platform == "Unknown":
                model_info = soup.find('div', class_='model-info')
                if model_info:
                    cat_link = model_info.find('a', href=lambda h: h and 'Category=' in h)
                    if cat_link: platform = cat_link.text.strip()

            if platform != "Unknown":
                self.platforms_cache[username] = platform
                self._save_platforms()
                return platform
        except Exception as e:
            logger.warning(f"解析创作者 {username} 平台时出错: {e}")
        
        return "Unknown"

    async def _get_session(self) -> AsyncSession:
        if not self._session:
            # 代理配置
            proxy = os.getenv("HTTP_PROXY")
            
            # 基础 Header 构造
            headers = {
                "User-Agent": self.user_agent,
                "Referer": "https://leakedzone.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }

            # 【GHA 专项优化】在 Linux 环境下，impersonate 建议选择更低或更稳的版本
            # 并且需要补全客户端指纹头
            imp = "chrome120"
            if "Linux" in self.user_agent:
                imp = "chrome110"
                headers["Sec-Ch-Ua-Platform"] = '"Linux"'
            else:
                headers["Sec-Ch-Ua-Platform"] = '"Windows"'
            
            # 使用 curl_cffi 模拟浏览器特征
            self._session = AsyncSession(
                impersonate=imp,
                headers=headers,
                proxies={"http": proxy, "https": proxy} if proxy else None,
                allow_redirects=True,
                timeout=40
            )
            
            # 手动合并 Cookie
            if self.cookie_str:
                for item in self.cookie_str.split(';'):
                    item = item.strip()
                    if '=' in item:
                        k, v = item.split('=', 1)
                        if k.strip() and v.strip():
                            self._session.cookies.set(k.strip(), v.strip(), domain="leakedzone.com")
            
            if proxy: logger.info(f"已启用代理 (curl_cffi): {proxy}")
        return self._session

    async def check_auth(self) -> bool:
        """强化版连通性与 CF 挑战检查"""
        try:
            session = await self._get_session()
            res = await session.get(f"{self.base_url}/videos")
            
            if res.status_code == 200:
                # 检查伪装后的 Cloudflare 页面
                if "Just a moment" in res.text or "Checking your browser" in res.text:
                    logger.error("🛑 依然被 Cloudflare 拦截 (即使状态码为 200)")
                    return False
                # 检查是否存在内容
                if "movie-item" in res.text or "videos" in res.url:
                    return True
                
            if res.status_code == 403:
                logger.error("🚫 抓取被拒 (403): Cookie 可能已过期")
            else:
                logger.error(f"Auth check failed: Status {res.status_code}")
            
            return False
        except Exception as e:
            logger.error(f"Auth check error: {e}")
            return False

    async def fetch_html(self, url: str) -> Optional[str]:
        """统一下载接口"""
        session = await self._get_session()
        try:
            res = await session.get(url)
            if res.status_code == 200:
                if "Just a moment" in res.text:
                    logger.warning("发现 Cloudflare 挑战，可能需要刷新 Cookie")
                    return None
                return res.text
            logger.warning(f"请求 {url} 失败: {res.status_code}")
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
