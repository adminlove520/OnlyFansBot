import asyncio
import json
import re
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("="*50)
        print("🚀 OnlyFans Auth Helper 已启动")
        print("请在打开的浏览器窗口中登录 OnlyFans 并正常浏览。")
        print("一旦截获到关键认证信息，脚本会自动提取并显示。")
        print("="*50)

        found_auth = {
            "sess": None,
            "auth_id": None,
            "x_bc": None,
            "user_agent": None
        }

        async def handle_request(request):
            if "api2/v2" in request.url and found_auth["sess"] is None:
                headers = request.headers
                cookies = await context.cookies()
                
                # Extract SESS from cookies
                sess = next((c['value'] for c in cookies if c['name'] == 'sess'), None)
                x_bc = headers.get("x-bc")
                ua = headers.get("user-agent")
                
                # auth_id is usually found in the headers or url
                # Sometimes it's the 'user-id' header if present
                auth_id = headers.get("user-id")
                
                if sess and x_bc:
                    found_auth["sess"] = sess
                    found_auth["x_bc"] = x_bc
                    found_auth["user_agent"] = ua
                    found_auth["auth_id"] = auth_id or "0" # Default 0 if not found immediately
                    
                    print("\n✅ 成功截获认证信息！")
                    print("-" * 30)
                    print(f"SESS: {found_auth['sess']}")
                    print(f"Auth ID: {found_auth['auth_id']}")
                    print(f"X-BC: {found_auth['x_bc']}")
                    print(f"User-Agent: {found_auth['user_agent']}")
                    print("-" * 30)
                    print("\n可以直接在 Discord 中使用以下命令配置:")
                    cmd = f"/admin_auth platform:onlyfans username:your_name sess:{found_auth['sess']} auth_id:{found_auth['auth_id']} x_bc:{found_auth['x_bc']} user_agent:{found_auth['user_agent']}"
                    print(cmd)
                    print("-" * 30)
                    print("抓取完成后，你可以关闭浏览器或按 Ctrl+C 退出脚本。")

        page.on("request", handle_request)

        await page.goto("https://onlyfans.com/")
        
        # Keep the script running until manually interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 正在退出...")
        finally:
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
