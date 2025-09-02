const { chromium } = require('playwright');
const fs = require('fs');

async function setupBrowser() {
    console.log('🚀 Setting up browser...');
    
    const browser = await chromium.launch({
        headless: process.env.DEBUG_MODE !== 'true', // Show browser in debug mode
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    });
    
    const page = await context.newPage();
    
    // Set longer timeout
    page.setDefaultTimeout(30000);
    page.setDefaultNavigationTimeout(30000);
    
    return { browser, context, page };
}

async function loginToGreytHR(page) {
    const url = process.env.LOGIN_URL;
    const loginId = process.env.LOGIN_ID;
    const password = process.env.LOGIN_PASSWORD;
    
    console.log(`🌐 Navigating to ${url}`);
    await page.goto(url, { waitUntil: 'networkidle' });
    
    // Wait for login form
    console.log('👤 Waiting for username field...');
    await page.waitForSelector('input[placeholder*="Employee"], input[name*="username"], input[id*="username"]', { 
        state: 'visible' 
    });
    
    // Fill username
    console.log('📝 Filling username...');
    await page.fill('input[placeholder*="Employee"], input[name*="username"], input[id*="username"]', loginId);
    
    // Fill password
    console.log('🔒 Filling password...');
    await page.fill('input[type="password"]', password);
    
    // Click login button
    console.log('🔑 Clicking login button...');
    
    // Try multiple approaches to find login button
    const loginButtonSelectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("LOGIN")',
        'button.btn-primary',
        '.login-btn',
        '#login-button'
    ];
    
    let loginClicked = false;
    
    for (const selector of loginButtonSelectors) {
        try {
            await page.click(selector);
            console.log(`✅ Clicked login button with selector: ${selector}`);
            loginClicked = true;
            break;
        } catch (error) {
            // Continue to next selector
        }
    }
    
    if (!loginClicked) {
        // Fallback: click any button that contains "login" text
        try {
            await page.click('button:has-text("Login")');
            console.log('✅ Clicked login button using text-based selector');
            loginClicked = true;
        } catch (error) {
            throw new Error('Could not find login button');
        }
    }
    
    // Wait for navigation
    console.log('⏳ Waiting for dashboard...');
    await page.waitForNavigation({ waitUntil: 'networkidle', timeout: 15000 });
    
    console.log('✅ Login successful!');
}

async function handleAttendanceSignIn(page) {
    console.log('📍 Starting attendance sign-in process...');
    
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    try {
        // First, check if already signed in
        const pageContent = await page.textContent('body');
        const alreadySignedIn = pageContent.toLowerCase().includes('already signed in') || 
                               pageContent.toLowerCase().includes('attendance marked') ||
                               pageContent.toLowerCase().includes('check out') ||
                               pageContent.toLowerCase().includes('signed in successfully');
        
        if (alreadySignedIn) {
            console.log('✅ Already signed in for today!');
            return true;
        }
        
        // Look for Sign In button and click it
        console.log('🔍 Looking for Sign In button...');
        
        let signInClicked = false;
        
        // Try different selectors for Sign In button
        const signInSelectors = [
            'button:has-text("Sign In")',
            'button:has-text("Sign in")',
            'button:has-text("SIGN IN")',
            'gt-button:has-text("Sign In")',
            '[role="button"]:has-text("Sign In")'
        ];
        
        for (const selector of signInSelectors) {
            try {
                await page.waitForSelector(selector, { state: 'visible', timeout: 5000 });
                await page.click(selector);
                console.log(`✅ Clicked Sign In button with selector: ${selector}`);
                signInClicked = true;
                break;
            } catch (error) {
                console.log(`⚠️ Selector ${selector} not found, trying next...`);
            }
        }
        
        if (!signInClicked) {
            throw new Error('Could not find or click Sign In button');
        }
        
        // Wait for location modal to appear
        console.log('⏳ Waiting for location modal...');
        await page.waitForTimeout(3000);
        
        // Handle location selection modal
        console.log('🏢 Handling location selection...');
        
        // First, check if modal appeared
        const modalVisible = await page.isVisible('text=Tell us your work location');
        
        if (!modalVisible) {
            console.log('ℹ️ No location modal detected, proceeding...');
        } else {
            console.log('📋 Location modal detected, selecting location...');
            
            try {
                // Method 1: Try to click dropdown and select Office
                const dropdown = page.locator('gt-dropdown, [class*="dropdown"]').first();
                
                if (await dropdown.isVisible()) {
                    console.log('🔽 Found dropdown, clicking to open...');
                    await dropdown.click();
                    
                    // Wait for dropdown options to appear
                    await page.waitForTimeout(1000);
                    
                    // Try to select "Office" option
                    const officeOption = page.locator('text=Office').first();
                    if (await officeOption.isVisible()) {
                        await officeOption.click();
                        console.log('✅ Selected Office option');
                    } else {
                        // If Office not found, select first available option
                        const firstOption = page.locator('[class*="dropdown"] >> nth=0, .dropdown-item >> nth=0').first();
                        if (await firstOption.isVisible()) {
                            await firstOption.click();
                            console.log('✅ Selected first available option');
                        }
                    }
                }
                
            } catch (error) {
                console.log('⚠️ Dropdown method failed, trying direct text selection...');
                
                // Method 2: Direct click on Office text
                try {
                    await page.click('text=Office');
                    console.log('✅ Clicked Office directly');
                } catch (directError) {
                    console.log('⚠️ Direct Office click failed, selecting any available option...');
                    
                    // Method 3: Click on "Select" dropdown and choose first option
                    try {
                        await page.click('text=Select');
                        await page.waitForTimeout(500);
                        
                        // Get all visible clickable elements and try them
                        const options = await page.locator('[class*="option"], [role="option"]').all();
                        if (options.length > 0) {
                            await options[0].click();
                            console.log('✅ Selected first available dropdown option');
                        }
                    } catch (fallbackError) {
                        console.log('⚠️ All location selection methods failed, continuing anyway...');
                    }
                }
            }
            
            // Wait for selection to register
            await page.waitForTimeout(2000);
        }
        
        // Click final Sign In button after location selection
        console.log('🎯 Looking for final Sign In button...');
        
        try {
            // Look for Sign In button in the modal
            const finalSignInButton = page.locator('button:has-text("Sign In"), button:has-text("Submit"), button:has-text("Confirm")').last();
            
            if (await finalSignInButton.isVisible()) {
                await finalSignInButton.click();
                console.log('✅ Clicked final Sign In button');
            } else {
                // Fallback: press Enter key
                await page.keyboard.press('Enter');
                console.log('✅ Pressed Enter as fallback');
            }
        } catch (error) {
            console.log('⚠️ Final Sign In click failed, trying Enter key...');
            await page.keyboard.press('Enter');
        }
        
        // Wait for sign-in process to complete
        console.log('⏳ Waiting for sign-in to complete...');
        await page.waitForTimeout(5000);
        
        // Verify sign-in status
        const finalContent = await page.textContent('body');
        const finalContentLower = finalContent.toLowerCase();
        
        const successIndicators = [
            'signed in successfully',
            'attendance marked',
            'check in successful',
            'already signed in',
            'punch in successful',
            'sign out' // If sign out button is visible, means sign in was successful
        ];
        
        const isSignedIn = successIndicators.some(indicator => 
            finalContentLower.includes(indicator)
        );
        
        if (isSignedIn) {
            console.log('✅ ATTENDANCE SIGN-IN SUCCESSFUL!');
            return true;
        } else {
            // Check if Sign In button is still visible (indicates failure)
            const signInStillVisible = await page.isVisible('button:has-text("Sign In")');
            
            if (!signInStillVisible) {
                console.log('✅ ATTENDANCE SIGN-IN LIKELY SUCCESSFUL (no Sign In button visible)');
                return true;
            } else {
                console.log('❌ ATTENDANCE SIGN-IN FAILED (Sign In button still visible)');
                return false;
            }
        }
        
    } catch (error) {
        console.error(`❌ Error during sign-in process: ${error.message}`);
        throw error;
    }
}

