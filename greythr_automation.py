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

def complete_signin_process(driver):
    """Complete the entire sign-in process using JavaScript"""
    print("🚀 Starting complete sign-in process with JavaScript...")
    
    result = driver.execute_script("""
        // Complete GreytHR sign-in automation
        var results = [];
        var stepCount = 0;
        
        function logStep(message) {
            stepCount++;
            results.push(stepCount + '. ' + message);
            console.log(message);
        }
        
        function findAndClickElement(selectors, description) {
            for (var i = 0; i < selectors.length; i++) {
                var elements = document.querySelectorAll(selectors[i]);
                for (var j = 0; j < elements.length; j++) {
                    var el = elements[j];
                    if (el.offsetParent !== null) { // Check if visible
                        logStep('Found ' + description + ' with selector: ' + selectors[i]);
                        el.click();
                        return true;
                    }
                }
            }
            return false;
        }
        
        function handleLocationModal() {
            // Check if location modal is present
            var modalTexts = document.querySelectorAll('*');
            var hasModal = false;
            
            for (var i = 0; i < modalTexts.length; i++) {
                if (modalTexts[i].textContent && modalTexts[i].textContent.includes('Tell us your work location')) {
                    hasModal = true;
                    break;
                }
            }
            
            if (!hasModal) {
                logStep('No location modal detected');
                return false;
            }
            
            logStep('Location modal detected');
            
            // Try to find and handle dropdown - multiple approaches
            var dropdownHandled = false;
            
            // Approach 1: Look for any dropdown/select elements
            var dropdownSelectors = [
                'gt-dropdown',
                'select',
                '[role="combobox"]',
                '[role="listbox"]',
                '.dropdown',
                '.select'
            ];
            
            for (var i = 0; i < dropdownSelectors.length; i++) {
                var dropdowns = document.querySelectorAll(dropdownSelectors[i]);
                for (var j = 0; j < dropdowns.length; j++) {
                    var dropdown = dropdowns[j];
                    if (dropdown.offsetParent !== null) {
                        logStep('Found dropdown with selector: ' + dropdownSelectors[i]);
                        
                        // Try to click it to open
                        var button = dropdown.querySelector('button, [role="button"], .dropdown-toggle');
                        if (button) {
                            button.click();
                            logStep('Clicked dropdown button');
                            
                            // Wait for options to appear
                            setTimeout(function() {
                                // Look for office option
                                var optionSelectors = [
                                    '[role="option"]',
                                    '.dropdown-item',
                                    '.option',
                                    'li',
                                    'div[class*="item"]'
                                ];
                                
                                for (var k = 0; k < optionSelectors.length; k++) {
                                    var options = document.querySelectorAll(optionSelectors[k]);
                                    for (var l = 0; l < options.length; l++) {
                                        var optionText = options[l].textContent || options[l].innerText || '';
                                        if (optionText.toLowerCase().includes('office')) {
                                            options[l].click();
                                            logStep('Selected Office option: ' + optionText);
                                            dropdownHandled = true;
                                            return;
                                        }
                                    }
                                }
                                
                                // If no office found, try first option
                                if (options.length > 0) {
                                    options[0].click();
                                    logStep('Selected first option as fallback');
                                    dropdownHandled = true;
                                }
                            }, 1500);
                            
                            return true;
                        }
                    }
                }
            }
            
            // Approach 2: Direct text-based selection
            if (!dropdownHandled) {
                var allElements = document.querySelectorAll('*');
                for (var i = 0; i < allElements.length; i++) {
                    var el = allElements[i];
                    var text = el.textContent || el.innerText || '';
                    if (text === 'Office' && el.offsetParent !== null) {
                        logStep('Found Office text element, clicking directly');
                        el.click();
                        dropdownHandled = true;
                        break;
                    }
                }
            }
            
            return dropdownHandled;
        }
        
        function clickSignInButton() {
            // Look for sign-in buttons
            var signInSelectors = [
                'gt-button[shade="primary"]',
                'button[shade="primary"]',
                '.btn-primary',
                'button:contains("Sign In")',
                '[role="button"]:contains("Sign In")'
            ];
            
            var buttonClicked = false;
            
            for (var i = 0; i < signInSelectors.length; i++) {
                var buttons = document.querySelectorAll(signInSelectors[i]);
                for (var j = 0; j < buttons.length; j++) {
                    var btn = buttons[j];
                    var btnText = btn.textContent || btn.innerText || btn.getAttribute('name') || '';
                    
                    if (btn.offsetParent !== null && 
                        (btnText.toLowerCase().includes('sign') || 
                         btnText.toLowerCase().includes('submit') || 
                         btnText.toLowerCase().includes('continue'))) {
                        
                        logStep('Clicking button: ' + btnText);
                        btn.click();
                        buttonClicked = true;
                        return true;
                    }
                }
            }
            
            return buttonClicked;
        }
        
        // Main execution flow
        logStep('Starting JavaScript automation');
        
        // Handle location modal if present
        handleLocationModal();
        
        // Wait a bit for any changes
        setTimeout(function() {
            // Click sign-in button
            var signInClicked = clickSignInButton();
            if (signInClicked) {
                logStep('Sign-in button clicked');
                
                // Wait and handle modal again if needed
                setTimeout(function() {
                    handleLocationModal();
                    
                    // Final sign-in attempt
                    setTimeout(function() {
                        clickSignInButton();
                        logStep('Final sign-in attempt completed');
                    }, 2000);
                }, 3000);
            } else {
                logStep('No sign-in button found');
            }
        }, 2000);
        
        return results.join('\\n');
    """)
    
    time.sleep(10)  # Give time for all JavaScript operations to complete
    print(f"📋 JavaScript execution log:\n{result}")
    
    return result

