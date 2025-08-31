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
        
        # Handle the custom gt-dropdown
        try:
            # First, try to find the gt-dropdown element
            gt_dropdown = driver.find_element(By.CSS_SELECTOR, "gt-dropdown")
            print("📋 Found gt-dropdown element")
            
            # Click on the dropdown button to open it
            dropdown_button = gt_dropdown.find_element(By.CSS_SELECTOR, "button.dropdown-button")
            print("🖱️ Found dropdown button, clicking to open...")
            driver.execute_script("arguments[0].click();", dropdown_button)
            time.sleep(2)  # Wait for dropdown to open
            
            # Now look for the dropdown items container
            dropdown_container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "gt-dropdown .dropdown-container"))
            )
            print("📂 Dropdown container is now visible")
            
            # Find all dropdown items
            dropdown_items = dropdown_container.find_elements(By.CSS_SELECTOR, ".dropdown-item")
            print(f"📝 Found {len(dropdown_items)} dropdown options")
            
            # Look for the "Office" option
            office_clicked = False
            for item in dropdown_items:
                item_text = item.get_attribute('innerText') or item.text or ''
                item_label = item.find_elements(By.CSS_SELECTOR, ".item-label")
                if item_label:
                    item_text = item_label[0].text
                
                print(f"📋 Checking item: '{item_text}'")
                
                if 'office' in item_text.lower():
                    print(f"✅ Found Office option: '{item_text}', clicking...")
                    driver.execute_script("arguments[0].click();", item)
                    office_clicked = True
                    time.sleep(2)
                    break
            
            if not office_clicked:
                print("⚠️ Could not find 'Office' option, trying second available option...")
                if dropdown_items:
                    second_item = dropdown_items[1]
                    second_text = second_item.get_attribute('innerText') or second_item.text or 'second Option'
                    print(f"📋 Clicking second option: '{second_text}'")
                    driver.execute_script("arguments[0].click();", second_item)
                    time.sleep(2)
                
        except Exception as dropdown_error:
            print(f"⚠️ Error handling gt-dropdown: {dropdown_error}")
            
            # Fallback: Try to interact with the dropdown using JavaScript
            try:
                print("🔄 Trying JavaScript fallback for dropdown...")
                driver.execute_script("""
                    // Find the gt-dropdown element
                    var dropdown = document.querySelector('gt-dropdown');
                    if (dropdown) {
                        // Try to open it
                        var button = dropdown.querySelector('button');
                        if (button) {
                            button.click();
                            
                            // Wait a bit for options to appear
                            setTimeout(function() {
                                // Look for Office option
                                var items = dropdown.querySelectorAll('.dropdown-item');
                                for (var i = 0; i < items.length; i++) {
                                    var text = items[i].textContent || items[i].innerText;
                                    if (text && text.toLowerCase().includes('office')) {
                                        items[i].click();
                                        console.log('Clicked Office option via JS');
                                        return;
                                    }
                                }
                                // If no Office found, click second item
                                if (items.length > 0) {
                                    items[0].click();
                                    console.log('Clicked second option via JS');
                                }
                            }, 1000);
                        }
                    }
                """)
                time.sleep(3)
                print("✅ JavaScript dropdown interaction completed")
            except Exception as js_error:
                print(f"⚠️ JavaScript fallback also failed: {js_error}")
        
        # Also try to fill the textarea if present (for reason/comments)
        try:
            textarea_selectors = [
                "gt-text-area textarea",
                "textarea",
                "gt-popup-modal textarea",
                ".modal textarea"
            ]
            
            for selector in textarea_selectors:
                try:
                    textarea = driver.find_element(By.CSS_SELECTOR, selector)
                    if textarea.is_displayed():
                        textarea.clear()
                        textarea.send_keys("Working from office")
                        print("📝 Entered reason in textarea")
                        break
                except:
                    continue
        except Exception as textarea_error:
            print(f"⚠️ Could not find textarea: {textarea_error}")
        
        # Look for submit/confirm button in the modal
        time.sleep(2)  # Give time for dropdown selection to register
        try:
            # Try multiple selectors for the submit button
            submit_selectors = [
                "gt-button[shade='primary']",
                "button[shade='primary']", 
                ".hydrated[shade='primary']",
                "gt-popup-modal gt-button",
                "//button[contains(text(), 'Sign In')]",
                "//gt-button[contains(text(), 'Sign In')]",
                "//button[contains(@class, 'primary')]",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Confirm')]",
                "//button[contains(text(), 'Continue')]"
            ]
            
            button_clicked = False
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        btn = driver.find_element(By.XPATH, selector)
                    else:
                        btn = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Check if button is visible
                    if btn.is_displayed() and btn.is_enabled():
                        btn_text = btn.get_attribute('innerText') or btn.text or btn.get_attribute('name') or 'Button'
                        print(f"🎯 Found button: '{btn_text}', clicking...")
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        
                        # Try different click methods
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                        except:
                            btn.click()
                            
                        print(f"✅ Clicked button: '{btn_text}'")
                        button_clicked = True
                        time.sleep(3)
                        break
                except Exception as btn_error:
                    continue
            
            if button_clicked:
                return True
            else:
                print("⚠️ Could not find any submit button")
                # Try clicking any visible button as last resort
                try:
                    all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, gt-button")
                    for btn in all_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_text = btn.get_attribute('innerText') or btn.text or 'Unknown'
                            if btn_text.strip() and len(btn_text.strip()) > 0:
                                print(f"🔄 Trying button: '{btn_text}'")
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(2)
                                return True
                except:
                    pass
                return False
                    
        except Exception as e:
            print(f"⚠️ Error clicking submit button: {e}")
            return False
            
    except TimeoutException:
        print("ℹ️ No location modal detected")
    except Exception as e:
        print(f"⚠️ Error handling location modal: {e}")
    
    return False

def find_and_click_signin(driver):
    """Find and click the sign-in button on the home page"""
    print("\n🔍 Looking for sign-in button on home page...")
    
    # Wait a moment for any animations to complete
    time.sleep(2)
    
    # Strategy 1: Look for the attendance widget button
    try:
        # The attendance widget shows a button with primary shade
        attendance_selectors = [
            "gt-attendance-info gt-button[shade='primary']",
            "gt-attendance-info gt-button",
            ".attendance-widget gt-button",
            "gt-button[shade='primary']"
        ]
        
        for selector in attendance_selectors:
            try:
                attendance_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if attendance_button.is_displayed():
                    print(f"✅ Found attendance widget button with selector: {selector}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", attendance_button)
                    time.sleep(1)
                    # Use JavaScript click to bypass any overlays
                    driver.execute_script("arguments[0].click();", attendance_button)
                    print("🎯 Clicked attendance sign-in button!")
                    return True
            except:
                continue
                
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