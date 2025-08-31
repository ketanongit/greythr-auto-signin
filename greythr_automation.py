import os, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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

def handle_location_modal(driver, location):
    """Handle the location selection modal if it appears"""
    print("🗺️ Checking for location modal...")
    
    try:
        # Look for the modal with "Tell us your work location" text
        modal_text = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Tell us your work location')]"))
        )
        print("📍 Location modal detected!")
        
        # Try to find and fill the location field
        try:
            # Look for textarea or input field in the modal
            textarea = driver.find_element(By.CSS_SELECTOR, "gt-text-area textarea, textarea")
            textarea.clear()
            textarea.send_keys(location if location else "Office")
            print(f"📝 Entered location: {location if location else 'Office'}")
        except:
            print("⚠️ Could not find location input field")
        
        # Look for submit/confirm button in the modal
        try:
            # Try multiple selectors for the submit button
            submit_selectors = [
                "gt-button[shade='primary']",
                "button:contains('Submit')",
                "button:contains('Confirm')",
                "button:contains('Sign In')",
                ".hydrated[shade='primary']"
            ]
            
            for selector in submit_selectors:
                try:
                    if ':contains' in selector:
                        # Use XPath for text-based selection
                        xpath = f"//button[contains(text(), '{selector.split('contains')[1][2:-2]}')]"
                        btn = driver.find_element(By.XPATH, xpath)
                    else:
                        btn = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"✅ Clicked modal submit button")
                        time.sleep(3)
                        return True
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Could not find modal submit button: {e}")
            
    except TimeoutException:
        print("ℹ️ No location modal detected")
    except Exception as e:
        print(f"⚠️ Error handling location modal: {e}")
    
    return False

def find_and_click_signin(driver):
    """Find and click the sign-in button on the home page"""
    print("\n🔍 Looking for sign-in button on home page...")
    
    # Strategy 1: Look for the attendance widget button
    try:
        # The attendance widget shows a button with primary shade
        attendance_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "gt-attendance-info gt-button[shade='primary']"))
        )
        print("✅ Found attendance widget button!")
        driver.execute_script("arguments[0].scrollIntoView(true);", attendance_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", attendance_button)
        print("🎯 Clicked attendance sign-in button!")
        return True
    except Exception as e:
        print(f"⚠️ Could not find attendance widget button: {e}")
    
    # Strategy 2: Click on any button with sign-in related text
    signin_keywords = ["sign in", "check in", "punch in", "clock in", "mark attendance"]
    for keyword in signin_keywords:
        try:
            xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"
            buttons = driver.find_elements(By.XPATH, xpath)
            for btn in buttons:
                if btn.is_displayed() and btn.is_enabled():
                    print(f"✅ Found button with text: {btn.text}")
                    driver.execute_script("arguments[0].click();", btn)
                    return True
        except:
            continue
    
    # Strategy 3: Look for gt-button elements (custom components)
    try:
        gt_buttons = driver.find_elements(By.CSS_SELECTOR, "gt-button")
        for btn in gt_buttons:
            btn_text = btn.get_attribute('innerText') or btn.get_attribute('name') or ''
            if any(keyword in btn_text.lower() for keyword in ['sign', 'check', 'punch', 'clock', 'attendance']):
                print(f"✅ Found gt-button: {btn_text}")
                driver.execute_script("arguments[0].click();", btn)
                return True
    except:
        pass
    
    return False

def main():
    url   = os.environ['LOGIN_URL']
    user  = os.environ['LOGIN_ID']
    pwd   = os.environ['LOGIN_PASSWORD']
    loc   = os.environ.get('SIGNIN_LOCATION', 'Office')
    debug = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    manual_run = os.environ.get('MANUAL_RUN', 'false').lower() == 'true'

    # Time info for debugging
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ist_hour = (now.hour + 5) % 24 + (30 // 60)
    is_weekend = now.weekday() >= 5
    
    print(f"🕐 Current time: {now.strftime('%A %H:%M UTC')} (IST: ~{ist_hour:02d}:xx)")
    print(f"📅 Is weekend: {is_weekend}")
    print(f"🔧 Manual run: {manual_run}")
    print(f"🐛 Debug mode: {debug}")
    
    if manual_run:
        print("🧪 Manual testing mode - will attempt sign-in regardless of time/status")

    driver = setup_driver()
    try:
        print("🚀 Starting GreytHR automation...")
        driver.get(url)
        time.sleep(3)

        # Login process
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
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'LOGIN') or contains(@value, 'Login')]")
        login_btn.click()
        time.sleep(5)

        print("⏳ Waiting for dashboard to load...")
        WebDriverWait(driver, 15).until(
            lambda d: "login" not in d.current_url.lower() or "dashboard" in d.current_url.lower() or "home" in d.current_url.lower()
        )
        
        print("✅ Successfully logged in!")
        time.sleep(3)
        
        # Handle location modal if it appears
        modal_handled = handle_location_modal(driver, loc)
        
        if modal_handled:
            print("📍 Location modal handled, waiting for page update...")
            time.sleep(5)
        
        # Try to find and click sign-in button
        signin_clicked = find_and_click_signin(driver)
        
        if signin_clicked:
            print("⏳ Waiting for sign-in to process...")
            time.sleep(5)
            
            # Handle location modal again if it appears after clicking sign-in
            handle_location_modal(driver, loc)
            time.sleep(3)
        
        # Final verification
        current_url = driver.current_url
        page_source = driver.page_source.lower()
        
        print(f"🌐 Final URL: {current_url}")
        
        # Check for success indicators
        if "signed in" in page_source or "attendance marked" in page_source:
            print("✅ ATTENDANCE SIGN-IN SUCCESSFUL!")
        elif "tell us your work location" in page_source:
            print("⚠️ Location selection still pending")
        elif "sign in" in page_source or "check in" in page_source:
            print("⚠️ Sign-in button still visible - may need manual intervention")
        else:
            print("✅ Process completed - please verify status")
        
        # Save debug files if in debug mode
        if debug or manual_run:
            print(f"\n📄 Page title: {driver.title}")
            try:
                with open("/tmp/final_page_source.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
                driver.save_screenshot("/tmp/final_screenshot.png")
                print("💾 Debug files saved successfully")
            except Exception as save_error:
                print(f"⚠️ Could not save debug files: {save_error}")

    except Exception as e:
        print(f"❌ Automation failed: {e}")
        
        # Save error debugging files
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            with open("/tmp/error_page_source.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            print("📸 Error debugging files saved")
        except:
            pass
            
        raise

    finally:
        driver.quit()

if __name__ == "__main__":
    main()