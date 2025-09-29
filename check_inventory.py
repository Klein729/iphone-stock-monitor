import time
import json
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 配置 Telegram bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'


# 配置 iPhone 型号与门店信息
IPHONE_MODELS = {
    "Cosmic Orange 256GB": "MFYN4X/A",
    "Deep Blue 256GB": "MG8J4X/A",
    "???": "MYE93ZP/A"
}

STORES = ["R669","R633", "R641", "R625"]

# 设置 Chrome 浏览器选项
def get_chrome_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


# 发送 Telegram 消息
def send_telegram_message(message):
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    response = requests.post(TELEGRAM_API_URL, data=payload)
    return response.status_code


# 获取库存信息
def get_stock_info(driver, model, store):
    url = f'https://www.apple.com/sg/shop/fulfillment-messages?pl=true&parts.0={model}&store={store}'
    driver.get(url)
    
    time.sleep(2)  # 等待页面加载
    
    # 获取页面内容
    page_content = driver.page_source
    try:
        # 尝试解析 JSON 内容
        start_index = page_content.find('var fulfillmentMessages = ') + len('var fulfillmentMessages = ')
        end_index = page_content.find(';</script>', start_index)
        json_content = page_content[start_index:end_index]
        stock_data = json.loads(json_content)
        
        # 提取库存信息
        delivery_message = stock_data.get('deliveryMessage', None)
        pickup_message = stock_data.get('pickupMessage', None)
        
        if delivery_message:
            return f"Delivery: {delivery_message}"
        elif pickup_message:
            return f"Pickup: {pickup_message}"
        else:
            return "No stock information available"
    
    except Exception as e:
        print(f"Error parsing stock data for {model} at store {store}: {str(e)}")
        return None


# 检查库存并发送通知
def check_inventory():
    driver = get_chrome_driver(headless=True)
    
    for model_name, model_id in IPHONE_MODELS.items():
        for store in STORES:
            print(f"Checking stock for {model_name} at store {store}...")
            stock_info = get_stock_info(driver, model_id, store)
            
            if stock_info:
                print(f"Stock info for {model_name} at store {store}: {stock_info}")
                message = f"{model_name} at store {store} - {stock_info}\nURL: https://www.apple.com/sg/shop/fulfillment-messages?pl=true&parts.0={model_id}&store={store}"
                send_telegram_message(message)
            else:
                print(f"No stock information for {model_name} at store {store}.")
            
            time.sleep(1.5)  # 控制请求频率
    
    driver.quit()


if __name__ == "__main__":
    check_inventory()
