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

def discover_page_elements(driver):
    """Discover all clickable elements on the page"""
    print("\n🔍 DISCOVERING ALL CLICKABLE ELEMENTS...")
    
    # Find all buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"Found {len(buttons)} button elements:")
    for i, btn in enumerate(buttons):
        try:
            text = btn.text.strip()
            classes = btn.get_attribute('class') or ''
            is_clickable = btn.is_enabled() and btn.is_displayed()
            if text or is_clickable:
                print(f"  Button {i}: '{text}' | classes: '{classes}' | clickable: {is_clickable}")
        except:
            pass
    
    # Find all links that might be styled as buttons
    links = driver.find_elements(By.TAG_NAME, "a")
    clickable_links = []
    for link in links:
        try:
            text = link.text.strip()
            classes = link.get_attribute('class') or ''
            if ('btn' in classes.lower() or 'button' in classes.lower()) and link.is_displayed():
                clickable_links.append(link)
                print(f"  Link-button: '{text}' | classes: '{classes}'")
        except:
            pass
    
    # Find all input buttons
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='button'], input[type='submit']")
    print(f"Found {len(inputs)} input buttons:")
    for i, inp in enumerate(inputs):
        try:
            value = inp.get_attribute('value') or ''
            classes = inp.get_attribute('class') or ''
            is_clickable = inp.is_enabled() and inp.is_displayed()
            if is_clickable:
                print(f"  Input {i}: '{value}' | classes: '{classes}' | clickable: {is_clickable}")
        except:
            pass
    
    # Look for elements with specific attendance-related text
    attendance_keywords = ['sign in', 'check in', 'punch in', 'attendance', 'clock in', 'mark attendance']
    print(f"\n🎯 SEARCHING FOR ATTENDANCE-RELATED ELEMENTS...")
    for keyword in attendance_keywords:
        elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
        if elements:
            print(f"  Found {len(elements)} elements containing '{keyword}':")
            for elem in elements:
                try:
                    tag = elem.tag_name
                    text = elem.text.strip()
                    classes = elem.get_attribute('class') or ''
                    clickable = elem.is_enabled() and elem.is_displayed()
                    print(f"    {tag}: '{text}' | clickable: {clickable} | classes: '{classes}'")
                except:
                    pass

def smart_signin_attempt(driver):
    """Try intelligent sign-in based on discovered elements"""
    print("\n🤖 ATTEMPTING SMART SIGN-IN...")
    
    # Strategy 1: Look for buttons with sign-in related text
    signin_patterns = [
        "sign in", "sign-in", "signin", "check in", "punch in", "clock in", "mark attendance"
    ]
    
    for pattern in signin_patterns:
        try:
            # Case-insensitive search for buttons
            elements = driver.find_elements(By.XPATH, 
                f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]"
            )
            
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    print(f"🎯 Found and clicking: '{elem.text}' (pattern: {pattern})")
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    time.sleep(1)
                    elem.click()
                    time.sleep(3)
                    return True
        except Exception as e:
            print(f"Pattern '{pattern}' failed: {e}")
            continue
    
    # Strategy 2: Click any blue/primary buttons (common for sign-in)
    try:
        blue_buttons = driver.find_elements(By.XPATH, 
            "//button[contains(@class, 'blue') or contains(@class, 'primary') or contains(@class, 'btn-primary')]"
        )
        for btn in blue_buttons:
            if btn.is_displayed() and btn.is_enabled():
                print(f"🔵 Trying blue/primary button: '{btn.text}'")
                btn.click()
                time.sleep(3)
                return True
    except:
        pass
    
    return False

def main():
    url   = os.environ['LOGIN_URL']
    user  = os.environ['LOGIN_ID']
    pwd   = os.environ['LOGIN_PASSWORD']
    loc   = os.environ.get('SIGNIN_LOCATION', '')
    debug = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    manual_run = os.environ.get('MANUAL_RUN', 'false').lower() == 'true'

    # Time info for debugging
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ist_hour = (now.hour + 5) % 24 + (30 // 60)  # Convert to IST approximately
    is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    if debug or manual_run:
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
        
        if debug or manual_run:
            discover_page_elements(driver)
        
        # Try smart sign-in
        signin_success = smart_signin_attempt(driver)
        
        if signin_success:
            print("✅ Smart sign-in attempt completed")
            
            # Handle location selection if it appears
            try:
                time.sleep(2)
                location_dropdown = driver.find_element(By.CSS_SELECTOR, "select")
                if location_dropdown.is_displayed():
                    print("📍 Location selection found")
                    if loc:
                        Select(location_dropdown).select_by_visible_text(loc)
                        print(f"Selected location: {loc}")
                    else:
                        Select(location_dropdown).select_by_index(1)
                        print("Selected first available location")
                    
                    # Final confirm button
                    time.sleep(1)
                    confirm_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign In') or contains(text(), 'Confirm')]")
                    for btn in confirm_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            print("✅ Final confirmation clicked")
                            break
            except:
                print("📍 No location selection required")
        
        # Final verification with detailed analysis
        time.sleep(5)
        current_url = driver.current_url
        page_source = driver.page_source
        print(f"🌐 Final URL: {current_url}")
        
        # Check page content for clues
        page_lower = page_source.lower()
        
        # Success indicators
        success_phrases = [
            "good afternoon", "good morning", "good evening", "welcome",
            "signed in", "attendance marked", "check-in successful", "punch in successful"
        ]
        
        # Still need action indicators  
        action_needed = [
            "sign in", "check in", "punch in", "mark attendance", "clock in",
            "tell us your work location", "select location"
        ]
        
        found_success = any(phrase in page_lower for phrase in success_phrases)
        found_action = any(phrase in page_lower for phrase in action_needed)
        
        if found_success and not found_action:
            print("✅ ATTENDANCE SIGN-IN SUCCESSFUL!")
        elif found_action:
            print("❌ Attendance sign-in still required - automation incomplete")
            if debug or manual_run:
                for phrase in action_needed:
                    if phrase in page_lower:
                        print(f"   Still needs: {phrase}")
        else:
            print("✅ Automation completed - status unclear but no action prompts detected")
        
        # Enhanced debug output
        if debug or manual_run:
            print(f"\n📄 Page title: {driver.title}")
            
            # Save debug files with better encoding
            try:
                with open("/tmp/final_page_source.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
                driver.save_screenshot("/tmp/final_screenshot.png")
                print("💾 Debug files saved successfully")
            except Exception as save_error:
                print(f"⚠️ Could not save debug files: {save_error}")

    except Exception as e:
        print(f"❌ Automation failed: {e}")
        
        # Always try to save error info
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