def handle_location_modal_selenium_fallback(driver, location):
    """Selenium fallback for location modal"""
    print("🔄 Using Selenium fallback for location modal...")
    
    try:
        # Look for any visible dropdown or select elements
        all_selects = driver.find_elements(By.CSS_SELECTOR, "select, gt-dropdown, [role='combobox'], [role='listbox']")
        for select_el in all_selects:
            if select_el.is_displayed():
                print(f"📋 Found dropdown element: {select_el.tag_name}")
                # Try clicking it
                driver.execute_script("arguments[0].click();", select_el)
                time.sleep(2)
                break
        
        # Look for Office text anywhere and click it
        office_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Office')]")
        for office_el in office_elements:
            if office_el.is_displayed():
                print(f"✅ Found Office text element, clicking...")
                driver.execute_script("arguments[0].click();", office_el)
                time.sleep(2)
                break
        
        # Click any primary button
        primary_buttons = driver.find_elements(By.CSS_SELECTOR, "gt-button[shade='primary'], button[shade='primary'], .btn-primary")
        for btn in primary_buttons:
            if btn.is_displayed():
                btn_text = btn.get_attribute('innerText') or btn.text or 'Button'
                print(f"🎯 Clicking primary button: '{btn_text}'")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                break
                
        return True
        
    except Exception as e:
        print(f"⚠️ Selenium fallback failed: {e}")
        return False

