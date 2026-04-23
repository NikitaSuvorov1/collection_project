const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const outDir = path.resolve(__dirname, '..', '..', 'docs', 'screenshots');
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  const FRONTEND = 'http://localhost:5173/';
  console.log('Opening', FRONTEND);
  await page.goto(FRONTEND, { waitUntil: 'networkidle' });
  // Save landing page for debugging
  const landingPath = path.join(outDir, 'landing.png');
  console.log('Saving', landingPath);
  await page.screenshot({ path: landingPath, fullPage: true });

  // Attempt to log in; if SPA login doesn't progress, set localStorage session as fallback
  try {
    const userInput = await page.$('input[type="text"]');
    const passInput = await page.$('input[type="password"]');
    if (userInput) await userInput.fill('admin');
    if (passInput) await passInput.fill('admin');
    await page.click('text=Войти').catch(() => {});
  } catch (e) {
    console.warn('Login form not usable:', e.message);
  }

  // Wait shortly for SPA to update
  await page.waitForTimeout(1200);

  // If login didn't navigate, set localStorage operator as manager and reload
  const isLoggedIn = await page.evaluate(() => !!localStorage.getItem('operator'));
  if (!isLoggedIn) {
    console.log('Setting localStorage operator to manager and reloading to ensure authenticated UI');
    await page.evaluate(() => {
      localStorage.setItem('operator', JSON.stringify({ id: 51, name: 'Администратор', full_name: 'Администратор системы', role: 'manager' }));
    });
    await page.reload({ waitUntil: 'networkidle' });
  }

  // Try clicking the Dashboard button programmatically if present
  try {
    const clicked = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for (const b of btns) {
        const t = b.innerText && b.innerText.trim();
        if (!t) continue;
        if (t.includes('Дашборд')) { b.click(); return 'dashboard'; }
        if (t.includes('Рабочий стол оператора')) { b.click(); return 'workspace'; }
      }
      return null;
    });
    if (clicked) {
      console.log('Clicked', clicked, 'button to reveal UI');
      await page.waitForTimeout(800);
    }
  } catch (e) {
    console.warn('Error clicking nav buttons:', e.message);
  }

  // Wait for dashboard API data to be available (poll up to 60s)
  try {
    console.log('Waiting for /api/dashboard response...');
    const first = await page.waitForResponse(r => r.url().includes('/api/dashboard') && r.status() === 200, { timeout: 30000 }).catch(() => null);
    if (first) {
      let data = await first.json().catch(() => null);
      if (!data || !Array.isArray(data.operatorStats) || data.operatorStats.length === 0) {
        const start = Date.now();
        while (Date.now() - start < 60000) {
          const resp = await page.waitForResponse(r => r.url().includes('/api/dashboard') && r.status() === 200, { timeout: 10000 }).catch(() => null);
          if (!resp) continue;
          data = await resp.json().catch(() => null);
          if (data && Array.isArray(data.operatorStats) && data.operatorStats.length > 0) {
            console.log('Dashboard API returned operatorStats > 0');
            break;
          }
          console.log('Dashboard data present but no operatorStats; continuing to poll...');
        }
      } else {
        console.log('Dashboard API returned initial data');
      }
    } else {
      console.warn('No /api/dashboard response within 30s; continuing');
    }
  } catch (e) {
    console.warn('Error waiting for dashboard API:', e.message);
  }

  // Define app pages to navigate to
  const pages = [
    { key: 'dashboard', label: 'Дашборд', wait: 'text=Дашборд руководителя' },
    { key: 'workspace', label: 'Рабочий стол оператора', wait: 'text=Рабочий стол оператора' },
    { key: 'credits', label: 'Кредиты', wait: 'text=Кредиты' },
    { key: 'overdue', label: 'Просрочка', wait: 'text=Просрочка' },
    { key: 'scoring', label: 'Скоринг' },
    { key: 'database', label: 'База данных' }
  ];

  for (const targetPage of pages) {
    try {
      console.log(`Navigating to ${targetPage.label}...`);
      const clicked = await page.evaluate((label) => {
        // find any button/link with matching text
        const all = Array.from(document.querySelectorAll('button, a'));
        for (const el of all) {
          const txt = (el.innerText || el.textContent || '').trim();
          if (!txt) continue;
          if (txt.includes(label)) { el.click(); return true; }
        }
        return false;
      }, targetPage.label);

      if (clicked) {
        // Wait for page-specific content to appear
        if (targetPage.wait) {
          try {
            await page.waitForSelector(targetPage.wait, { timeout: 8000 });
          } catch (e) {
            console.warn(`  Selector "${targetPage.wait}" not found after click, waiting 1s anyway`);
            await page.waitForTimeout(1000);
          }
        } else {
          await page.waitForTimeout(1500);
        }
        const outPath = path.join(outDir, `${targetPage.key}.png`);
        console.log('Saving', outPath);
        // If capturing workspace, wait for assignments API to load
        if (targetPage.key === 'workspace') {
          try {
            console.log('Waiting for /api/assignments response...');
            await page.waitForResponse(r => r.url().includes('/api/assignments') && r.status() === 200, { timeout: 20000 }).catch(() => null);
            await page.waitForTimeout(600);
          } catch (e) {
            console.warn('Assignments API wait failed:', e.message);
          }
        }
        await page.screenshot({ path: outPath, fullPage: true });
      } else {
        console.warn(`  Button/label not found: ${targetPage.label}`);
      }
    } catch (e) {
      console.warn(`Error capturing ${targetPage.label}:`, e.message);
    }
  }

  // Wait for dashboard or workspace topbar
  await page.waitForTimeout(1200);

  // Capture dashboard (if present)
  try {
    await page.waitForSelector('text=Дашборд руководителя', { timeout: 8000 });
    const dashPath = path.join(outDir, `dashboard.png`);
    console.log('Saving', dashPath);
    await page.screenshot({ path: dashPath, fullPage: true });
  } catch (e) {
    console.warn('Dashboard not detected:', e.message);
  }

  // Switch to operator workspace and capture
  try {
    // Try to open workspace (button may be present for manager view)
    const wsButton = await page.$('text=Рабочий стол оператора');
    if (wsButton) {
      await Promise.all([
        wsButton.click(),
        page.waitForSelector('text=Рабочий стол оператора', { timeout: 8000 }).catch(() => {})
      ]);
      const wsPath = path.join(outDir, 'workspace.png');
      console.log('Saving', wsPath);
      await page.screenshot({ path: wsPath, fullPage: true });

      // Click first client if exists
      const client = await page.$('.client-list-item');
      if (client) {
        await client.click();
        await page.waitForSelector('.detail-card', { timeout: 5000 }).catch(() => {});
        const clientPath = path.join(outDir, 'client_detail.png');
        console.log('Saving', clientPath);
        await page.screenshot({ path: clientPath, fullPage: true });
      } else {
        console.warn('No client list item found to capture detail.');
      }
    } else {
      console.warn('Workspace button not found.');
    }
  } catch (e) {
    console.warn('Error capturing workspace:', e.message);
  }

  await browser.close();
  console.log('Screenshots finished.');
})().catch(err => { console.error(err); process.exit(1); });
