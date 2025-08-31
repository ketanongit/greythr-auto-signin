import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_driver():
    chrome_path = "/usr/bin/google-chrome-stable"
    driver_path = "/usr/bin/chromedriver"
    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(30)
    return driver

def main():
    url = os.environ['LOGIN_URL']
    user = os.environ['LOGIN_ID']
    pwd  = os.environ['LOGIN_PASSWORD']
    loc  = os.environ.get('SIGNIN_LOCATION', '')

    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(2)

        # Login ID
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Employee']"))
        )
        username.clear()
        username.send_keys(user)

        # Password
        password = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password.clear()
        password.send_keys(pwd)

        # Click Login
        login_btn = driver.find_element(By.CSS_SELECTOR, "button:has-text('Login')")
        login_btn.click()
        time.sleep(5)

        # Click Sign In
        sign_in = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button:has-text('Sign In')"))
        )
        sign_in.click()
        time.sleep(3)

        # Select location
        if loc:
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select"))
            )
            Select(dropdown).select_by_visible_text(loc)
            time.sleep(1)
            confirm = driver.find_element(By.CSS_SELECTOR, "button:has-text('Sign In')")
            confirm.click()
            time.sleep(2)

        print("✅ Automation completed successfully!")

    except Exception as e:
        print(f"❌ Automation failed: {e}")
        raise

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
