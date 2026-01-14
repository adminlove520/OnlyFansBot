# 🛠️ OnlyFans Bot 配置指南

本指南将协助你从零开始配置并运行 OnlyFans 监控机器人。

## 1. 获取 Discord Bot Token

1.  访问 [Discord Developer Portal](https://discord.com/developers/applications)。
2.  点击 **"New Application"**，输入名称（如 OnlyFans Bot）。
3.  在左侧菜单点击 **"Bot"**。
4.  点击 **"Reset Token"** 并复制生成的 Token。
5.  **重要**: 在下方 **"Privileged Gateway Intents"** 中开启：
    - `PRESENCE INTENT`
    - `SERVER MEMBERS INTENT`
    - `MESSAGE CONTENT INTENT` (必须开启，否则无法响应 `!sync` 命令)

## 2. 邀请机器人到服务器

1.  在左侧菜单点击 **"OAuth2"** -> **"URL Generator"**。
2.  在 **Scopes** 中勾选 `bot` 和 `applications.commands`。
3.  在 **Bot Permissions** 中勾选：
    - `Administrator` (省事之选) 或
    - `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`。

## 3. 获取管理 ID 与频道 ID

1.  在 Discord 客户端中，打开 **"设置" (Settings)** -> **"高级" (Advanced)**。
2.  开启 **"开发者模式" (Developer Mode)**。
3.  **管理 ID**: 右键点击你自己的头像，选择 **"复制 ID"**。这将作为 `ADMIN_USER_ID`。
4.  **通知频道 ID**: 右键点击你想接收通知的频道，选择 **"复制 ID"**。这将作为 `DISCORD_CHANNEL_ID`。

## 4. 填写配置文件

在 `OnlyFans-Bot` 根目录下创建 `.env` 文件：

```env
DISCORD_TOKEN=你的机器人Token
DISCORD_CHANNEL_ID=你的频道ID
ADMIN_USER_ID=你的DiscordID
CHECK_INTERVAL=15
```

## 5. 核心：配置 OnlyFans 认证

由于 OnlyFans 的认证信息（Cookie 等）既复杂又会过期，我们不建议将其硬编码在 `.env` 或环境变量中。机器人支持通过 Discord 指令**动态配置**。

### 第一步：使用辅助脚本提取信息
在本地（你的电脑上）运行我们提供的工具：
```bash
python scripts/auth_helper.py
```
1.  脚本会打开浏览器，请登录你的 OnlyFans 账号。
2.  登录后，脚本会在终端（命令行）自动打印出一组参数。
3.  **注意 Username**: 脚本中 `username` 只是一个别名，建议使用你自己的 OF 用户名（如你截图中的 `u543782498`，去掉了 `@` 符号）。

### 第二步：在 Discord 中激活
将脚本生成的指令直接粘贴到 Discord 频道并发送：

> [!TIP]
> **示例指令格式：**
> `/admin_auth platform:onlyfans username:u543782498 sess:xxx auth_id:0 x_bc:xxx user_agent:xxx`

发送成功后，机器人会即刻生效，无需重启！

---

## 6. 部署说明 (Zeabur)

1.  **环境变量**: 在 Zeabur 中设置 `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID`, `ADMIN_USER_ID`。
2.  **持久化存储 (必读)**:
    - OnlyFans-Bot 使用 SQLite 存储你的订阅和 Cookie。
    - 在 Zeabur 的 **Storage** 选项卡，点击 **Add Volume**。
    - **Mount Path** 必须填写 `/app/data`。
    - 如果不挂载 Volume，每次容器重启，你之前在 Discord 里用 `/admin_auth` 配置的所有信息都会消失。
