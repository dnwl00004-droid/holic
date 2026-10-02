/* Real-browser checks against published data, without network price fixtures. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '../web');
const out = path.resolve(__dirname, '../test-results');
fs.mkdirSync(out, {recursive: true});
const server = http.createServer((req, res) => {
  const relative = decodeURIComponent(new URL(req.url, 'http://localhost').pathname).replace(/^\/+/, '') || 'index.html';
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404); return res.end();
  }
  const types = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml'};
  res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless: true});
  const report = [];
  try {
    for (const [name, viewport] of [['desktop', {width:1440,height:1000}], ['mobile', {width:390,height:844}]]) {
      const page = await browser.newPage({viewport});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(url, {waitUntil:'networkidle'});
      await page.waitForFunction(() => document.querySelectorAll('.sidebar-nav button').length >= 45);
      await page.screenshot({path:path.join(out, `${name}-today.png`), fullPage:true});
      const routes = await page.locator('.sidebar-nav button').evaluateAll(bs => bs.map(b => b.dataset.tab));
      for (const route of routes) {
        if (name === 'mobile') await page.locator('#menuButton').click();
        await page.locator(`.sidebar-nav button[data-tab="${route}"]`).click();
        await page.waitForTimeout(80);
        assert.equal(await page.locator('.view.active').count(), 1, `${name}: ${route} active screen`);
        assert.equal(await page.locator(`#${route}`).evaluate(e => e.classList.contains('active')), true, `${route} navigation`);
        if (['ratesfocus','calendar','historyexplorer','datahealth'].includes(route)) {
          await page.screenshot({path:path.join(out, `${name}-${route}.png`), fullPage:true});
        }
      }
      if (name === 'mobile') await page.locator('#menuButton').click();
      await page.locator('.sidebar-nav button[data-tab="historyexplorer"]').click();
      await page.locator('#historySeries').selectOption('DGS10');
      await page.waitForFunction(() => document.querySelector('#historyRows').children.length > 0);
      await page.locator('#historyRanges button[data-range="MAX"]').click();
      const rows = await page.locator('#historyRows tr').count();
      assert(rows > 0, `${name}: history loads`);
      assert.deepEqual(errors, [], `${name}: JavaScript runtime errors`);
      const overflow = await page.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
      assert(overflow.content <= overflow.viewport + 1, `${name}: page-wide overflow ${JSON.stringify(overflow)}`);
      report.push({viewport:name, routes:routes.length, historyRows:rows, runtimeErrors:errors, overflow, status:'passed'});
      await page.close();
    }
    fs.writeFileSync(path.join(out,'browser-report.json'), JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); server.close(); }
})().catch(e => {console.error(e); server.close(); process.exitCode=1;});
