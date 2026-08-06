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
page.on('response', async (res) => {
  if (res.url().includes('get_items_by_do_number')) {
    console.log('DO_LOOKUP', res.status());
    try { console.log(JSON.stringify(await res.json())); } catch(e) {}
  }
});

await page.setViewportSize({ width: 1440, height: 900 });
await page.goto('http://bsp.localhost:8002/app/posapp/sales-invoices/new', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(3000);
const closeBtn = page.locator('.modal.show .btn-modal-close, .modal.show [aria-label="Close"]').first();
if (await closeBtn.isVisible().catch(() => false)) {
  await closeBtn.click().catch(() => {});
  await page.waitForTimeout(300);
}

const whVal = await page.evaluate(() => {
  const el = document.querySelector('.sale-opt-warehouse input, .sale-opt-warehouse');
  return el ? (el.value || el.textContent) : 'N/A';
});
console.log('Warehouse shown:', whVal);

const doCard = page.locator('.invoice-section-card', { hasText: 'DO Number' }).first();
const doInput = doCard.locator('input').first();
await doInput.click();
await doInput.fill('LJK41654654JSHF');
await page.waitForTimeout(300);
await doInput.blur();
await page.waitForTimeout(3000);
await page.screenshot({ path: `${shotDir}/wh3-after.png` });
await browser.close();
