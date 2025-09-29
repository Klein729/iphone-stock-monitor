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
    "???": "MYE93ZP/A"
}

    #"Cosmic Orange 256GB": "MFYN4X/A",
    #"Deep Blue 256GB": "MG8J4X/A",

STORES = ["R669"]
#STORES = ["R669","R633", "R641", "R625"]

#logging.basicConfig(level=logging.INFO)

def get_chrome_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
'''
def get_chrome_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 强制重新安装 ChromeDriver
    driver_path = ChromeDriverManager().install()
    #logging.debug(f"Using ChromeDriver: {driver_path}")
    
    driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
    return driver
'''
# 设置 Chrome 浏览器选项
'''
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
'''

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
    # 1. 先访问商品页面（建立 cookies、referer 等上下文）
    product_url = "https://www.apple.com/sg/shop/buy-iphone/iphone-17-pro"
    # logging.info(f"Visiting product page: {product_url}")
    driver.get(product_url)
    time.sleep(10)  # 等待页面 JS 加载并种下 Cookie
    print(f"first_loading_page_content : {driver.page_source}")
    
    url = f'https://www.apple.com/sg/shop/fulfillment-messages?pl=true&parts.0={model}&store={store}'
    print(f"URL : {url}")
    driver.get(url)
    
    time.sleep(2)  # 等待页面加载
    
    # 获取页面内容
    page_content = driver.page_source
    print(f"start_index : {page_content}")
    try:
        
        # 尝试解析 JSON 内容
        start_index = page_content.find('var fulfillmentMessages = ') + len('var fulfillmentMessages = ')
        print(f"start_index : {start_index}")
        end_index = page_content.find(';</script>', start_index)
        print(f"end_index : {end_index}")
        json_content = page_content[start_index:end_index]
        print(f"json_content : {json_content}")
        stock_data = json.loads(json_content)
        print(f"stock_data : {stock_data}")
        
        # 提取库存信息
        delivery_message = stock_data.get('deliveryMessage', None)
        print(f"delivery_message : {delivery_message}")
        pickup_message = stock_data.get('pickupMessage', None)
        print(f"pickup_message : {pickup_message}")
        
        if delivery_message:
            return f"Delivery: {delivery_message}"
        elif pickup_message:
            return f"Pickup: {pickup_message}"
        else:
            return "No stock information available"
    
    except Exception as e:
        print(f"Error parsing stock data for {model} at store {store}: {str(e)}")
        return None


'''
def check_inventory(model_id: str, store_id: str):
    driver = get_chrome_driver(headless=True)
    try:
        # 1. 先访问商品页面（建立 cookies、referer 等上下文）
        product_url = "https://www.apple.com/sg/shop/buy-iphone/iphone-17-pro"
        logging.info(f"Visiting product page: {product_url}")
        driver.get(product_url)
        time.sleep(3)  # 等待页面 JS 加载并种下 Cookie

        # 2. 再访问库存接口
        fulfillment_url = f"https://www.apple.com/sg/shop/fulfillment-messages?parts.0={model_id}&location={store_id}"
        logging.info(f"Visiting fulfillment URL: {fulfillment_url}")
        driver.get(fulfillment_url)
        time.sleep(2)

        # 3. 获取返回的 JSON（页面实际上就是个 JSON 字符串）
        pre_element = driver.find_element("tag name", "pre")  # JSON 在 <pre> 标签里
        json_text = pre_element.text
        logging.info(f"Fulfillment JSON for {model_id} at {store_id}:\n{json_text[:300]}...")

        # 4. 可在此处解析 json_text，提取库存状态
        # import json
        # data = json.loads(json_text)

    except Exception as e:
        logging.error(f"Error during inventory check: {e}")
    finally:
        driver.quit()
'''

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
