import os
import json
import time
import logging
import sys

# 【核心加固】终极隔离代理，彻底解决 502 Bad Gateway
# 禁止 Python 及其子进程（WebDriver）的所有本地通讯走代理
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

try:
    from seleniumbase import Driver
except ImportError:
    print("正在安装 SeleniumBase...")
    os.system(f"{sys.executable} -m pip install seleniumbase")
    from seleniumbase import Driver

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LZ-Refresh-Hardened")

AUTH_FILE = "data/lz_auth.json"
TARGET_URL = "https://leakedzone.com/videos"

def save_auth(cookie_dict, ua):
    """保存凭据"""
    os.makedirs("data", exist_ok=True)
    valid_cookies = {k: v for k, v in cookie_dict.items() if k and v}
    cookie_str = "; ".join([f"{k}={v}" for k, v in valid_cookies.items()])
    data = {
        "cookie": cookie_str,
        "ua": ua,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    logger.info(f"✅ 凭据同步成功！(字段数: {len(valid_cookies)})")

def refresh_cookie():
    """使用 SeleniumBase UC 模式 (强力隔离 + 自动过盾版)"""
    logger.info("🚀 启动强力隔离驱动 (UC Mode)...")
    
    from dotenv import load_dotenv
    load_dotenv(override=True)
    proxy_url = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

    driver = None
    try:
        # 使用 SeleniumBase 的底层 UC 配置，极大降低被拦截概率
        driver = Driver(uc=True, headless=False, proxy=proxy_url)
        
        # 针对五秒盾的进阶方法：打开网页并自动处理可能的重连
        logger.info(f"⏳ 正在尝试加载页面 (带自动挑战处理): {TARGET_URL}")
        driver.uc_open_with_reconnect(TARGET_URL, reconnect_time=10)
        
        # 针对有些环境依然会跳出 Checkbox 的情况：额外进行一次“无人值守”式查找与点击
        try:
            # 等待几秒观察是否出现了 CF 验证框
            time.sleep(5)
            # SeleniumBase 内置的 cf_click() 不够稳定，我们用通用的 iframe 穿透
            for frame in driver.find_elements("tag name", "iframe"):
                if "challenges" in frame.get_attribute("src"):
                    logger.info("🤖 发现 Cloudflare 验证框，尝试自动穿透点击...")
                    driver.switch_to.frame(frame)
                    # 点击复选框
                    checkbox = driver.find_element("css selector", "input[type='checkbox']")
                    if checkbox:
                        driver.execute_script("arguments[0].click();", checkbox)
                        logger.info("☝️ 已尝试模拟点击复选框。")
                    driver.switch_to.default_content()
                    time.sleep(5)
                    break
        except: pass

        success = False
        cookie_dict = {}
        
        for i in range(40):
            try:
                title = driver.title
                url = driver.current_url
                logger.info(f"[检查 {i+1}] Title: {title}")
                
                # 判定条件：业务主页
                if "Just a moment" not in title and ("videos" in url.lower() or "videos" in title.lower()):
                    # 再次核实内容
                    if driver.find_elements("css selector", ".movie-item"):
                        logger.info("✨ 成功进入主页！正在捕获状态...")
                        time.sleep(6) # 稳定落盘
                        
                        cookies = driver.get_cookies()
                        cookie_dict = {c['name']: c['value'] for c in cookies}
                        ua = driver.execute_script("return navigator.userAgent")
                        
                        if 'cf_clearance' in cookie_dict:
                            # 【GHA 核心加固】过盾后的实时校验
                            # 使用 curl_cffi 同步版进行冒烟测试，确保 Cookie 在非浏览器下也有效
                            from curl_cffi import requests as curl_requests
                            logger.info("🧪 正在进行过盾后的冒烟测试 (curl_requests)...")
                            try:
                                # 模拟 Linux/Windows 指纹
                                imp = "chrome120"
                                if "Linux" in ua: imp = "chrome110"
                                
                                test_res = curl_requests.get(
                                    TARGET_URL,
                                    cookies=cookie_dict,
                                    headers={"User-Agent": ua},
                                    impersonate=imp,
                                    timeout=10
                                )
                                if test_res.status_code == 200 and "Just a moment" not in test_res.text:
                                    logger.info("✅ 冒烟测试通过！凭据真实有效。")
                                    success = True
                                    break
                                else:
                                    logger.warning(f"❌ 冒烟测试未通过 (Status: {test_res.status_code})，继续等待反爬失效...")
                            except Exception as test_e:
                                logger.warning(f"⚠️ 冒烟测试异常: {test_e}")
                        else:
                            logger.warning("🔸 页面正常但尚未拿到 cf_clearance，等待下一次循环...")
                else:
                    if i == 5:
                        logger.warning("\n" + "!"*60 + "\n⚠️ 识别到五秒盾，请在弹出的窗口中手动勾选“复选框”！\n" + "!"*60 + "\n")
            except Exception as inner_e:
                logger.debug(f"检查循环中异常 (通常可忽略): {inner_e}")
            
            time.sleep(3)
            
        if success:
            save_auth(cookie_dict, ua)
            driver.quit()
            return True
            
    except Exception as e:
        logger.error(f"💥 驱动运行严重异常: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
    return False

def manual_input():
    print("\n" + "="*60)
    print("🛠️  手动助手 (备用)")
    print("-" * 60)
    print("请粘贴 cURL 并连续双击回车：")
    print("="*60)
    lines = []
    while True:
        try:
            line = input().strip()
            if not line: break
            lines.append(line)
        except: break
    import re
    input_data = " ".join(lines)
    cookie_str = ""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    res = re.findall(r"(?:-H|--header)\s*[\"\']cookie:\s*([^\"\']+)[\"\']", input_data, re.I)
    if res: cookie_str = res[0].strip()
    if not cookie_str: cookie_str = input_data.strip()
    if cookie_str:
        cd = {item.strip().split('=', 1)[0]: item.strip().split('=', 1)[1] for item in cookie_str.split(';') if '=' in item}
        save_auth(cd, ua)
        return True
    return False

if __name__ == "__main__":
    if "--manual" in sys.argv:
        manual_input()
    else:
        if not refresh_cookie():
            logger.warning("\n自动化暂时失效。请最后尝试【手动模式】：\n👉 python scripts/lz_refresh.py --manual")
