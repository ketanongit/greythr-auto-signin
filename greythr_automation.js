const { chromium } = require('playwright');
const config = require("config");
const fs = require("fs");
const path = require("path");

const checkArguments = async () => {
  const args = process.argv;
  var dir = path.join(__dirname, "config");

  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // Handle GitHub Actions environment
  if (process.env.GITHUB_ACTIONS) {
    console.log("Running in GitHub Actions environment");
    return; // Skip command line argument processing
  }

  if (args.includes("--user") && !args.includes("--password")) {
    console.log("Please provide password along with user");
    process.exit();
  }
  if (!args.includes("--user") && args.includes("--password")) {
    console.log("Please provide user along with password");
    process.exit();
  }
  if (args.includes("--user") && args.includes("--password")) {
    let user = args.indexOf("--user");
    let password = args.indexOf("--password");
    if (user > 0 && password > 0) {
      let credentials = {
        username: args[user + 1],
        password: args[password + 1],
      };
      fs.writeFileSync(
        path.join(__dirname, "config", "default.json"),
        JSON.stringify(credentials)
      );
      console.log("Your credentials are saved! ");
      console.log('Run "node index.js" to sign in');
      process.exit();
    }
  }
};

checkArguments();

const automate = async () => {
  // Launch browser with GitHub Actions optimized settings
  const browser = await chromium.launch({
    headless: process.env.GITHUB_ACTIONS ? true : false, // Always headless in CI
    slowMo: process.env.GITHUB_ACTIONS ? 100 : 300,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
      '--window-size=1920,1080'
    ]
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  
  const page = await context.newPage();
  
  // Add console listener for debugging
  page.on('console', msg => {
    console.log(`Browser console [${msg.type()}]:`, msg.text());
  });
  
  // Set longer timeout for CI environment
  const timeout = process.env.GITHUB_ACTIONS ? 90000 : 60000;
  page.setDefaultTimeout(timeout);
  
  var result = "";
  
  try {
    console.log("Navigating to login page...");
    await page.goto("https://kalvium.greythr.com/", { 
      waitUntil: 'domcontentloaded',
      timeout: timeout 
    });
    
    // Wait for page to be interactive
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    console.log("Page loaded successfully");
    
    // Take initial screenshot for debugging
    if (process.env.DEBUG_MODE === 'true') {
      await page.screenshot({ path: "login_page.png" });
    }
    
    // Wait for and fill username
    console.log("Looking for username field...");
    const usernameField = await page.waitForSelector('input[type="text"], input[type="email"], input[name="username"], input[placeholder*="mail"], input[placeholder*="user"]', { timeout: 30000 });
    await usernameField.fill(config.get("username"));
    console.log("Username entered");
    
    // Wait for and fill password
    console.log("Looking for password field...");
    const passwordField = await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    await passwordField.fill(config.get("password"));
    console.log("Password entered");
    
    // Take screenshot before submission if debug mode
    if (process.env.DEBUG_MODE === 'true') {
      await page.screenshot({ path: "before_submit.png" });
    }
    
    // Submit form - try multiple methods
    console.log("Submitting login form...");
    try {
      // Try clicking submit button first
      const submitButton = await page.locator('button[type="submit"], input[type="submit"], button:has-text("Sign In"), button:has-text("Login")').first();
      if (await submitButton.count() > 0) {
        await submitButton.click();
      } else {
        // Fallback to Enter key
        await page.press('input[type="password"]', 'Enter');
      }
    } catch (e) {
      console.log("Submit button click failed, trying Enter key:", e.message);
      await page.press('input[type="password"]', 'Enter');
    }
    
    // Wait for navigation after login
    console.log("Waiting for login to complete...");
    await page.waitForLoadState('networkidle', { timeout: 45000 });
    
    console.log("Current URL:", page.url());
    
    // Take screenshot after login
    await page.screenshot({ path: "after_login.png" });
    
    // Check if already signed in (Sign Out button exists)
    const signOutExists = await page.locator('button:has-text("Sign Out"), a:has-text("Sign Out")').count();
    if (signOutExists > 0) {
      console.log("Already signed in (Sign Out button found)");
      result = "✅ Already signed in - no action needed";
      return result;
    }
    
    console.log("Not signed in yet, proceeding with attendance sign-in...");
    
    // Look for the Sign In button in the attendance section with multiple strategies
    console.log("Looking for Sign In button in attendance section...");
    
    let signInButton;
    try {
      // Strategy 1: Direct button text match
      signInButton = page.locator('button:has-text("Sign In")').first();
      if (await signInButton.count() === 0) {
        // Strategy 2: Look for buttons containing "Sign" or "In"
        signInButton = page.locator('button').filter({ hasText: /sign\s*in/i }).first();
      }
      if (await signInButton.count() === 0) {
        // Strategy 3: Look in attendance or dashboard sections
        signInButton = page.locator('[class*="attendance"] button, [class*="dashboard"] button').filter({ hasText: /sign/i }).first();
      }
    } catch (e) {
      console.log("Error finding sign in button:", e.message);
    }
    
    if (await signInButton.count() > 0) {
      console.log("Found Sign In button, clicking...");
      await signInButton.click();
      console.log("Clicked initial Sign In button");
      
      // Wait for modal with extended timeout
      await page.waitForTimeout(5000);
      console.log("Waiting for modal to appear...");
      
      // Take screenshot of modal state
      await page.screenshot({ path: "modal_state.png" });
      
      // Debug: Check what's on the page
      const modalCheck = await page.evaluate(() => {
        const modalTexts = ['Tell us your work location', 'You are not signed in yet', 'Sign-In Location', 'Location', 'Office', 'Work from'];
        for (const text of modalTexts) {
          const elements = Array.from(document.querySelectorAll('*')).filter(el => 
            el.textContent.includes(text) && el.offsetParent !== null
          );
          if (elements.length > 0) {
            return { found: true, text, count: elements.length };
          }
        }
        
        // Also check for any dropdowns or select elements
        const dropdowns = document.querySelectorAll('select, [role="combobox"], [class*="dropdown"], [class*="select"]');
        const buttons = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null);
        
        return { 
          found: false, 
          dropdowns: dropdowns.length, 
          buttons: buttons.map(b => b.textContent?.trim()).filter(t => t) 
        };
      });
      
      console.log("Modal check result:", JSON.stringify(modalCheck, null, 2));
      
      if (modalCheck.found || modalCheck.dropdowns > 0) {
        console.log("Modal/dropdown detected, attempting to handle...");
        
        try {
          // Handle location selection
          await handleLocationSelection(page);
          
          // Wait and click final Sign In button
          await page.waitForTimeout(2000);
          
          const finalSignInButtons = await page.locator('button:has-text("Sign In")').all();
          if (finalSignInButtons.length > 0) {
            console.log(`Found ${finalSignInButtons.length} Sign In buttons, clicking the last one...`);
            await finalSignInButtons[finalSignInButtons.length - 1].click();
            result = "✅ Successfully completed sign-in process";
          } else {
            result = "⚠️ Could not find final Sign In button after location selection";
          }
          
        } catch (modalError) {
          console.log("Error handling modal:", modalError.message);
          result = "⚠️ Modal appeared but could not be handled: " + modalError.message;
        }
      } else {
        result = "⚠️ No modal detected after clicking Sign In button";
      }
      
    } else {
      console.log("No Sign In button found on the page");
      result = "❌ Could not find Sign In button on the dashboard";
    }
    
    // Final verification with extended wait
    await page.waitForTimeout(5000);
    console.log("Performing final verification...");
    
    const signOutFinal = await page.locator('button:has-text("Sign Out"), a:has-text("Sign Out")').count();
    const successMessage = await page.locator('text=/successfully/i, text=/signed.*in/i').count();
    
    if (signOutFinal > 0) {
      result = "✅ Successfully signed in - Sign Out button present";
    } else if (successMessage > 0) {
      result = "✅ Successfully signed in - Success message present";  
    } else if (!result.includes("✅")) {
      result = result || "⚠️ Sign in attempted but could not verify success";
    }
    
    // Take final screenshot
    await page.screenshot({ path: "final_result.png" });
    
  } catch (error) {
    console.log("Error during automation:", error.message);
    await page.screenshot({ path: "error_page.png" });
    result = "❌ Error: " + error.message;
  }
  
  await browser.close();
  return result;
};

