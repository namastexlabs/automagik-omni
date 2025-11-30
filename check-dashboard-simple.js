const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  await page.goto('http://192.168.112.111:9882/');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'ui-homepage.png', fullPage: true });
  console.log('Screenshot saved: ui-homepage.png');
  
  const text = await page.textContent('body');
  console.log('\nPage content check:');
  console.log('- Has "genie":', text.includes('genie'));
  console.log('- Has "Dashboard":', text.includes('Dashboard'));
  console.log('- Has "Login":', text.includes('Enter your API key'));
  
  await browser.close();
})();
