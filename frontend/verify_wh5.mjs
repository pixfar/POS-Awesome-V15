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
const calls = [];
page.on('request', (req) => {
  const url = req.url();
  if (url.includes('api.items.get_items') && !url.includes('get_items_groups') && !url.includes('get_items_count') && !url.includes('get_items_details')) {
    calls.push({ url, postData: req.postData() });
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

calls.forEach((c, i) => {
  const post = c.postData || '';
  const match = post.match(/pos_profile=([^&]*)/);
  console.log(`call ${i}: postData length=${post.length}`);
  // find "warehouse" inside the pos_profile JSON blob
  const wh = post.match(/%22warehouse%22%3A%22([^%"]*(%[0-9A-F]{2})*)/i);
  console.log('  raw snippet around warehouse:', post.indexOf('warehouse') >=0 ? post.slice(post.indexOf('warehouse')-5, post.indexOf('warehouse')+80) : 'not found');
});
await browser.close();