def verify_signin_status(driver):
    """Verify if sign-in was successful"""
    print("🔍 Verifying sign-in status...")
    
    try:
        # Check for various success indicators
        page_source = driver.page_source.lower()
        
        # Look for signed-in indicators
        success_indicators = [
            "signed in",
            "attendance marked", 
            "check in successful",
            "punch in successful",
            "already signed in"
        ]
        
        for indicator in success_indicators:
            if indicator in page_source:
                print(f"✅ Success indicator found: '{indicator}'")
                return True
        
        # Check if Sign In button is still present (indicates not signed in)
        try:
            signin_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Sign In') or contains(text(), 'Check In')]")
            visible_signin_buttons = [btn for btn in signin_buttons if btn.is_displayed()]
            
            if visible_signin_buttons:
                print("❌ Sign In button still visible - attendance not marked")
                return False
            else:
                print("✅ No Sign In button visible - likely signed in")
                return True
                
        except:
            print("⚠️ Could not determine button status")
            
        # Check attendance widget for status
        try:
            attendance_info = driver.find_elements(By.CSS_SELECTOR, "gt-attendance-info")
            if attendance_info:
                attendance_text = attendance_info[0].get_attribute('innerText') or attendance_info[0].text
                print(f"📊 Attendance widget text: {attendance_text}")
                if any(word in attendance_text.lower() for word in ['signed', 'checked', 'marked']):
                    return True
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"⚠️ Error verifying status: {e}")
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
        
        # Use JavaScript-based approach for the entire sign-in process
        js_result = complete_signin_process(driver)
        
        # Also try Selenium fallback if location modal is still present
        try:
            modal_still_present = driver.find_elements(By.XPATH, "//*[contains(text(), 'Tell us your work location')]")
            if modal_still_present and modal_still_present[0].is_displayed():
                print("🔄 Location modal still present, trying Selenium fallback...")
                handle_location_modal_selenium_fallback(driver, loc)
        except:
            pass
        
        # Final verification with proper status check
        time.sleep(5)
        is_signed_in = verify_signin_status(driver)
        
        if is_signed_in:
            print("✅ ATTENDANCE SIGN-IN VERIFIED SUCCESSFUL!")
        else:
            print("❌ ATTENDANCE SIGN-IN FAILED - Still showing as not signed in")
            
            # One more attempt with different approach
            print("🔄 Making final attempt...")
            final_attempt_result = driver.execute_script("""
                // Final aggressive attempt
                var clicked = false;
                
                // Find any button that might be a sign-in button
                var allButtons = document.querySelectorAll('button, gt-button, [role="button"]');
                
                for (var i = 0; i < allButtons.length; i++) {
                    var btn = allButtons[i];
                    var text = btn.textContent || btn.innerText || btn.getAttribute('aria-label') || '';
                    
                    if (btn.offsetParent !== null && 
                        (text.toLowerCase().includes('sign') || 
                         text.toLowerCase().includes('check') ||
                         text.toLowerCase().includes('punch') ||
                         text.toLowerCase().includes('mark'))) {
                        
                        console.log('Final attempt clicking: ' + text);
                        btn.click();
                        clicked = true;
                        
                        // If this opens a modal, try to handle it
                        setTimeout(function() {
                            // Look for Office option anywhere
                            var officeElements = document.querySelectorAll('*');
                            for (var j = 0; j < officeElements.length; j++) {
                                var el = officeElements[j];
                                var elText = el.textContent || el.innerText || '';
                                if (elText === 'Office' && el.offsetParent !== null) {
                                    el.click();
                                    console.log('Clicked Office option in final attempt');
                                    
                                    // Then click any submit button
                                    setTimeout(function() {
                                        var submitButtons = document.querySelectorAll('button, gt-button');
                                        for (var k = 0; k < submitButtons.length; k++) {
                                            var submitBtn = submitButtons[k];
                                            var submitText = submitBtn.textContent || submitBtn.innerText || '';
                                            if (submitBtn.offsetParent !== null && 
                                                (submitText.toLowerCase().includes('sign') || 
                                                 submitText.toLowerCase().includes('submit') ||
                                                 submitText.toLowerCase().includes('continue'))) {
                                                submitBtn.click();
                                                console.log('Clicked final submit button: ' + submitText);
                                                break;
                                            }
                                        }
                                    }, 1000);
                                    break;
                                }
                            }
                        }, 2000);
                        break;
                    }
                }
                
                return clicked ? 'Final attempt made' : 'No suitable button found';
            """)
            
            time.sleep(8)
            print(f"🔄 Final attempt result: {final_attempt_result}")
            
            # Verify again
            final_status = verify_signin_status(driver)
            if final_status:
                print("✅ FINAL VERIFICATION: SIGN-IN SUCCESSFUL!")
            else:
                print("❌ FINAL VERIFICATION: SIGN-IN STILL FAILED")
        
        # Get final status info
        current_url = driver.current_url
        print(f"🌐 Final URL: {current_url}")
        
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

def handle_location_modal_selenium_fallback(driver, location):
    """Selenium fallback for location modal"""
    print("🔄 Using Selenium fallback for location modal...")
    
    try:
        # Look for Office text anywhere and click it
        office_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Office')]")
        for office_el in office_elements:
            if office_el.is_displayed():
                print(f"✅ Found Office text element, clicking...")
                driver.execute_script("arguments[0].click();", office_el)
                time.sleep(2)
                break
        
        # Click any primary button
        primary_buttons = driver.find_elements(By.CSS_SELECTOR, "gt-button[shade='primary'], button[shade='primary'], .btn-primary")
        for btn in primary_buttons:
            if btn.is_displayed():
                btn_text = btn.get_attribute('innerText') or btn.text or 'Button'
                print(f"🎯 Clicking primary button: '{btn_text}'")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                break
                
        return True
        
    except Exception as e:
        print(f"⚠️ Selenium fallback failed: {e}")
        return False

if __name__ == "__main__":
    main()