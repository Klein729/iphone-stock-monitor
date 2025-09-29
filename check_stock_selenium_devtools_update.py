import os
import time
import json
import logging
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from telegram import Bot  # 假设你用 python-telegram-bot 或类似库

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg: str):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)


def make_driver(headless=True):
    """
    使用 Selenium 4+ 的 Chrome + DevTools 接口来捕获网络日志
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")  # Selenium 4.11+ 推荐 new headless 模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
    # 防止被检测
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # 启用 performance 日志（network 等信息）
    caps = webdriver.DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"performance": "ALL"}
    # 也可以设置 perfLoggingPrefs 进一步过滤
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    # 启动 driver
    service = Service()  # 你可以传入 chromedriver 路径或环境变量自动寻找
    driver = webdriver.Chrome(service=service, options=chrome_options, desired_capabilities=caps)

    # 可选：利用 CDP 接口启用 network 域（部分场景需要主动启用）
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception as e:
        logger.warning("execute_cdp_cmd Network.enable failed: %s", e)

    return driver


def get_network_responses(driver, url_filter: str = None):
    """
    从 driver 的 performance 日志中抓取 response body
    如果提供 url_filter，则只返回 URL 中包含该过滤字符串的响应
    返回 dict: url -> {"requestId": .., "status": .., "body": str或bytes 或 JSON 解码后的对象}
    """
    results = {}
    logs = driver.get_log("performance")
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
        except Exception:
            continue

        method = msg.get("method")
        params = msg.get("params", {})

        # 我们关心 Network.responseReceived 事件
        if method == "Network.responseReceived":
            response = params.get("response", {})
            request_id = params.get("requestId")
            url = response.get("url")
            status = response.get("status")

            if url_filter and url_filter not in url:
                continue

            # 使用 CDP cmd 获取 response body
            try:
                resp_body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            except WebDriverException as e:
                logger.debug("getResponseBody failed for %s: %s", url, e)
                continue

            # resp_body 典型结构是 {"body": "...", "base64Encoded": bool}
            body = resp_body.get("body")
            if resp_body.get("base64Encoded"):
                # decode base64 如果有必要
                import base64
                body = base64.b64decode(body)
            # 这里也可以尝试 json.loads(body) 如果是 JSON
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body

            results[url] = {
                "requestId": request_id,
                "status": status,
                "body": parsed,
            }
    return results


def check_stock():
    """
    核心逻辑：打开页面 / 发起请求 / 从 network 响应中解析 / 通知
    """
    driver = make_driver(headless=True)
    try:
        target_page = "https://www.apple.com/retail/availability/"  # 举例
        driver.get(target_page)
        # 根据你实际页面可能还要点击、滚动、等待等
        time.sleep(5)  # 等待网络请求完成

        # 取所有 network 响应（或过滤特定 endpoint）
        responses = get_network_responses(driver, url_filter="fulfillment-messages")
        logger.info("Found %d matching responses", len(responses))

        for url, info in responses.items():
            status = info["status"]
            body = info["body"]
            logger.info("URL %s status %s body %s", url, status, str(body)[:200])

            # 依据 body 判断是否有库存
            # 这是你原脚本的逻辑：假设 body 是 JSON，包含某个字段表示有库存
            try:
                # 假设 JSON 结构示例
                if isinstance(body, dict) and body.get("someInventoryField", 0) > 0:
                    send_telegram(f"Stock found! URL: {url}, body: {body}")
            except Exception as e:
                logger.error("Parsing stock logic error: %s\n%s", e, traceback.format_exc())

    except Exception as e:
        logger.error("check_stock error: %s\n%s", e, traceback.format_exc())
        send_telegram(f"Exception in check_stock: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    check_stock()

