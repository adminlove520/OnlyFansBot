import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

class OnlyFansCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(base_url="https://onlyfans.com")
        self.source_name = "OnlyFans"
        self.api_base = "https://onlyfans.com/api2/v2"
        self.auth: Dict[str, str] = {}
    async def fetch_via_adapter(self, command: str, username: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Call the external OF-Scraper adapter script"""
        # Current file: OnlyFans-Bot/crawlers/onlyfans.py
        # Root (OnlyFans-Bot): ..
        # Adapter: ../scripts/of_adapter.py
        # Venv: ../OF-Scraper/venv/Scripts/python.exe
        root_dir = os.path.dirname(os.path.dirname(__file__))
        adapter_script = os.path.join(root_dir, "scripts", "of_adapter.py")
        venv_python = os.path.join(root_dir, "OF-Scraper", "venv", "Scripts", "python.exe")
        
        if not os.path.exists(venv_python):
            logger.error(f"❌ Venv Python not found at: {venv_python}")
            return None
            
        cmd = [venv_python, adapter_script, command, username, "--limit", str(limit)]
        
        try:
            logger.info(f"🔄 Calling Adapter: {command} {username}...")
            # Run in thread pool to avoid blocking async loop
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"❌ Adapter failed (code {process.returncode}): {stderr.decode()}")
                return None
                
            output = stdout.decode().strip()
            if not output:
                logger.error("❌ Adapter returned empty output")
                return None
                
            result = json.loads(output)
            if not result.get("success"):
                logger.error(f"❌ Adapter reported error: {result.get('error')}")
                if stderr:
                    logger.error(f"🔍 Adapter Traceback: {stderr.decode()}")
                return None
                
            return result.get("data")
            
        except Exception as e:
            logger.error(f"❌ Adapter execution error: {e}")
            return None

    def _update_auth_file(self):
        """Sync current auth to OF-Scraper's auth.json"""
        if not self.auth:
            return
            
        # Target path (Default Windows path for OF-Scraper)
        # Note: OF-Scraper uses 'main_profile' by default as seen in logs
        auth_path = os.path.expanduser("~/.config/ofscraper/profiles/main_profile/auth.json")
        os.makedirs(os.path.dirname(auth_path), exist_ok=True)
        
        # Prepare content (keys matching schema.py)
        content = {
            "sess": self.auth.get('sess', ''),
            "auth_id": self.auth.get('auth_id', '0'),
            "auth_uid": self.auth.get('auth_uid', self.auth.get('auth_id', '0')), # Fallback to auth_id if uid missing
            "user_agent": self.auth.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0'),
            "x-bc": self.auth.get('x_bc', '')
        }
        
        try:
            with open(auth_path, 'w') as f:
                json.dump(content, f, indent=4)
            logger.info(f"✅ Synced credentials to {auth_path}")
        except Exception as e:
            logger.error(f"❌ Failed to sync auth file: {e}")

    def set_auth(self, auth_data: Dict[str, str]):
        """Update auth credentials and sync to disk"""
        super().set_auth(auth_data) # Updates self.auth in BaseCrawler (if it exists) or just manually
        self.auth = auth_data # Ensure it is set
        self._update_auth_file()

    async def fetch_creator_info(self, username: str) -> Optional[Dict[str, Any]]:
        data = await self.fetch_via_adapter("profile", username)
        if data and ("id" in data or "username" in data):
            return {
                "id": str(data.get("id")),
                "username": data.get("username"),
                "display_name": data.get("name"),
                "avatar_url": data.get("avatar"),
                "platform": "onlyfans"
            }
        return None

    async def crawl_posts(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        data = await self.fetch_via_adapter("timeline", username, limit)
        
        posts = []
        if data and isinstance(data, list):
            for item in data:
                # OF-Scraper returns processed objects or raw json?
                # Based on timeline.py it returns list of dicts from API
                
                # Check structure
                post_id = str(item.get('id'))
                text = item.get('text')
                posted_at = item.get('postedAt')
                
                media = []
                for m in item.get('media', []):
                    if m.get('canView'):
                        media.append({"url": m.get('full'), "type": m.get('type')})
                        
                posts.append({
                    "post_id": post_id,
                    "content": text,
                    "media_urls": media,
                    "is_ppv": item.get('isFree') is False and not item.get('canView'),
                    "price": item.get('price'),
                    "created_at": posted_at,
                    "platform": "onlyfans"
                })
        return posts

    # Legacy methods removed/unused
    def create_sign(self, path: str, query_string: str = "") -> Dict[str, str]:
        return {}
    async def fetch_api(self, path: str, query: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        return None

