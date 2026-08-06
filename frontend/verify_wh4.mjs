import { chromium } from 'playwright';
import fs from 'fs';
const shotDir = '/tmp/claude-1000/-workspace-development/d806f49c-0751-4a12-99a7-44437766f146/scratchpad/pw';
const mockBody = fs.readFileSync(`${shotDir}/shift_mock.json`, 'utf-8');
const browser = await chromium.launch({ args: ['--no-sandbox'] });
const context = await browser.newContext({ storageState: `${shotDir}/state.json` });
await context.route('**/api/method/*check_opening_shift*', async (route) => {
  await route.fulfill({ status: 200, contentType: 'application/json', body: mockBody });
});
const page = await context.newPage();
const getItemsCalls = [];
page.on('request', (req) => {
  const url = req.url();
  if (url.includes('get_items') && !url.includes('get_items_groups') && !url.includes('get_items_count') && !url.includes('get_items_details') && !url.includes('get_items_by_do_number')) {
    getItemsCalls.push(url);
  }
});

await page.setViewportSize({ width: 1440, height: 900 });
await page.goto('http://bsp.localhost:8002/app/posapp/sales-invoices/new', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(3500);
const closeBtn = page.locator('.modal.show .btn-modal-close, .modal.show [aria-label="Close"]').first();
if (await closeBtn.isVisible().catch(() => false)) {
  await closeBtn.click().catch(() => {});
  await page.waitForTimeout(300);
}

console.log('get_items calls made on load:', getItemsCalls.length);
getItemsCalls.forEach((u) => {
  const params = new URLSearchParams(u.split('?')[1] || '');
  console.log('  warehouse param present:', params.has('warehouse'), 'raw url tail:', u.slice(-150));
});

// check what warehouse SAP7's card currently shows
const cardText = await page.evaluate(() => {
  const cards = Array.from(document.querySelectorAll('.v-card--flat')).filter(c => {
    const t = c.innerText || '';
    return t.includes('SAP7') && t.includes('In Stock') && t.length < 200;
  });
  return cards.map(c => c.innerText.replace(/\n/g, ' | '));
});
console.log('SAP7 card(s):', JSON.stringify(cardText));
await browser.close();
