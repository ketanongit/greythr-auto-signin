const puppeteer = require('puppeteer');

async function setupBrowser() {
    console.log('🚀 Setting up browser...');
    
    const browser = await puppeteer.launch({
        headless: "new", // Use new headless mode
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-features=VizDisplayCompositor'
        ]
    });
    
    const page = await browser.newPage();
    
    // Set viewport and user agent
    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');
    
    // Set longer timeout
    page.setDefaultTimeout(30000);
    page.setDefaultNavigationTimeout(30000);
    
    return { browser, page };
}

async function loginToGreytHR(page) {
    const url = process.env.LOGIN_URL;
    const loginId = process.env.LOGIN_ID;
    const password = process.env.LOGIN_PASSWORD;
    
    console.log(`🌐 Navigating to ${url}`);
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    // Wait for login form
    console.log('👤 Waiting for username field...');
    await page.waitForSelector('input[placeholder*="Employee"], input[name*="username"], input[id*="username"]', { visible: true });
    
    // Fill username
    console.log('📝 Filling username...');
    await page.type('input[placeholder*="Employee"], input[name*="username"], input[id*="username"]', loginId);
    
    // Fill password
    console.log('🔒 Filling password...');
    await page.type('input[type="password"]', password);
    
    // Click login button using XPath for text matching
    console.log('🔑 Clicking login button...');
    
    // Try multiple approaches to find login button
    let loginClicked = false;
    
    // Approach 1: Try common button selectors
    const buttonSelectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button.btn-primary',
        '.login-btn',
        '#login-button'
    ];
    
    for (const selector of buttonSelectors) {
        try {
            await page.click(selector);
            console.log(`✅ Clicked login button with selector: ${selector}`);
            loginClicked = true;
            break;
        } catch (error) {
            // Continue to next selector
        }
    }
    
    // Approach 2: Use XPath for text-based selection
    if (!loginClicked) {
        try {
            const loginButtonXPath = '//button[contains(text(), "Login") or contains(text(), "LOGIN") or contains(@value, "Login")]';
            await page.waitForXPath(loginButtonXPath, { visible: true });
            const [loginButton] = await page.$x(loginButtonXPath);
            if (loginButton) {
                await loginButton.click();
                console.log('✅ Clicked login button using XPath');
                loginClicked = true;
            }
        } catch (error) {
            console.log('⚠️ XPath login button not found');
        }
    }
    
    // Approach 3: JavaScript execution as fallback
    if (!loginClicked) {
        await page.evaluate(() => {
            const buttons = document.querySelectorAll('button, input[type="submit"]');
            for (const btn of buttons) {
                const text = btn.textContent || btn.value || btn.innerText || '';
                if (text.toLowerCase().includes('login') || btn.type === 'submit') {
                    btn.click();
                    console.log('Clicked login button via JavaScript:', text);
                    return;
                }
            }
        });
        console.log('✅ Clicked login button using JavaScript fallback');
    }
    
    // Wait for navigation
    console.log('⏳ Waiting for dashboard...');
    await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 });
    
    console.log('✅ Login successful!');
}

