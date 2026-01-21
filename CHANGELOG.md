# Changelog

All notable changes to this project will be documented in this file.

## [1.0.7] - 2026-01-21
### Added
- **LeakedZone 增强**: 引入基于 `SeleniumBase` (UC Mode) 的自动化 Cloudflare 过盾方案 (`scripts/lz_refresh.py`)。
- **环境自适应**: 爬虫支持 Linux (GHA) 与 Windows 指纹自动对齐，完美解决 GHA 环境下的 403 抓取难题。
- **情报启动卡片**: 脚本启动时发送专业概览卡片，展示版本号、监控状态。
- **豆瓣新片榜**: 集成 `api.baiwumm.com` 豆瓣新片接口，支持全量福利推送与转场仪式感卡片。
- **字段智能解析**: 自动识别创作者所属平台（Reddit/Fansly/Fansly等）并增加跳转链接。

### Changed
- **品牌重塑**: 项目由 `SecBridge` 正式更名为 **OnlyFans-Bot**。
- **架构优化**: 核心凭据存储统一至 `data/lz_auth.json`，实现“一处刷新，全局共用”。
- **卡片美化**: 重新设计 Discord Embed，优化了创作者、分类、豆瓣推荐的展示布局。

### Fixed
- 修复 `leakedzone_push.py` 中由于变量作用域导致的 `UnboundLocalError`。
- 解决 `api.baiwumm.com` 在本地全局代理环境下的 `ProxyError`（通过剥离 trust_env 实现）。
- 移除 `diagnose.py`、`geckodriver.exe` 等过期测试文件，精简代码库。

## [1.0.0] - 2026-01-14
### Added
- 初始化 OnlyFans 机器人独立项目。
- 引入 `OnlyFansCrawler` 支持动态签名算法和媒体抓取。
- 数据库适配：支持创作者、动态、订阅及认证管理。
- Discord 指令集：`/subscribe`, `/list`, `!sync`, `/admin_auth`, `/admin_list`。
- 自动化工作流：支持版本自动升级与 Docker 构建。
