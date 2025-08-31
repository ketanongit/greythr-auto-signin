const puppeteer = require('puppeteer');

async function setupBrowser() {
    console.log('🚀 Setting up browser...');
    
    const browser = await puppeteer.launch({
        headless: true,
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
    
    // Click login button
    console.log('🔑 Clicking login button...');
    await page.click('button:has-text("Login"), button:has-text("LOGIN"), input[value*="Login"]');
    
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
        
        const signInResult = await page.evaluate(() => {
            // Find Sign In button using multiple strategies
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
        
        if (!signInResult.success) {
            throw new Error(signInResult.error);
        }
        
        console.log(`✅ Clicked Sign In button: "${signInResult.buttonText}"`);
        
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
                const dropdownButton = dropdown.querySelector('button, [role="button"]');
                if (dropdownButton) {
                    dropdownButton.click();
                    results.push('Clicked dropdown button');
                    
                    // Wait a moment for options to appear
                    setTimeout(() => {
                        // Look for Office option in dropdown body
                        const dropdownBody = dropdown.querySelector('.dropdown-body, .dropdown-container');
                        if (dropdownBody) {
                            const officeOption = Array.from(dropdownBody.querySelectorAll('div, li, [role="option"]'))
                                .find(el => el.textContent.trim() === 'Office');
                            
                            if (officeOption) {
                                officeOption.click();
                                results.push('Selected Office from dropdown');
                            } else {
                                // Select first available option
                                const firstOption = dropdownBody.querySelector('div[class*="item"], li, [role="option"]');
                                if (firstOption) {
                                    firstOption.click();
                                    results.push('Selected first available option');
                                }
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
            }, 1500);
            
            // Strategy 3: Click any visible Sign In button after location selection
            setTimeout(() => {
                const signInButtons = Array.from(document.querySelectorAll('button, gt-button'))
                    .filter(btn => {
                        const text = btn.innerText || btn.textContent || '';
                        const isVisible = btn.offsetParent !== null;
                        return isVisible && (text.includes('Sign In') || text.includes('Submit'));
                    });
                
                if (signInButtons.length > 0) {
                    signInButtons[0].click();
                    results.push('Clicked final Sign In button');
                }
            }, 3000);
            
            return { success: true, message: results.join(' | ') };
            
        }, process.env.SIGNIN_LOCATION || 'Office');
        
        console.log(`📋 Location handling: ${locationResult.message}`);
        
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
            
            // One final attempt
            console.log('🔄 Making final attempt...');
            
            await page.evaluate(() => {
                // Aggressive final attempt - click any button that might be related
                const allButtons = document.querySelectorAll('button, gt-button, [role="button"]');
                
                for (const btn of allButtons) {
                    const text = btn.innerText || btn.textContent || '';
                    const isVisible = btn.offsetParent !== null;
                    
                    if (isVisible && (text.includes('Sign') || text.includes('Mark') || text.includes('Check') || text.includes('Punch'))) {
                        console.log('Final attempt clicking:', text);
                        btn.click();
                        
                        // If this opens a modal, try to handle it
                        setTimeout(() => {
                            // Look for Office option
                            const officeElements = Array.from(document.querySelectorAll('*'))
                                .filter(el => el.textContent.trim() === 'Office' && el.offsetParent !== null);
                            
                            if (officeElements.length > 0) {
                                officeElements[0].click();
                                
                                // Then click final submit
                                setTimeout(() => {
                                    const submitButtons = Array.from(document.querySelectorAll('button, gt-button'))
                                        .filter(btn => {
                                            const text = btn.innerText || btn.textContent || '';
                                            const isVisible = btn.offsetParent !== null;
                                            return isVisible && (text.includes('Sign') || text.includes('Submit'));
                                        });
                                    
                                    if (submitButtons.length > 0) {
                                        submitButtons[0].click();
                                    }
                                }, 1000);
                            }
                        }, 2000);
                        break;
                    }
                }
            });
            
            await page.waitForTimeout(6000);
            
            // Final verification
            const ultimateStatus = await page.evaluate(() => {
                const pageText = document.body.innerText.toLowerCase();
                return pageText.includes('signed in') || 
                       pageText.includes('marked') || 
                       pageText.includes('successful') ||
                       !Array.from(document.querySelectorAll('*'))
                           .some(el => (el.innerText || '').toLowerCase().includes('sign in') && el.offsetParent !== null);
            });
            
            if (ultimateStatus) {
                console.log('✅ FINAL ATTEMPT SUCCESSFUL!');
                return true;
            } else {
                console.log('❌ ALL ATTEMPTS FAILED');
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
