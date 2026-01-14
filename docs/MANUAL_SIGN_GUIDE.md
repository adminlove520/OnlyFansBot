# OnlyFans Bot - 手动签名模式使用指南

由于 OnlyFans 已将动态签名规则完全混淆进 JS 代码，Bot 无法自动生成有效的 `Sign` header。因此我们采用**手动签名代理模式**。

## 🚀 快速开始

### 步骤 1：从浏览器复制签名

1. 登录 OnlyFans（保持登录状态）
2. 按 **F12** 打开开发者工具
3. 切换到 **Network（网络）** 选项卡
4. 刷新页面（Ctrl+R）
5. 点击任意一个 `api2/v2/users/` 开头的请求
6. 在 **Headers（标头）** 里找到：
   - `sign: 53321:xxxx:xxx:696661b0`
   - `time: 1768380092919`
7. 复制这两个值

### 步骤 2：同步到 Bot

在 Discord 执行（记得点击斜杠指令弹出的菜单）：

```
/admin_auth 
  platform:onlyfans 
  username:@u543782498 
  sess:gbl84qfck8145r961edc88kuc5 
  auth_id:543782498 
  x_bc:29e9195c6bbfa598a131f9b7a6ebc98c00ed98b1 
  user_agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0
  manual_sign:53321:b2c655e595e6c7efbae00894bc2e182cc9f254d0:8f7:696661b0
  manual_time:1768380092919
```

**重要**: `manual_sign` 和 `manual_time` 必须配对使用（从同一个请求中复制）。

### 步骤 3：验证是否生效

执行 `/subscribe username:lenatheplug` 测试一下。

## ⏰ 签名有效期

OnlyFans 的签名大约 **1-2 小时**后会过期。如果 Bot 报错，重复步骤 1-2 即可。

## 💡 提示

- 你的浏览器必须保持登录状态
- 每次更新签名时，只需要复制新的 `manual_sign` 和 `manual_time`，其他参数可以不填
