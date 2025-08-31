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

        print("🔍 Checking for immediate sign-in requirement...")
        try:
            # Check if we need to click Sign In immediately after login
            sign_in = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign In')]"))
            )
            print("✅ Found immediate Sign In button, clicking...")
            sign_in.click()
            time.sleep(3)
        except Exception as e:
            print(f"⚠️  No immediate Sign In button found: {e}")

        print("📍 Handling location selection...")
        try:
            # Wait for location selection page
            location_text = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Tell us your work location') or contains(text(), 'work location')]"))
            )
            print("📍 Location selection page detected")
            
            # Find and click the dropdown
            dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "select, .select, [role='combobox'], input[placeholder*='Select']"))
            )
            
            if loc:
                print(f"📍 Selecting location: {loc}")
                # Try different methods to select location
                try:
                    Select(dropdown).select_by_visible_text(loc)
                except:
                    try:
                        Select(dropdown).select_by_value(loc)
                    except:
                        # If it's not a select element, try clicking and selecting
                        dropdown.click()
                        time.sleep(1)
                        location_option = driver.find_element(By.XPATH, f"//*[contains(text(), '{loc}')]")
                        location_option.click()
            else:
                print("📍 No specific location provided, selecting first available option")
                # Select first available option (usually "Office" or "Work from Home")
                select_obj = Select(dropdown)
                options = select_obj.options
                if len(options) > 1:  # Skip the default "Select" option
                    select_obj.select_by_index(1)
            
            time.sleep(2)
            
            # Click the Sign In button after location selection
            location_signin = find_button_by_text(driver, "Sign In")
            location_signin.click()
            time.sleep(3)
            print("✅ Location selected and signed in")
            
        except Exception as e:
            print(f"⚠️  Location selection step not found or failed: {e}")
            # This might be normal if location selection isn't required

        # Final verification
        time.sleep(5)
        current_url = driver.current_url
        page_source = driver.page_source.lower()
        print(f"🌐 Final URL: {current_url}")
        
        # Check for success indicators
        success_indicators = [
            "dashboard", "home", "employee", "profile", "attendance", "worklife"
        ]
        
        failure_indicators = [
            "login", "signin", "sign-in", "tell us your work location", "not signed in"
        ]
        
        if any(indicator in current_url.lower() for indicator in success_indicators):
            print("✅ Login successful - reached dashboard!")
        elif any(indicator in page_source for indicator in failure_indicators):
            print("❌ Login incomplete - still on login/location page")
            # Try to find what's still needed
            if "tell us your work location" in page_source:
                print("🔍 Location selection still required")
            elif "not signed in" in page_source:
                print("🔍 Sign-in step still pending")
        elif "good afternoon" in page_source or "good morning" in page_source or "good evening" in page_source:
            print("✅ Login successful - greeting detected!")
        else:
            print("✅ Automation completed - final status unclear")

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