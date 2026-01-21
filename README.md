# 🔞 OnlyFans-Bot (智能情报先锋)

基于 **OF-Scraper** 核心，专为 OnlyFans、LeakedZone 等平台定制的智能监控与情报推送系统。

## 🌟 核心功能

- **🚀 跨平台情报站**: 完美集成 **LeakedZone** 动态抓取，支持自动识别创作者所属平台（Reddit/Fansly/Twitter 等）并分类推送。
- **🛡️ 强力 Cloudflare 绕过**: 采用 `SeleniumBase` (UC Mode) + `curl_cffi` 指纹模拟技术。支持 Windows/Linux (GHA) 自适应过盾，解决五秒盾截流。
- **🍿 豆瓣福利速递**: 任务结束后自动全量推送豆瓣最新电影榜单，情报福利两不误。
- **OF-Scraper 内核集成**: 本地化集成 `OF-Scraper` 引擎，利用其强大的签名生成能力，完美下载媒体资产。
- **Discord 深度交互**: 全流程 Embed 卡片展示。支持自动同步认证、查询资料、监控时间线及新帖实时触达。
- **自动化运维**: 完美适配 GitHub Actions，全流程自动化“刷新-抓取-推送-存储”，无需人工干预。

## 🚀 安装与配置

### 环境要求
- Python 3.10+ (用于运行 Bot 主程序)
- Python 3.11+ (用于运行 Adapter 适配器)

### 目录结构
```
OnlyFans-Bot/          # Git 仓库根目录
├── bot.py             # 机器人启动入口
├── crawlers/          # 爬虫逻辑封装
├── OF-Scraper/        # 核心引擎 (Git 子模块)
├── scripts/           # 适配器脚本目录
└── docs/              # 说明文档
```

### 快速开始

1. **克隆仓库 (含子模块)**:
   ```bash
   git clone --recursive <你的仓库地址>
   # 如果已经克隆了但没有子模块:
   git submodule update --init --recursive
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
   *注意: 请确保 `OF-Scraper/` 目录下的 venv 虚拟环境也已正确配置（参考 submodule 说明）。*

3. **启动机器人**:
   ```bash
   python bot.py
   ```

## 🛠️ 常用指令


### 1. 普通用户指令 (Slash Commands)
- `/subscribe [username] [platform]`: 订阅一位创作者（默认 OnlyFans）。如果有新动态，机器人会艾特你。
- `/unsubscribe [username] [platform]`: 取消订阅，不再接收该创作者的推送。
- `/list`: 查看你目前正在监控的所有创作者列表。

### 2. 管理员指令 (Prefix & Slash Commands)
- `!sync` (前缀指令): 将所有新的斜杠指令同步到当前 Discord 服务器。
- `/admin_auth`: 配置爬虫账号的 SESS, Auth_ID 等认证信息。支持动态更新。
- `/admin_list`: 查看全站监控状态，包括每个创作者的订阅人数。


- **/auth [sess] [user_id] ...**: (管理员) 配置 OnlyFans 账号凭据。
- **!profile [username]**: 手动查询某位博主的资料。
- **!timeline [username]**: 手动抓取某位博主的时间线。
- **!subscribe [username]**: 订阅博主，开启自动监控。

## 📄 更多文档

详细配置指南和更新日志请查看 `docs/` 文件夹。
