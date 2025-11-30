const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  // Navigate to home
  await page.goto('http://192.168.112.111:9882/');
  console.log('✅ Page loaded');
  
  // Login
  await page.fill('input[type="password"]', 'namastex888');
  await Promise.all([
    page.waitForNavigation({ timeout: 10000 }),
    page.click('button:has-text("Access Dashboard")')
  ]);
  console.log('✅ Logged in');
  
  // Take screenshot of dashboard
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'dashboard-current.png', fullPage: true });
  console.log('✅ Dashboard screenshot saved');
  
  // Check for genie instance
  const text = await page.textContent('body');
  if (text.includes('genie')) {
    console.log('✅ Found genie instance');
  } else {
    console.log('❌ Genie instance not found');
  }
  
  // Check status
  if (text.toLowerCase().includes('connecting')) {
    console.log('📊 Status: Connecting');
  }
  if (text.toLowerCase().includes('open')) {
    console.log('📊 Status: Open');
  }
  
  // Navigate to instances page
  await page.goto('http://192.168.112.111:9882/instances');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'instances-current.png', fullPage: true });
  console.log('✅ Instances page screenshot saved');
  
  await browser.close();
  console.log('\n✅ Screenshots saved: dashboard-current.png, instances-current.png');
})();
