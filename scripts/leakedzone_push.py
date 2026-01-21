import asyncio
import logging
import os
import sys
import json
import argparse
from datetime import datetime
import random
import httpx
from dotenv import load_dotenv

# 将项目根目录添加到 Python 路径，以便导入 crawlers 模块
# 无论脚本从哪里运行，都能正确找到 crawlers 包
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlers.leakedzone import LeakedZoneCrawler

# 加载配置
load_dotenv(override=True)

# 日志配置 (必须在 load_dotenv 之后定义 logger 涉及的 context)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LZ-Push-v6")

DB_FILE = "data/lz_history.json"
# 剥离单双引号
WEBHOOK_URL = os.getenv("LZ_WEBHOOK_URL", "").strip("'").strip('"')
if not WEBHOOK_URL:
    logger.error("❌ LZ_WEBHOOK_URL 为空，请检查 .env 配置")

def load_history():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return set(json.load(f))
        except: return set()
    return set()

def save_history(history):
    os.makedirs("data", exist_ok=True)
    with open(DB_FILE, "w") as f: json.dump(list(history), f)

async def send_webhook(embed):
    if not WEBHOOK_URL:
        logger.error("未配置 LZ_WEBHOOK_URL")
        return
    proxy_url = os.getenv("HTTP_PROXY")
    async with httpx.AsyncClient(proxy=proxy_url) as client:
        for i in range(3):
            try:
                res = await client.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=15)
                if res.status_code in [200, 204]:
                    return
                # 如果是 429 限流，多等一会
                if res.status_code == 429:
                    await asyncio.sleep(5)
                logger.warning(f"Webhook 发送失败 (尝试 {i+1}/3): {res.status_code}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Webhook 网络异常 (尝试 {i+1}/3): {e}")
                await asyncio.sleep(2)
        logger.error("❌ Webhook 发送最终失败")

async def push_item(item):
    """构建极简美化卡片 (v6.0)"""
    tag = item['tag']
    username = item['username']
    post_id = item['post_id']
    is_video = item['is_video']
    
    # 分类逻辑对齐
    # 如果 tag 在 5 大平台中，它是“创作者入驻/动态”
    # Load categories dynamically if possible, or use hardcoded list for check
    default_platforms = ["OnlyFans", "Fansly", "Celebrity+Nudes", "Reddit", "Snapchat"]
    is_platform_update = tag in default_platforms or tag not in ['Videos', 'Photos']
    
    title = f"LeakedZone-{tag}动态"
    color = random.randint(0, 0xFFFFFF)
    
    embed = {
        "title": title,
        "url": item['url'],
        "description": f"发现来自创作者 **@{username}** 的新动态。\n\n> 🆔 唯一标识: `{post_id}`\n> 🏷️ 源标签: `{tag}`",
        "color": color,
        "fields": [
            {
                "name": "创作者",
                "value": f"[@{username}]({item['url']})",
                "inline": True
            },
            {
                "name": "分类",
                "value": "创作者信息" if is_platform_update else ("视频" if is_video else "图片"),
                "inline": True
            }
        ],
        "footer": {
            "text": f"Power By 东方隐侠安全团队 • {datetime.now().strftime('%H:%M')}"
        }
    }
    
    # 预览图逻辑
    # 只有当确实有预览图且不是空的，才设置
    if item['img_url'] and "default" not in item['img_url']:
        embed["image"] = {"url": item['img_url']}
        embed["thumbnail"] = {"url": item['img_url']}
    
    # 增加点击详情
    embed["fields"].append({
        "name": "访问详情",
        "value": f"[🔗 点击访问详情]({item['url']})",
        "inline": False
    })

    if item['created_at']:
        embed["fields"].append({
            "name": "发布时间",
            "value": f"`{item['created_at']}`",
            "inline": True
        })

    await send_webhook(embed)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", help="Update cookies and UA")
    args = parser.parse_args()

    crawler = LeakedZoneCrawler()
    
    if args.login:
        # 简单分割，格式: "cookie|ua"
        parts = args.login.split('|')
        cookie = parts[0]
        ua = parts[1] if len(parts) > 1 else None
        crawler.set_auth(cookie, ua)
        logger.info("✅ 认证凭据已更新")
        if await crawler.check_auth():
            logger.info("✨ 凭据校验成功！")
        else:
            logger.error("❌ 凭据校验失败，请检查输入")
        return

    # 1. 启动校验
    if not await crawler.check_auth():
        logger.error("🚨 无法通过 LeakedZone 验证，请运行 --login 更新 Cookie")
        return

    history = load_history()
    all_items = []

    # 2. 采集数据
    logger.info("✅正在采集 (当日视频&图片)...")
    all_items.extend(await crawler.crawl_tag("videos"))
    all_items.extend(await crawler.crawl_tag("photos"))

    logger.info("✅正在采集平台分类...")
    
    # Load configurable categories
    platforms = ["OnlyFans", "Fansly", "Celebrity+Nudes", "Reddit", "Snapchat"]
    try:
        # 优先读取 leakedzone-category.json
        cat_file = "crawlers/leakedzone-category.json"
        if not os.path.exists(cat_file): cat_file = "data/lz_auth.json"
        
        with open(cat_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "categories" in data and isinstance(data["categories"], list):
                platforms = data["categories"]
                logger.info(f"已加载自定义分类: {platforms}")
    except: pass

    for p in platforms:
        all_items.extend(await crawler.crawl_category(p))
        await asyncio.sleep(1)

    # 3. 去重与推送
    new_count = 0
    try:
        for item in all_items:
            unique_key = f"{item['tag']}_{item['post_id']}"
            if unique_key not in history:
                logger.info(f"🆕 发现新动态: @{item['username']} ({item['tag']})")
                await push_item(item)
                history.add(unique_key)
                new_count += 1
                # 增量保存，防止中途由于网络异常或限流导致记录丢失
                save_history(history)
                await asyncio.sleep(1)
            
            if new_count >= 30: break # 单次上限
    except Exception as e:
        logger.error(f"⚠️ 推送过程中断: {e}")
    finally:
        save_history(history)
        logger.info(f"✅ 处理完毕，当前周期新增: {new_count}")

if __name__ == "__main__":
    asyncio.run(main())