async function saveDebugFiles(page) {
    try {
        console.log('💾 Saving debug files...');
        
        // Save screenshot
        await page.screenshot({ 
            path: 'final_screenshot.png', 
            fullPage: true 
        });
        
        // Save page source
        const pageSource = await page.content();
        fs.writeFileSync('page_source.html', pageSource);
        
        console.log('✅ Debug files saved successfully');
    } catch (error) {
        console.log(`⚠️ Could not save debug files: ${error.message}`);
    }
}

async function main() {
    const debugMode = process.env.DEBUG_MODE === 'true';
    const manualRun = process.env.MANUAL_RUN === 'true';
    
    // Time info
    const now = new Date();
    const istOffset = 5.5 * 60 * 60 * 1000; // IST is UTC+5:30
    const istTime = new Date(now.getTime() + istOffset);
    const isWeekend = now.getUTCDay() === 0 || now.getUTCDay() === 6;
    
    console.log(`🕐 Current time: ${now.toUTCString()} (IST: ${istTime.getHours()}:${istTime.getMinutes().toString().padStart(2, '0')})`);
    console.log(`📅 Is weekend: ${isWeekend}`);
    console.log(`🔧 Manual run: ${manualRun}`);
    console.log(`🐛 Debug mode: ${debugMode}`);
    
    if (manualRun) {
        console.log('🧪 Manual testing mode - will attempt sign-in regardless of time/status');
    }
    
    let browser, context, page;
    
    try {
        // Setup browser
        const browserSetup = await setupBrowser();
        browser = browserSetup.browser;
        context = browserSetup.context;
        page = browserSetup.page;
        
        // Login to GreytHR
        await loginToGreytHR(page);
        
        // Handle attendance sign-in
        const signInSuccess = await handleAttendanceSignIn(page);
        
        // Get final page info
        const currentUrl = page.url();
        const pageTitle = await page.title();
        
        console.log(`🌐 Final URL: ${currentUrl}`);
        console.log(`📄 Page title: ${pageTitle}`);
        
        // Save debug files if needed
        if (debugMode || manualRun || !signInSuccess) {
            await saveDebugFiles(page);
        }
        
        if (signInSuccess) {
            console.log('🎉 GreytHR automation completed successfully!');
            process.exit(0);
        } else {
            console.log('❌ GreytHR automation failed');
            process.exit(1);
        }
        
    } catch (error) {
        console.error(`💥 Automation failed: ${error.message}`);
        
        // Save error screenshot
        if (page) {
            try {
                await page.screenshot({ path: 'error_screenshot.png' });
                console.log('📸 Error screenshot saved');
            } catch (screenshotError) {
                console.log('⚠️ Could not save error screenshot');
            }
        }
        
        process.exit(1);
        
    } finally {
        if (context) {
            await context.close();
        }
        if (browser) {
            await browser.close();
        }
    }
}

// Run the automation
main().catch(error => {
    console.error('💥 Unhandled error:', error);
    process.exit(1);
});