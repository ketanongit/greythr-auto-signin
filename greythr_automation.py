import os, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_driver():
    chrome_path = "/usr/bin/chromium-browser"
    driver_path = "/usr/bin/chromedriver"
    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(30)
    return driver

def find_button_by_text(driver, text, timeout=10):
    """Find button by text content using XPath"""
    xpath_patterns = [
        f"//button[contains(text(), '{text}')]",
        f"//button[contains(., '{text}')]",
        f"//input[@type='submit' and contains(@value, '{text}')]",
        f"//input[@type='button' and contains(@value, '{text}')]",
        f"//*[@role='button' and contains(text(), '{text}')]",
        f"//a[contains(@class, 'btn') and contains(text(), '{text}')]"
    ]
    
    for pattern in xpath_patterns:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, pattern))
            )
            return element
        except:
            continue
    
    raise Exception(f"Could not find clickable button with text '{text}'")

def main():
    url   = os.environ['LOGIN_URL']
    user  = os.environ['LOGIN_ID']
    pwd   = os.environ['LOGIN_PASSWORD']
    loc   = os.environ.get('SIGNIN_LOCATION', '')

    driver = setup_driver()
    try:
        print("🚀 Starting GreytHR automation...")
        driver.get(url)
        time.sleep(3)

        print("📝 Filling username...")
        username = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Employee'], input[name*='username'], input[name*='email'], input[id*='username']"))
        )
        username.clear()
        username.send_keys(user)

        print("🔒 Filling password...")
        password = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password.clear()
        password.send_keys(pwd)

        print("🔑 Clicking login button...")
        login_btn = find_button_by_text(driver, "Login")
        login_btn.click()
        time.sleep(5)

        print("✅ Attempting to sign in...")
        try:
            sign_in = find_button_by_text(driver, "Sign In")
            sign_in.click()
            time.sleep(3)
        except Exception as e:
            print(f"⚠️  Sign In button not found or not needed: {e}")

        if loc:
            print(f"📍 Selecting location: {loc}")
            try:
                dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "select"))
                )
                Select(dropdown).select_by_visible_text(loc)
                time.sleep(1)
                
                confirm = find_button_by_text(driver, "Sign In")
                confirm.click()
                time.sleep(2)
            except Exception as e:
                print(f"⚠️  Location selection failed: {e}")

        # Verify successful login
        time.sleep(3)
        current_url = driver.current_url
        print(f"🌐 Current URL: {current_url}")
        
        # Check for common success indicators
        success_indicators = [
            "dashboard", "home", "employee", "profile", "attendance"
        ]
        
        if any(indicator in current_url.lower() for indicator in success_indicators):
            print("✅ Login appears successful!")
        else:
            # Check if we're still on login page
            if "login" in current_url.lower() or "signin" in current_url.lower():
                print("❌ Still on login page - login may have failed")
            else:
                print("✅ Automation completed successfully!")

    except Exception as e:
        print(f"❌ Automation failed: {e}")
        
        # Take screenshot for debugging (if not headless)
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            print("📸 Screenshot saved for debugging")
        except:
            pass
            
        raise

    finally:
        driver.quit()

if __name__ == "__main__":
    main()