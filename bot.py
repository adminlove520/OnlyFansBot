import os
import asyncio
import discord
import logging
from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from database import Database
from crawler import CrawlerManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

class SirenBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database("data/onlyfans.db")
        self.crawler_mgr = CrawlerManager(self.db)
        self.check_interval = int(os.getenv('CHECK_INTERVAL', 15))

    async def setup_hook(self):
        await self.crawler_mgr.init_sessions()
        self.check_new_posts.start()
        logger.info("Bot setup hook completed.")

    async def on_ready(self):
        logger.info(f'✅ Discord 已连接：{self.user} (ID: {self.user.id})')
        channel = self.get_channel(CHANNEL_ID)
        if channel:
            try:
                await channel.send("🚀 **OnlyFans 监控助手已在线！**\n系统已成功连接到 Discord，并正在初始化抓取模块。")
            except Exception as e:
                logger.error(f"发送启动通知失败: {e}")

    @tasks.loop(minutes=15)
    async def check_new_posts(self):
        logger.info("Checking for new posts...")
        
        # 1. 检查订阅的创作者动态
        creators = self.db.get_all_creators()
        for creator in creators:
            crawler = await self.crawler_mgr.get_crawler(creator['platform'])
            if not crawler: continue
            
            try:
                posts = await crawler.crawl_posts(creator['username'])
                for post in posts:
                    if not self.db.is_post_exists(post['post_id'], post['platform']):
                        post['creator_id'] = creator['id']
                        saved = self.db.save_post(post)
                        if saved:
                            await self.push_post_to_subscribers(creator, post)
                
                # Update last check time
                last_post_id = posts[0]['post_id'] if posts else None
                self.db.update_creator_check(creator['id'], last_post_id)
            except Exception as e:
                logger.error("Error polling creator %s: %s", creator['username'], e)

        # 2. LeakedZone 全局动态发现 (无需订阅即可推送)
        try:
            lz_crawler = await self.crawler_mgr.get_crawler("leakedzone")
            if lz_crawler:
                logger.info("Scanning LeakedZone for global latest posts...")
                latest_posts = await lz_crawler.crawl_latest()
                for post in latest_posts:
                    if not self.db.is_post_exists(post['post_id'], post['platform']):
                        # 自动为新作者创建记录（如果不存在）
                        display_name = post.get('username')
                        creator_id = self.db.add_creator(post['username'], post['platform'], display_name)
                        post['creator_id'] = creator_id
                        saved = self.db.save_post(post)
                        if saved:
                            # 构造简易创作者对象进行推送
                            fake_creator = {
                                'id': creator_id,
                                'username': post['username'],
                                'display_name': display_name,
                                'platform': post['platform'],
                                'avatar_url': None
                            }
                            await self.push_post_to_subscribers(fake_creator, post, is_global=True)
        except Exception as e:
            logger.error(f"Error in LeakedZone global check: {e}")

    async def push_post_to_subscribers(self, creator, post, is_global=False):
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return
        
        sub_ids = self.db.get_subscribers(creator['id'])
        mentions = " ".join([f"<@{uid}>" for uid in sub_ids])
        
        embed = self.create_post_embed(creator, post)
        
        title_prefix = "🌟 **[发现]**" if is_global else "📢"
        content = f"{title_prefix} **{creator['display_name'] or creator['username']}** 有新动态！\n{mentions if mentions else ''}"
        
        # Determine media to push (Simplified large file handling)
        files = []
        import json
        media_list = json.loads(post['media_urls'])
        
        # Placeholder for downloading and sending files (optional based on size)
        # For now, we just rely on the embed's image if available
        
        await channel.send(content=content, embed=embed)

    def create_post_embed(self, creator, post):
        embed = discord.Embed(
            title=f"New post from {creator['display_name'] or creator['username']}",
            description=post.get('content')[:1000] if post.get('content') else "No text content",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_author(name=creator.get('username'), icon_url=creator.get('avatar_url'))
        
        import json
        media_list = json.loads(post['media_urls'])
        if media_list:
            # Show first image/video as thumbnail/image
            embed.set_image(url=media_list[0]['url'])
        
        if post.get('is_ppv'):
            embed.add_field(name="💰 PPV Content", value=f"Price: {post.get('price', 'Unknown')}", inline=False)
            
        embed.add_field(name="Platform", value=post['platform'].capitalize(), inline=True)
        embed.set_footer(text="Siren OnlyFans Monitor")
        return embed

bot = SirenBot()

# --- Admin Prefix Command ---
@bot.command(name="sync")
async def sync(ctx):
    """强制同步 Slash Commands"""
    if ctx.author.id != ADMIN_USER_ID:
        return await ctx.send("❌ 只有管理员可以执行此操作。")
    
    await ctx.send("🔄 正在同步 Slash Commands...")
    try:
        await bot.tree.sync()
        await ctx.send("✅ 指令同步完成！")
    except Exception as e:
        await ctx.send(f"❌ 同博失败: {e}")

# --- User Slash Commands ---
@bot.tree.command(name="subscribe", description="订阅创作者动态")
@app_commands.describe(username="创作者用户名", platform="平台 (onlyfans/twitter/leakedzone)")
async def subscribe(interaction: discord.Interaction, username: str, platform: str = "onlyfans"):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        pass
    
    platform = platform.lower()
    crawler = await bot.crawler_mgr.get_crawler(platform)
    if not crawler:
        return await interaction.followup.send(f"❌ 不支持的平台: {platform}")
        
    info = await crawler.fetch_creator_info(username)
    if not info:
        return await interaction.followup.send(f"❌ 未在 {platform} 找到用户: {username}")
        
    creator_id = bot.db.add_creator(info['username'], info['platform'], info['display_name'], info['avatar_url'])
    bot.db.subscribe(interaction.user.id, creator_id, info['platform'])
    
    await interaction.followup.send(f"✅ 已成功订阅 **{info['display_name']}** ({info['username']}) @ {platform}")

@bot.tree.command(name="list", description="查看我的订阅列表")
async def list_subs(interaction: discord.Interaction):
    subs = bot.db.get_subscriptions(interaction.user.id)
    if not subs:
        return await interaction.response.send_message("你目前没有任何订阅。")
        
    lines = ["📋 **你的订阅列表:**"]
    for s in subs:
        lines.append(f"- **{s['username']}** @ {s['platform']}")
    
    await interaction.response.send_message("\n".join(lines))

# --- Admin Slash Commands ---
@bot.tree.command(name="admin_auth", description="配置爬虫账号认证信息 (仅限管理员)")
@app_commands.describe(
    platform="平台", 
    username="账号名", 
    sess="SESS Cookie", 
    auth_id="Auth ID", 
    x_bc="X-BC Header", 
    user_agent="User Agent",
    x_hash="X-Hash Header (可选)",
    x_of_rev="X-OF-Rev (可选)",
    manual_sign="手动签名 (可选，从浏览器 F12 Network 复制)",
    manual_time="手动时间戳 (可选，与 manual_sign 配对使用)"
)
async def admin_auth(interaction: discord.Interaction, platform: str, username: str, sess: str, auth_id: str, x_bc: str, user_agent: str, x_hash: str = "", x_of_rev: str = "", manual_sign: str = "", manual_time: str = ""):
    if interaction.user.id != ADMIN_USER_ID:
        return await interaction.response.send_message("❌ 权限不足。", ephemeral=True)
        
    auth_data = {
        "sess": sess,
        "auth_id": auth_id,
        "x_bc": x_bc,
        "user_agent": user_agent,
        "x_hash": x_hash,
        "x_of_rev": x_of_rev,
        "manual_sign": manual_sign,
        "manual_time": manual_time
    }
    bot.db.save_auth(platform, username, auth_data)
    
    # Reload crawler auth
    crawler = await bot.crawler_mgr.get_crawler(platform)
    if crawler:
        crawler.set_auth(auth_data)
        
    await interaction.response.send_message(f"✅ 已更新 {platform} 账号 **{username}** 的认证信息！\n系统将立即尝试使用新凭据。", ephemeral=True)
    
    # Send a quick check to the channel if OnlyFans
    if platform == "onlyfans" and crawler:
        info = await crawler.fetch_creator_info(username)
        channel = bot.get_channel(CHANNEL_ID)
        if info and "error" not in info:
            logger.info(f"✅ OnlyFans 认证成功：{username}")
            if channel:
                await channel.send(f"✅ **OnlyFans 认证成功！**\n当前账号：**{username}**\n系统已开始监控动态。")
        else:
            logger.error(f"❌ OnlyFans 认证验证失败：{username}")
            if channel:
                await channel.send(f"❌ **OnlyFans 认证失败！**\n账号 **{username}** 的凭据似乎无效或已过期，请检查后重试。")

@bot.tree.command(name="admin_list", description="查看所有监控的创作者 (仅限管理员)")
async def admin_list(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_USER_ID:
        return await interaction.response.send_message("❌ 权限不足。", ephemeral=True)
        
    creators = bot.db.get_all_creators()
    if not creators:
        return await interaction.response.send_message("系统当前未监控任何创作者。")
        
    lines = ["📊 **全局监控列表:**"]
    for c in creators:
        sub_count = len(bot.db.get_subscribers(c['id']))
        lines.append(f"- **{c['username']}** @ {c['platform']} (订阅人数: {sub_count}, 最后检查: {c['last_check'] or '从未'})")
        
    await interaction.response.send_message("\n".join(lines))

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)
