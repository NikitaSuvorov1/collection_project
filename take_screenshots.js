const { chromium } = require('playwright');
const path = require('path');
const fs   = require('fs');

const BASE     = 'http://localhost:5173';
const OUT      = 'C:\\project\\collection_app\\screenshots';
const LOGIN    = 'admin';
const PASSWORD = 'admin';

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log('  SAVED:', name + '.png');
}

async function goToPage(page, pageName) {
  await page.evaluate((p) => {
    try {
      const nav = JSON.parse(localStorage.getItem('collection_nav') || '{}');
      nav.page = p;
      localStorage.setItem('collection_nav', JSON.stringify(nav));
    } catch(e) {}
  }, pageName);
  await page.reload({ waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1800);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // ── 1. LoginPage ─────────────────────────────────────────────
  console.log('1/8  LoginPage...');
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(800);
  await shot(page, '01_LoginPage');

  // ── Авторизация ──────────────────────────────────────────────
  const loginField = page.locator('input').first();
  const passField  = page.locator('input[type="password"]').first();
  await loginField.fill(LOGIN);
  await passField.fill(PASSWORD);
  await page.locator('button').filter({ hasText: /войти|login|вход/i }).first().click();
  await page.waitForTimeout(2500);

  // ── 2. CollectionDeskApp ──────────────────────────────────────
  console.log('2/8  CollectionDeskApp...');
  await goToPage(page, 'desk');
  await shot(page, '02_CollectionDeskApp');

  // ── 3. Client360Page ──────────────────────────────────────────
  console.log('3/8  Client360Page...');
  await page.evaluate(() => {
    const nav = JSON.parse(localStorage.getItem('collection_nav') || '{}');
    nav.page = 'client360';
    nav.client360Id = 5001;
    localStorage.setItem('collection_nav', JSON.stringify(nav));
  });
  await page.reload({ waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(3000);
  await shot(page, '03_Client360Page');

  // ── 4. DashboardPage ──────────────────────────────────────────
  console.log('4/8  DashboardPage...');
  // force role to manager temporarily for this screenshot
  await page.evaluate(() => {
    const saved = localStorage.getItem('collection_user');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        parsed.user.role = 'manager';
        parsed.user.is_manager = true;
        localStorage.setItem('collection_user', JSON.stringify(parsed));
      } catch(e) {}
    }
    const nav = JSON.parse(localStorage.getItem('collection_nav') || '{}');
    nav.page = 'dashboard';
    localStorage.setItem('collection_nav', JSON.stringify(nav));
  });
  await page.reload({ waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(3000);
  await shot(page, '04_DashboardPage');

  // ── 5. OperatorStatsPage ──────────────────────────────────────
  console.log('5/8  OperatorStatsPage...');
  await goToPage(page, 'mystats');
  await shot(page, '05_OperatorStatsPage');

  // ── 6. OverduePredictionPage ──────────────────────────────────
  console.log('6/8  OverduePredictionPage...');
  await goToPage(page, 'overdue');
  await shot(page, '06_OverduePredictionPage');

  // ── 7. ModelTrainingPage ──────────────────────────────────────
  console.log('7/8  ModelTrainingPage...');
  await goToPage(page, 'training');
  await shot(page, '07_ModelTrainingPage');

  // ── 8. LoanTrainingPage ───────────────────────────────────────
  console.log('8/8  LoanTrainingPage...');
  await goToPage(page, 'loanTraining');
  await shot(page, '08_LoanTrainingPage');

  await browser.close();
  console.log('\nГотово! Все скриншоты в:', OUT);
})().catch(err => { console.error('ERROR:', err.message); process.exit(1); });
