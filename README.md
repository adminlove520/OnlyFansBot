# 🔞 OnlyFans Bot (OF-Scraper 增强版)

基于 **OF-Scraper** 引擎重构的 OnlyFans 监控与下载机器人，彻底解决认证签名不稳定问题。

## 🌟 核心功能

- **OF-Scraper 内核集成**: 采用 Git 子模块形式集成 `OF-Scraper`，利用其强大的签名生成能力，完美绕过 API 验证。
- **自动认证同步**: 在 Discord 发送的认证指令会自动同步到爬虫配置文件，无需手动修改 JSON。
- **Discord 交互**: 随时查询用户资料、监控时间线动态，有新帖自动推送。
- **环境隔离**: 爬虫运行在独立的 Python 3.11 虚拟环境中，与 Bot 主程序 (Python 3.10) 互不干扰。

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