// Helper function to handle location selection
const handleLocationSelection = async (page) => {
  console.log("Handling location selection...");
  
  // Strategy 1: Look for Office button/dropdown
  try {
    const officeButton = page.locator('button:has-text("Office"), [role="combobox"]:has-text("Office")').first();
    if (await officeButton.count() > 0) {
      await officeButton.click();
      await page.waitForTimeout(1000);
      
      // Look for Office option in dropdown
      const officeOption = page.locator('div:has-text("Office"), li:has-text("Office"), option:has-text("Office")').first();
      if (await officeOption.count() > 0) {
        await officeOption.click();
        console.log("Selected Office from dropdown");
        return;
      }
    }
  } catch (e) {
    console.log("Strategy 1 failed:", e.message);
  }
  
  // Strategy 2: Look for select element
  try {
    const selectElement = page.locator('select').first();
    if (await selectElement.count() > 0) {
      await selectElement.selectOption({ label: 'Office' });
      console.log("Selected Office from select element");
      return;
    }
  } catch (e) {
    console.log("Strategy 2 failed:", e.message);
  }
  
  // Strategy 3: Direct DOM manipulation
  try {
    await page.evaluate(() => {
      // Find any element containing "Office" and click it
      const allElements = Array.from(document.querySelectorAll('*'));
      const officeElements = allElements.filter(el => 
        el.textContent?.trim() === 'Office' && 
        el.offsetParent !== null &&
        (el.tagName === 'DIV' || el.tagName === 'LI' || el.tagName === 'OPTION')
      );
      
      if (officeElements.length > 0) {
        officeElements[0].click();
        return true;
      }
      
      // Try to find and interact with dropdowns
      const dropdowns = document.querySelectorAll('[role="combobox"], .dropdown, [class*="select"]');
      for (const dropdown of dropdowns) {
        if (dropdown.offsetParent !== null) {
          dropdown.click();
          setTimeout(() => {
            const options = document.querySelectorAll('[role="option"], .option, [class*="option"]');
            for (const option of options) {
              if (option.textContent?.includes('Office')) {
                option.click();
                break;
              }
            }
          }, 500);
          break;
        }
      }
      
      return false;
    });
    console.log("Attempted DOM manipulation for location selection");
  } catch (e) {
    console.log("Strategy 3 failed:", e.message);
  }
};

const signIn = async () => {
  const date = new Date();
  console.log(`Starting GreytHR automation at ${date.toLocaleString()}`);
  
  let result = await automate();
  
  const logEntry = `\n${result} at ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')} on ${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
  
  fs.appendFileSync("log.txt", logEntry);
  
  console.log("\n" + "=".repeat(50));
  console.log("FINAL RESULT:", result);
  console.log("=".repeat(50));
  
  // Set appropriate exit code for GitHub Actions
  if (result.includes("❌")) {
    process.exit(1); // Failure
  } else if (result.includes("⚠️")) {
    console.log("Warning: Process completed with warnings but did not fail completely");
    // Don't exit with error for warnings, just log them
  }
  // Success cases (✅) will exit with 0 by default
};

// Check if credentials exist, if not in GitHub Actions
if (!process.env.GITHUB_ACTIONS && !fs.existsSync(path.join(__dirname, "config", "default.json"))) {
  console.log("No credentials found. Please run:");
  console.log("node index.js --user YOUR_USERNAME --password YOUR_PASSWORD");
  process.exit(1);
}

// Run sign-in
signIn();