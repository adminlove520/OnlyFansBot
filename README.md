# 🔞 OnlyFans Bot

基于 Siren 架构复刻的 OnlyFans 监控与下载机器人。

## 📖 项目文档
- [🛠️ 配置指南](docs/config_guide.md): 如何获取 Token 并启动机器人。
- [📖 使用手册](docs/usage_manual.md): 指令说明与功能介绍。

## 主要功能
- **OnlyFans 官方同步**: 使用官方 API 抓取动态，支持动态签名算法绕过 401。
- **精准推送**: 发现新动态时，自动 @ 所有订阅了该创作者的 Discord 用户。
- **模块化架构**: 支持多平台扩展（已预留 Twitter 占位）。
- **智能媒体显示**: 自动检测视频大小，大文件推送封面预览，小文件直接推送。
- **指令系统**:
  - `/subscribe`: 订阅指定创作者。
  - `/unsubscribe`: 取消订阅。
  - `/list`: 管理我的订阅。
  - `!sync`: (管理) 同步斜杠指令。
  - `/admin_auth`: (管理) 动态配置爬虫 Cookie。
  - `/admin_list`: (管理) 监控全貌。

## 环境要求
- Python 3.10+
- Discord Bot Token
- Chrome/Safari 模拟 (curl-cffi)

## 快速开始

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境**:
   复制 `.env.example` 并重命名为 `.env`，填写你的 Token 和管理员 ID：
   ```env
   DISCORD_TOKEN=你的Token
   DISCORD_CHANNEL_ID=频道ID
   ADMIN_USER_ID=你的DiscordID
   ```

3. **运行机器人**:
   ```bash
   python bot.py
   ```

4. **快速获取 Cookie (Auth Helper)**:
   我们提供了一个自动化工具来帮助你提取 OnlyFans 的认证信息：
   ```bash
   # 安装 Playwright 浏览器内核
   python -m playwright install chromium
   # 运行辅助脚本
   python scripts/auth_helper.py
   ```
   脚本会打开浏览器，你只需登录 OF，脚本会自动在终端打印出可供机器人使用的 `/admin_auth` 命令。

5. **同步指令**:
   在 Discord 频道发送 `!sync` 刷出所有斜杠指令。

## 目录结构
- `bot.py`: 机器人入口及指令逻辑。
- `crawler.py`: 爬虫管理器逻辑。
- `database.py`: 数据库存储逻辑。
- `crawlers/`: 核心爬虫模块目录。
- `data/`: 持久化数据目录。
