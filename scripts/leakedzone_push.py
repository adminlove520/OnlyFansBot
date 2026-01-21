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

VERSION = "1.0.0"
try:
    version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
    if os.path.exists(version_path):
        with open(version_path, "r") as f:
            VERSION = f.read().strip()
except:
    pass

REPO_URL = "https://github.com/adminlove520/OnlyFansBot" # 仓库地址

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

async def send_startup_card(platforms):
    """发送启动通知卡片"""
    logger.info("📡 发送启动通知卡片...")
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    embed = {
        "title": "🛰️ LeakedZone 涩涩先锋",
        "url": REPO_URL,
        "description": f"欢迎使用 **OnlyFans-Bot** 自动化情报服务。\n扫描程序已就绪，正在精准捕获最新涩涩。",
        "color": 0x00ff00,
        "fields": [
            {"name": "当前版本", "value": f"`{VERSION}`", "inline": True},
            {"name": "启动时间", "value": f"`{start_time}`", "inline": True},
            {"name": "监控范围", "value": f"共 `{len(platforms)}` 个平台 ", "inline": False},
            {"name": "开源仓库", "value": f"[OnlyFans-Bot @ GitHub]({REPO_URL})", "inline": False}
        ],
        "footer": {
            "text": f"情报同步中 | Power By OnlyFans-Bot"
        }
    }
    await send_webhook(embed)

async def fetch_douban_movies():
    """获取豆瓣新片榜"""
    url = "https://api.baiwumm.com/api/douban-movic" 
    try:
        # trust_env=False 强制不使用系统代理，verify=False 忽略 SSL 证书错误(提高兼容性)
        async with httpx.AsyncClient(trust_env=False, verify=False) as client:
            res = await client.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "data" in data: return data["data"]
    except Exception as e:
        logger.warning(f"获取豆瓣电影失败 (请检查网络或 API): {e}")
    return []

async def push_movie_item(movie):
    """推送单条电影信息 """
    title = movie.get("title", "未知电影")
    score = movie.get("score") or "N/A"
    hot = movie.get("hot", 0)
    douban_url = movie.get("url", "https://movie.douban.com")
    
    desc_lines = []
    desc_lines.append(f"**评分**: ⭐ `{score}`")
    if hot > 0:
        desc_lines.append(f"**热度**: 🔥 `{hot}`")
    
    embed = {
        "title": f"🍿 豆瓣新片：{title}",
        "url": douban_url,
        "description": "\n".join(desc_lines),
        "color": 0x00BB29, # 豆瓣绿
        "fields": [
            {"name": "直达通道", "value": f"[🔗 点击查看详情(豆瓣)]({douban_url})", "inline": True}
        ],
        "footer": {"text": f"OnlyFans-Bot 豆瓣精选·新片速递"}
    }
    await send_webhook(embed)

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

async def push_item(crawler: LeakedZoneCrawler, item):
    """构建卡片 (涩涩适度) 针对用户链接跳转深度优化"""
    tag = item['tag']
    username = item['username']
    post_id = item['post_id']
    is_video = item['is_video']
    
    # 获取创作者所属平台 (Category)
    platform = await crawler.get_creator_platform(username)
    
    # 1. 链接逻辑优化
    profile_url = f"https://leakedzone.com/{username}"
    # 标题指向具体类型页: /username/photo 或 /username/video
    type_suffix = "video" if is_video else "photo"
    type_url = f"{profile_url}/{type_suffix}"
    # 平台列表指向分类页: /creators?Category=Reddit
    category_list_url = f"https://leakedzone.com/creators?Category={platform}"
    
    title_type = "Videos" if is_video else "Photos"
    title = f"LeakedZone-{title_type}动态"
    color = random.randint(0, 0xFFFFFF)
    
    embed = {
        "title": title,
        "url": type_url,
        "description": f"发现来自创作者 **[@{username}]({profile_url})** 的新动态。\n\n> 🆔 唯一标识: `{post_id}`\n> 🏷️ 源标签: `{tag}`",
        "color": color,
        "fields": [
            {
                "name": "创作者",
                "value": f"[@{username}]({profile_url})",
                "inline": True
            },
            {
                "name": "分类",
                "value": f"Category: [{platform}]({category_list_url}) | {'视频' if is_video else '图片'}",
                "inline": True
            }
        ],
        "footer": {
            "text": f"OnlyFans-Bot 情报先锋 • {datetime.now().strftime('%H:%M')}"
        }
    }
    
    # 预览图逻辑
    if item['img_url'] and "default" not in item['img_url']:
        embed["image"] = {"url": item['img_url']}
        embed["thumbnail"] = {"url": item['img_url']}
    
    # 增加点击详情 (指向具体动态帖)
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

    # --- 1. 初始化变量与环境 ---
    history = load_history()
    all_items = []
    
    # 初始化监控平台列表
    platforms = ["OnlyFans", "Fansly", "Celebrity+Nudes", "Reddit", "Snapchat"]
    try:
        # 优先读取配置文件
        cat_file = "crawlers/leakedzone-category.json"
        if not os.path.exists(cat_file): cat_file = "data/lz_auth.json"
        
        with open(cat_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "categories" in data and isinstance(data["categories"], list):
                platforms = data["categories"]
                logger.info(f"已加载监控平台: {platforms}")
    except: pass

    # --- 2. 权限校验 ---
    if not await crawler.check_auth():
        logger.error("🚨 无法通过 LeakedZone 验证（Cloudflare 拦截或 Cookie 过期）")
        logger.info("💡 正在尝试自动运行刷新脚本...")
        try:
            refresh_script = os.path.join(project_root, "scripts", "lz_refresh.py")
            process = await asyncio.create_subprocess_exec(
                sys.executable, refresh_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info("✅ 自动化刷新脚本执行成功，正在重新初始化...")
                crawler = LeakedZoneCrawler() # 重新加载凭据
                if await crawler.check_auth():
                    logger.info("✨ 刷新后校验成功！")
                else:
                    logger.error("❌ 刷新后依然校验失败，请手动运行 scripts/lz_refresh.py")
                    return
            else:
                logger.error(f"❌ 自动化刷新脚本执行失败: {stderr.decode()}")
                return
        except Exception as e:
            logger.error(f"❌ 触发刷新脚本异常: {e}")
            return

    # --- 3. 发送启动通报 ---
    await send_startup_card(platforms)
    
    # --- 4. 执行采集 ---
    logger.info("✅正在采集 (当日视频&图片)...")
    all_items.extend(await crawler.crawl_tag("videos"))
    all_items.extend(await crawler.crawl_tag("photos"))

    logger.info("✅正在采集各平台详情动态...")
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
                await push_item(crawler, item)
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

    # 4. 推送豆瓣新片 (作为福利环节)
    logger.info("🍿 （戒色，来点小清新~）正在获取豆瓣新片榜...")
    movies = await fetch_douban_movies()
    if movies:
        # 发送转场分隔卡片
        await send_webhook({
            "title": "✅ 情报扫描任务圆满完成",
            "description": "所有当日动态已处理完毕， **OnlyFans-Bot** 豆瓣精选：\n🍿 **今日豆瓣新片速递**",
            "color": 0x00BB29
        })
        await asyncio.sleep(2)

        logger.info(f"📊 发现 {len(movies)} 部新片，正在推送...")
        for m in movies:
            await push_movie_item(m)
            await asyncio.sleep(1)
    
    logger.info(f"✨ 这一轮推送工作已圆满完成！")

if __name__ == "__main__":
    asyncio.run(main())
