const { chromium } = require('playwright');
const fs = require("fs");

// Get credentials from environment variables (GitHub Secrets)
const getConfig = () => {
  return {
    url: process.env.GREYTHR_URL || "https://kalvium.greythr.com/",
    username: process.env.LOGIN_ID,
    password: process.env.LOGIN_PASSWORD,
    location: process.env.SIGNIN_LOCATION || "Office",
    debugMode: process.env.DEBUG_MODE === 'true',
    isManualRun: process.env.MANUAL_RUN === 'true'
  };
};

const automate = async () => {
  const config = getConfig();
  
  // Validate credentials
  if (!config.username || !config.password) {
    console.error("ERROR: LOGIN_ID and LOGIN_PASSWORD environment variables are required");
    process.exit(1);
  }

  console.log("Starting GreytHR automation...");
  console.log(`URL: ${config.url}`);
  console.log(`Debug Mode: ${config.debugMode}`);
  console.log(`Manual Run: ${config.isManualRun}`);

  // Launch browser with more robust settings
  const browser = await chromium.launch({
    headless: !config.debugMode, // Headless in production, visible in debug
    slowMo: 250, // Delay between actions for stability
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--window-size=1920,1080'
    ]
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  
  const page = await context.newPage();
  
  // Add console listener for debugging
  if (config.debugMode) {
    page.on('console', msg => console.log('Browser console:', msg.text()));
  }
  
  // Set longer timeout
  page.setDefaultTimeout(60000);
  
  var result = "";
  
  try {
    console.log("Navigating to login page...");
    await page.goto(config.url, { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
    
    // Wait for page to be interactive
    await page.waitForLoadState('networkidle');
    console.log("Page loaded successfully");
    
    // Save screenshot if in debug mode
    if (config.debugMode) {
      await page.screenshot({ path: "/tmp/initial_page.png" });
    }
    
    // Wait for and fill username
    console.log("Looking for username field...");
    const usernameField = await page.waitForSelector('input[type="text"], input[type="email"], input[name="username"]', { timeout: 30000 });
    await usernameField.fill(config.username);
    console.log("Username entered");
    
    // Wait for and fill password
    console.log("Looking for password field...");
    const passwordField = await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    await passwordField.fill(config.password);
    console.log("Password entered");
    
    // Submit form
    console.log("Submitting login form...");
    await Promise.race([
      page.click('button[type="submit"]'),
      page.click('input[type="submit"]'),
      page.press('input[type="password"]', 'Enter')
    ]);
    
    // Wait for navigation after login
    console.log("Waiting for login to complete...");
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    
    console.log("Current URL:", page.url());
    
    if (config.debugMode) {
      await page.screenshot({ path: "/tmp/dashboard.png" });
    }
    
    // Check if already signed in (Sign Out button exists)
    const signOutExists = await page.locator('button:has-text("Sign Out")').count();
    if (signOutExists > 0) {
      console.log("Already signed in (Sign Out button found)");
      result = "✅ Already signed in - no action needed";
      if (config.debugMode) {
        await page.screenshot({ path: "/tmp/already_signed_in.png" });
      }
      await browser.close();
      return result;
    }
    
    console.log("Not signed in yet, proceeding...");
    
    // Look for the Sign In button in the attendance section
    console.log("Looking for Sign In button in attendance section...");
    
    // Wait for and click the Sign In button
    const signInButton = await page.locator('button:has-text("Sign In")').first();
    await signInButton.waitFor({ state: 'visible', timeout: 10000 });
    console.log("Found Sign In button");
    
    await signInButton.click();
    console.log("Clicked initial Sign In button");
    
    // Wait for modal with a longer timeout
    await page.waitForTimeout(4000);
    console.log("Waiting for modal to appear...");
    
    // Save debug info
    if (config.debugMode) {
      await page.screenshot({ path: "/tmp/modal_state.png" });
      const htmlContent = await page.content();
      fs.writeFileSync('/tmp/modal_page.html', htmlContent);
      console.log("Saved debug files to /tmp/");
    }
    
    // Check what's visible on the page
    const debugInfo = await page.evaluate(() => {
      const info = {
        modals: [],
        dropdowns: [],
        buttons: [],
        modalPresent: false
      };
      
      // Check for modals
      const modals = document.querySelectorAll('gt-popup-modal');
      modals.forEach((modal, index) => {
        info.modals.push({
          index,
          hasOpen: modal.hasAttribute('open'),
          isVisible: modal.offsetParent !== null
        });
      });
      
      // Check for dropdowns
      const dropdowns = document.querySelectorAll('gt-dropdown, .dropdown-button, button.dropdown-button, [class*="dropdown"]');
      dropdowns.forEach((dd, index) => {
        if (dd.offsetParent !== null) {
          info.dropdowns.push({
            index,
            tagName: dd.tagName,
            className: dd.className,
            text: dd.textContent?.trim().substring(0, 50),
            isVisible: true
          });
        }
      });
      
      // Check for all visible buttons
      const buttons = document.querySelectorAll('button');
      buttons.forEach((btn) => {
        if (btn.offsetParent !== null && btn.textContent.trim()) {
          info.buttons.push(btn.textContent.trim());
        }
      });
      
      // Check if modal text is present
      const modalTexts = ['Tell us your work location', 'You are not signed in yet', 'Sign-In Location'];
      for (const text of modalTexts) {
        const elements = Array.from(document.querySelectorAll('*')).filter(el => 
          el.textContent.includes(text) && el.offsetParent !== null
        );
        if (elements.length > 0) {
          info.modalPresent = true;
          break;
        }
      }
      
      return info;
    });
    
    console.log("Debug Info:", JSON.stringify(debugInfo, null, 2));
    
    // If modal is present, handle it
    if (debugInfo.modalPresent || debugInfo.modals.length > 0) {
      console.log("Modal detected, attempting to handle...");
      
      // Method 1: Try using Playwright's built-in selectors
      try {
        // Look for dropdown with Office text
        const dropdownWithOffice = await page.locator('button:has-text("' + config.location + '")').first();
        if (await dropdownWithOffice.count() > 0) {
          console.log(`Found dropdown with ${config.location} text, clicking...`);
          await dropdownWithOffice.click();
          await page.waitForTimeout(2000);
          
          // Look for Office option in expanded dropdown
          const officeOptions = await page.locator('div:has-text("' + config.location + '")').all();
          for (const option of officeOptions) {
            const text = await option.textContent();
            if (text?.trim() === config.location) {
              console.log(`Clicking ${config.location} option...`);
              await option.click();
              break;
            }
          }
          
          await page.waitForTimeout(2000);
          
          // Click Sign In button
          const modalSignInButtons = await page.locator('button:has-text("Sign In")').all();
          if (modalSignInButtons.length > 1) {
            console.log(`Found ${modalSignInButtons.length} Sign In buttons, clicking the last one...`);
            await modalSignInButtons[modalSignInButtons.length - 1].click();
          } else if (modalSignInButtons.length === 1) {
            console.log("Clicking the only Sign In button...");
            await modalSignInButtons[0].click();
          }
          
          result = "✅ Modal handled with Playwright selectors";
        }
      } catch (e) {
        console.log("Playwright selector method failed:", e.message);
      }
      
      // Method 2: Direct DOM manipulation if Method 1 failed
      if (!result.includes("✅")) {
        console.log("Trying direct DOM manipulation...");
        
        const manipResult = await page.evaluate((location) => {
          try {
            // Find and click any button containing location text
            const locationButtons = Array.from(document.querySelectorAll('button')).filter(b => 
              b.textContent.includes(location) && b.offsetParent !== null
            );
            
            if (locationButtons.length > 0) {
              locationButtons[0].click();
              console.log(`Clicked ${location} button`);
              
              // Wait a bit and try to find location option
              setTimeout(() => {
                const allDivs = Array.from(document.querySelectorAll('div'));
                const locationDiv = allDivs.find(d => 
                  d.textContent.trim() === location && 
                  !d.querySelector('button') // Not the button container
                );
                if (locationDiv) {
                  locationDiv.click();
                  console.log(`Clicked ${location} div`);
                }
                
                // Then click Sign In
                setTimeout(() => {
                  const signInButtons = Array.from(document.querySelectorAll('button')).filter(b => 
                    b.textContent.trim() === 'Sign In' && b.offsetParent !== null
                  );
                  if (signInButtons.length > 0) {
                    signInButtons[signInButtons.length - 1].click();
                    console.log("Clicked Sign In");
                  }
                }, 1000);
              }, 1000);
              
              return "Attempted DOM manipulation";
            }
            
            return `No ${location} button found`;
          } catch (error) {
            return error.message;
          }
        }, config.location);
        
        console.log("DOM manipulation result:", manipResult);
        await page.waitForTimeout(4000);
      }
      
    } else {
      console.log("No modal detected on page");
      result = "❌ Modal did not appear after clicking Sign In";
    }
    
    // Final verification
    await page.waitForTimeout(3000);
    console.log("Performing final verification...");
    
    // Check for success indicators
    const signOutFinal = await page.locator('button:has-text("Sign Out")').count();
    const successMessage = await page.locator('text=/successfully/i').count();
    
    if (signOutFinal > 0) {
      result = "✅ Successfully signed in - Sign Out button present";
      console.log("SUCCESS: Sign Out button found");
    } else if (successMessage > 0) {
      result = "✅ Successfully signed in - Success message present";
      console.log("SUCCESS: Success message found");
    } else if (!result.includes("✅")) {
      result = "⚠️ Sign in attempted but could not verify success";
      console.log("WARNING: Could not verify sign in success");
    }
    
    // Take final screenshot
    if (config.debugMode) {
      await page.screenshot({ path: "/tmp/final_result.png" });
      const finalHtml = await page.content();
      fs.writeFileSync('/tmp/final_page_source.html', finalHtml);
    }
    
  } catch (error) {
    console.log("Error during automation:", error.message);
    if (config.debugMode) {
      await page.screenshot({ path: "/tmp/error_screenshot.png" });
    }
    result = "❌ Error: " + error.message;
  }
  
  await browser.close();
  return result;
};

const signIn = async () => {
  const date = new Date();
  let result = await automate();
  
  // Log result
  const logMessage = `${result} at ${date.getHours()}:${date.getMinutes()} on ${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
  
  console.log("\n" + "=".repeat(50));
  console.log("FINAL RESULT:", result);
  console.log("Time:", new Date().toLocaleString());
  console.log("=".repeat(50));
  
  // Append to log file if exists
  try {
    fs.appendFileSync("log.txt", `\n${logMessage}`);
  } catch (e) {
    // Log file may not exist in CI environment
    console.log("Could not write to log file:", e.message);
  }
  
  // Exit with appropriate code for GitHub Actions
  if (result.includes("✅")) {
    process.exit(0); // Success
  } else if (result.includes("⚠️")) {
    console.log("Warning: Sign-in status unclear");
    process.exit(0); // Don't fail the workflow for warnings
  } else {
    process.exit(1); // Failure
  }
};

// Run sign-in immediately when script is executed
signIn();