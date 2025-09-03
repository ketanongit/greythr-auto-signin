#!/usr/bin/env python3
"""
GreytHR Auto Sign-In Automation Script
Compatible with GitHub Actions workflow
"""

import os
import sys
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GreytHRAutomation:
    def __init__(self):
        # Get environment variables
        self.login_url = os.environ.get('LOGIN_URL', 'https://kalvium.greythr.com/')
        self.login_id = os.environ.get('LOGIN_ID', '')
        self.login_password = os.environ.get('LOGIN_PASSWORD', '')
        self.signin_location = os.environ.get('SIGNIN_LOCATION', 'Office')
        self.debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
        self.manual_run = os.environ.get('MANUAL_RUN', 'false').lower() == 'true'
        
        # Validate credentials
        if not self.login_id or not self.login_password:
            logger.error("LOGIN_ID and LOGIN_PASSWORD environment variables are required")
            sys.exit(1)
        
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        
        # Headless mode for GitHub Actions
        if not self.debug_mode:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        
        # Common options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Add experimental options to avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # For GitHub Actions, use the system-installed chromedriver
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # For local development
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)
            
            # Execute script to prevent detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            sys.exit(1)
    
    def save_debug_info(self, stage):
        """Save debug information if in debug mode"""
        if self.debug_mode:
            try:
                # Take screenshot
                screenshot_path = f'/tmp/{stage}_screenshot.png'
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Save page source
                page_source_path = f'/tmp/{stage}_page_source.html'
                with open(page_source_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.info(f"Page source saved: {page_source_path}")
                
                # Log current URL
                logger.info(f"Current URL: {self.driver.current_url}")
            except Exception as e:
                logger.error(f"Failed to save debug info: {e}")
    
    def login(self):
        """Perform login to GreytHR"""
        try:
            logger.info(f"Navigating to login page: {self.login_url}")
            self.driver.get(self.login_url)
            time.sleep(3)
            
            # Wait for and fill username
            logger.info("Looking for username field...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"], input[type="email"], input[name="username"]'))
            )
            username_field.clear()
            username_field.send_keys(self.login_id)
            logger.info("Username entered")
            
            # Fill password
            logger.info("Looking for password field...")
            password_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
            password_field.clear()
            password_field.send_keys(self.login_password)
            logger.info("Password entered")
            
            # Submit form
            logger.info("Submitting login form...")
            try:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
                submit_button.click()
            except:
                # Alternative: press Enter on password field
                password_field.submit()
            
            # Wait for login to complete
            time.sleep(5)
            logger.info(f"Login completed, current URL: {self.driver.current_url}")
            
            self.save_debug_info("after_login")
            
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.save_debug_info("login_error")
            return False
    
    def check_already_signed_in(self):
        """Check if already signed in"""
        try:
            sign_out_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign Out')]")
            if sign_out_buttons:
                logger.info("✅ Already signed in (Sign Out button found)")
                return True
            return False
        except:
            return False
    
    def handle_sign_in(self):
        """Handle the sign-in process"""
        try:
            # Check if already signed in
            if self.check_already_signed_in():
                return True
            
            # Look for Sign In button
            logger.info("Looking for Sign In button...")
            sign_in_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign In')]")
            
            if not sign_in_buttons:
                logger.warning("No Sign In button found")
                return False
            
            # Click the first Sign In button
            logger.info(f"Found {len(sign_in_buttons)} Sign In button(s)")
            sign_in_buttons[0].click()
            logger.info("Clicked initial Sign In button")
            
            # Wait for modal to appear
            time.sleep(3)
            self.save_debug_info("after_signin_click")
            
            # Handle modal
            return self.handle_modal()
            
        except Exception as e:
            logger.error(f"Sign-in handling failed: {e}")
            self.save_debug_info("signin_error")
            return False
    
    def handle_modal(self):
        """Handle the work location modal"""
        try:
            logger.info("Checking for work location modal...")
            
            # Method 1: Direct JavaScript execution
            modal_handled = self.driver.execute_script("""
                try {
                    // Check for modal
                    const modals = document.querySelectorAll('gt-popup-modal');
                    console.log('Found ' + modals.length + ' modal(s)');
                    
                    // Look for dropdown button with Office text
                    const dropdownButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                        btn.textContent.includes('Office') && 
                        btn.offsetParent !== null
                    );
                    
                    if (dropdownButtons.length > 0) {
                        console.log('Clicking dropdown button');
                        dropdownButtons[0].click();
                        return 'dropdown_clicked';
                    }
                    
                    // Alternative: Look for any dropdown button
                    const anyDropdown = document.querySelector('button.dropdown-button');
                    if (anyDropdown) {
                        anyDropdown.click();
                        return 'any_dropdown_clicked';
                    }
                    
                    return 'no_dropdown_found';
                } catch (e) {
                    return 'error: ' + e.message;
                }
            """)
            
            logger.info(f"Dropdown interaction result: {modal_handled}")
            
            if 'clicked' in str(modal_handled):
                time.sleep(2)
                
                # Select Office from dropdown
                office_selected = self.driver.execute_script("""
                    try {
                        // Look for Office option in expanded dropdown
                        const allElements = Array.from(document.querySelectorAll('*'));
                        const officeOptions = allElements.filter(el => 
                            el.textContent.trim() === 'Office' && 
                            el.tagName !== 'BUTTON' &&
                            el.offsetParent !== null
                        );
                        
                        if (officeOptions.length > 0) {
                            officeOptions[0].click();
                            return 'office_selected';
                        }
                        
                        // Alternative: Click div with Office text
                        const divs = document.querySelectorAll('div');
                        for (const div of divs) {
                            if (div.textContent.trim() === 'Office' && !div.querySelector('button')) {
                                div.click();
                                return 'office_div_clicked';
                            }
                        }
                        
                        return 'office_not_found';
                    } catch (e) {
                        return 'error: ' + e.message;
                    }
                """)
                
                logger.info(f"Office selection result: {office_selected}")
                time.sleep(2)
            
            # Click Sign In button in modal
            signin_result = self.driver.execute_script("""
                try {
                    // Find all Sign In buttons
                    const signInButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                        btn.textContent.trim() === 'Sign In' && 
                        btn.offsetParent !== null
                    );
                    
                    if (signInButtons.length > 1) {
                        // Click the last one (should be in modal)
                        signInButtons[signInButtons.length - 1].click();
                        return 'modal_signin_clicked';
                    } else if (signInButtons.length === 1) {
                        signInButtons[0].click();
                        return 'signin_clicked';
                    }
                    
                    return 'no_signin_button';
                } catch (e) {
                    return 'error: ' + e.message;
                }
            """)
            
            logger.info(f"Sign In click result: {signin_result}")
            
            # Wait for action to complete
            time.sleep(4)
            
            # Verify success
            return self.verify_signin_success()
            
        except Exception as e:
            logger.error(f"Modal handling failed: {e}")
            return False
    
    def verify_signin_success(self):
        """Verify if sign-in was successful"""
        try:
            # Check for Sign Out button
            if self.check_already_signed_in():
                logger.info("✅ Successfully signed in - Sign Out button present")
                return True
            
            # Check for success message
            success_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Successfully') or contains(text(), 'successfully')]")
            if success_elements:
                logger.info("✅ Successfully signed in - Success message found")
                return True
            
            # Check if modal is gone
            modals = self.driver.find_elements(By.CSS_SELECTOR, 'gt-popup-modal[open]')
            if not modals:
                logger.info("Modal closed - checking final state...")
                if self.check_already_signed_in():
                    return True
                else:
                    logger.warning("⚠️ Modal closed but sign-in status unclear")
                    return False
            else:
                logger.error("❌ Modal still open - sign-in may have failed")
                return False
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def run(self):
        """Main execution flow"""
        try:
            # Setup driver
            self.setup_driver()
            
            # Login
            if not self.login():
                logger.error("Login failed")
                return False
            
            # Handle sign-in
            success = self.handle_sign_in()
            
            if success:
                logger.info("=" * 50)
                logger.info("✅ GREYTHR AUTO SIGN-IN SUCCESSFUL")
                logger.info("=" * 50)
            else:
                logger.error("=" * 50)
                logger.error("❌ GREYTHR AUTO SIGN-IN FAILED")
                logger.error("=" * 50)
            
            self.save_debug_info("final")
            
            return success
            
        except Exception as e:
            logger.error(f"Automation failed: {e}")
            self.save_debug_info("error")
            return False
        finally:
            if self.driver:
                time.sleep(2)
                self.driver.quit()
                logger.info("Driver closed")

def main():
    """Main entry point"""
    automation = GreytHRAutomation()
    success = automation.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()