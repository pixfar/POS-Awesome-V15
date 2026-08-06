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

await page.setViewportSize({ width: 1440, height: 900 });
await page.goto('http://bsp.localhost:8002/app/posapp/sales-invoices/new', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(2200);
const closeBtn = page.locator('.modal.show .btn-modal-close, .modal.show [aria-label="Close"]').first();
if (await closeBtn.isVisible().catch(() => false)) {
  await closeBtn.click().catch(() => {});
  await page.waitForTimeout(300);
}
const whSelect = page.locator('.sale-opt-warehouse').first();
if (await whSelect.isVisible().catch(() => false)) {
  await whSelect.click();
  await page.waitForTimeout(500);
  const option = page.getByText('বি. এস. পি স্টোররুম', { exact: false }).first();
  if (await option.isVisible().catch(() => false)) {
    await option.click();
    await page.waitForTimeout(500);
  }
}
const doCard = page.locator('.invoice-section-card', { hasText: 'DO Number' }).first();
const doInput = doCard.locator('input').first();
await doInput.click();
await doInput.fill('LJK41654654JSHF');
await page.waitForTimeout(300);
await doInput.blur();
await page.waitForTimeout(3000);

const rowHTML = await page.evaluate(() => {
  const rows = Array.from(document.querySelectorAll('.invoice-shell table tbody tr'));
  const row = rows.find(r => r.innerText.includes('SAP7'));
  const row = document.querySelector('.invoice-shell table tbody tr');
  return row ? row.outerHTML.slice(0, 3000) : 'NOROW';
});
console.log(rowHTML);
await browser.close();
