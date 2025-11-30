const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  // Capture console messages
  page.on('console', msg => console.log('CONSOLE:', msg.text()));
  page.on('pageerror', err => console.log('ERROR:', err.message));
  
  await page.goto('http://192.168.112.111:9882/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);
  
  const content = await page.content();
  console.log('\nHTML length:', content.length);
  console.log('Has React root:', content.includes('id="root"'));
  
  await page.screenshot({ path: 'ui-loaded.png' });
  await browser.close();
})();
