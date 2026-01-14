import os
import re
import json
import time
import hashlib
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
        # Dynamic rules for signing
        self.rules = {
            "static_param": "62423",
            "start": "2",
            "end": "4"
        }

    def set_auth(self, auth_data: Dict[str, str]):
        """Update auth credentials: sess, auth_id, x_bc, user_agent"""
        self.auth = auth_data
        if 'user_agent' in auth_data:
            self.user_agent = auth_data['user_agent']
            self.session.headers.update({"User-Agent": self.user_agent})

    def create_sign(self, path: str, query_string: str = "") -> Dict[str, str]:
        """
        OnlyFans request signing logic:
        Sign = SHA1(path + query + timestamp + static_param)
        The location of the signature in the final 'sign' header is determined by 'rules'.
        """
        unixtime = str(int(time.time()))
        # Combine path and query
        url_part = f"{path}{'?' + query_string if query_string else ''}"
        
        # Message to hash
        msg = f"{self.rules['static_param']}\n{unixtime}\n{url_part}\n{self.auth.get('auth_id', '0')}"
        
        sha = hashlib.sha1(msg.encode("utf-8")).hexdigest()
        
        # Format the sign header (Simplified implementation of the dynamic rule)
        # Sign header format: checksum:unixtime:static_param:auth_id
        sign_header = f"{sha}:{unixtime}:{self.rules['static_param']}:{self.auth.get('auth_id', '0')}"
        
        return {
            "sign": sha,
            "time": unixtime,
            "x-bc": self.auth.get('x_bc', ''),
            "Cookie": f"sess={self.auth.get('sess', '')}"
        }

    async def fetch_api(self, path: str, query: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        query_string = ""
        if query:
            import urllib.parse
            query_string = urllib.parse.urlencode(query)
            
        url = f"{self.api_base}{path}"
        if query_string:
            url += f"?{query_string}"
            
        full_path = f"/api2/v2{path}"
        sign_headers = self.create_sign(full_path, query_string)
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-BC": sign_headers['x-bc'],
            "Sign": sign_headers['sign'],
            "Time": sign_headers['time'],
            "Cookie": sign_headers['Cookie'],
            "Referer": "https://onlyfans.com/"
        }
        
        try:
            response = await self.session.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("OnlyFans Auth Expired (401) for %s", url)
                return {"error": "AUTH_EXPIRED"}
            else:
                logger.warning("OnlyFans API failed: %d for %s", response.status_code, url)
        except Exception as e:
            logger.error("OnlyFans API error: %s", e)
        return None

    async def fetch_creator_info(self, username: str) -> Optional[Dict[str, Any]]:
        data = await self.fetch_api(f"/users/{username}")
        if data and "id" in data:
            return {
                "id": data["id"],
                "username": data["username"],
                "display_name": data.get("name"),
                "avatar_url": data.get("avatar"),
                "platform": "onlyfans"
            }
        return None

    async def crawl_posts(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Need user ID first
        user_info = await self.fetch_creator_info(username)
        if not user_info:
            return []
            
        user_id = user_info['id']
        data = await self.fetch_api(f"/users/{user_id}/posts", query={"limit": limit, "order": "publish_date_desc"})
        
        posts = []
        if data and isinstance(data, list):
            for item in data:
                media = []
                for m in item.get('media', []):
                    if m.get('canView'):
                        media.append({"url": m.get('full'), "type": m.get('type')})
                        
                posts.append({
                    "post_id": str(item['id']),
                    "content": item.get('text'),
                    "media_urls": media,
                    "is_ppv": item.get('isFree') is False and not item.get('canView'),
                    "price": item.get('price'),
                    "created_at": item.get('postedAt'),
                    "platform": "onlyfans"
                })
        return posts