async function handleAttendanceSignIn(page) {
    console.log('📍 Starting attendance sign-in process...');
    
    // Wait a bit for page to fully load
    await page.waitForTimeout(3000);
    
    try {
        // First, check if already signed in
        const alreadySignedIn = await page.evaluate(() => {
            const pageText = document.body.innerText.toLowerCase();
            return pageText.includes('already signed in') || 
                   pageText.includes('attendance marked') ||
                   pageText.includes('check out') ||
                   pageText.includes('signed in successfully');
        });
        
        if (alreadySignedIn) {
            console.log('✅ Already signed in for today!');
            return true;
        }
        
        // Look for Sign In button and click it
        console.log('🔍 Looking for Sign In button...');
        
        let signInClicked = false;
        
        // Approach 1: Try XPath for Sign In button
        try {
            const signInXPath = '//button[contains(text(), "Sign In") or contains(text(), "Sign in") or contains(text(), "SIGN IN")]';
            await page.waitForXPath(signInXPath, { visible: true, timeout: 10000 });
            const [signInButton] = await page.$x(signInXPath);
            if (signInButton) {
                await signInButton.click();
                console.log('✅ Clicked Sign In button using XPath');
                signInClicked = true;
            }
        } catch (error) {
            console.log('⚠️ XPath Sign In button not found, trying other methods...');
        }
        
        // Approach 2: JavaScript-based button finding
        if (!signInClicked) {
            const signInResult = await page.evaluate(() => {
                const buttons = document.querySelectorAll('button, gt-button, [role="button"]');
                
                for (const btn of buttons) {
                    const text = btn.innerText || btn.textContent || '';
                    const isVisible = btn.offsetParent !== null;
                    
                    if (isVisible && text.toLowerCase().includes('sign in')) {
                        console.log('Found Sign In button:', text);
                        btn.click();
                        return { success: true, buttonText: text };
                    }
                }
                return { success: false, error: 'No Sign In button found' };
            });
            
            if (signInResult.success) {
                console.log(`✅ Clicked Sign In button: "${signInResult.buttonText}"`);
                signInClicked = true;
            }
        }
        
        if (!signInClicked) {
            throw new Error('Could not find or click Sign In button');
        }
        
        // Wait for location modal to appear
        await page.waitForTimeout(3000);
        
        // Handle location selection modal
        console.log('🏢 Handling location selection...');
        
        const locationResult = await page.evaluate((signinLocation) => {
            const results = [];
            
            // Check if modal is present
            const modalTexts = Array.from(document.querySelectorAll('*'))
                .some(el => el.textContent && el.textContent.includes('Tell us your work location'));
            
            if (!modalTexts) {
                return { success: true, message: 'No location modal detected' };
            }
            
            results.push('Location modal detected');
            
            // Strategy 1: Find and click the gt-dropdown
            const dropdown = document.querySelector('gt-dropdown');
            if (dropdown) {
                results.push('Found gt-dropdown element');
                
                // Try to click the dropdown button
                const dropdownButton = dropdown.querySelector('button, [role="button"], .dropdown-button');
                if (dropdownButton) {
                    dropdownButton.click();
                    results.push('Clicked dropdown button');
                    
                    // Wait for dropdown to open and then select option
                    setTimeout(() => {
                        // Look for Office option in dropdown body
                        const dropdownItems = dropdown.querySelectorAll('.dropdown-item, [class*="item"], div[class*="dropdown"]');
                        
                        for (const item of dropdownItems) {
                            const itemText = item.textContent || item.innerText || '';
                            if (itemText.trim() === 'Office') {
                                item.click();
                                results.push('Selected Office from dropdown');
                                return;
                            }
                        }
                        
                        // If Office not found, try first visible option
                        for (const item of dropdownItems) {
                            if (item.offsetParent !== null) {
                                item.click();
                                results.push('Selected first available option: ' + (item.textContent || '').trim());
                                return;
                            }
                        }
                    }, 1000);
                }
            }
            
            // Strategy 2: Direct text-based clicking
            setTimeout(() => {
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const text = el.textContent || el.innerText || '';
                    if (text.trim() === 'Office' && el.offsetParent !== null) {
                        results.push('Found Office text element, clicking directly');
                        el.click();
                        break;
                    }
                }
            }, 2000);
            
            return { success: true, message: results.join(' | ') };
            
        }, process.env.SIGNIN_LOCATION || 'Office');
        
        console.log(`📋 Location handling: ${locationResult.message}`);
        
        // Wait for location selection to complete
        await page.waitForTimeout(4000);
        
        // Click final Sign In button after location selection
        console.log('🎯 Looking for final Sign In button after location selection...');
        
        try {
            // Try XPath first
            const finalSignInXPath = '//button[contains(text(), "Sign In") or contains(text(), "Sign in")]';
            const [finalSignInButton] = await page.$x(finalSignInXPath);
            if (finalSignInButton) {
                await finalSignInButton.click();
                console.log('✅ Clicked final Sign In button using XPath');
            }
        } catch (error) {
            // JavaScript fallback
            await page.evaluate(() => {
                const buttons = document.querySelectorAll('button, gt-button');
                for (const btn of buttons) {
                    const text = btn.innerText || btn.textContent || '';
                    const isVisible = btn.offsetParent !== null;
                    if (isVisible && (text.includes('Sign In') || text.includes('Submit') || text.includes('Confirm'))) {
                        console.log('Clicking final button:', text);
                        btn.click();
                        break;
                    }
                }
            });
            console.log('✅ Clicked final Sign In button using JavaScript');
        }
        
        // Wait for sign-in process to complete
        await page.waitForTimeout(5000);
        
        // Verify sign-in status
        const finalStatus = await page.evaluate(() => {
            const pageText = document.body.innerText.toLowerCase();
            
            // Check for success indicators
            const successIndicators = [
                'signed in successfully',
                'attendance marked',
                'check in successful',
                'already signed in',
                'punch in successful'
            ];
            
            for (const indicator of successIndicators) {
                if (pageText.includes(indicator)) {
                    return { signedIn: true, indicator };
                }
            }
            
            // Check if Sign In button is still visible (indicates failure)
            const signInButtons = Array.from(document.querySelectorAll('button, gt-button'))
                .filter(btn => {
                    const text = btn.innerText || btn.textContent || '';
                    const isVisible = btn.offsetParent !== null;
                    return isVisible && text.toLowerCase().includes('sign in');
                });
            
            if (signInButtons.length > 0) {
                return { signedIn: false, reason: 'Sign In button still visible' };
            }
            
            return { signedIn: true, reason: 'No Sign In button visible, assuming success' };
        });
        
        if (finalStatus.signedIn) {
            console.log(`✅ ATTENDANCE SIGN-IN SUCCESSFUL! ${finalStatus.indicator || finalStatus.reason}`);
            return true;
        } else {
            console.log(`❌ ATTENDANCE SIGN-IN FAILED: ${finalStatus.reason}`);
            return false;
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
        require('fs').writeFileSync('page_source.html', pageSource);
        
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
    
    let browser, page;
    
    try {
        // Setup browser
        const browserSetup = await setupBrowser();
        browser = browserSetup.browser;
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
