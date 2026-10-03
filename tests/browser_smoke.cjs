/* Real-browser checks against published data, without network price fixtures. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '../web');
const out = path.resolve(__dirname, '../test-results');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'latest.json')));
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
      const navigate = async route => {
        if (name === 'mobile') await page.locator('#menuButton').click();
        await page.locator(`.sidebar-nav button[data-tab="${route}"]`).click();
      };
      await page.screenshot({path:path.join(out, `${name}-today.png`), fullPage:true});
      let stockFlow = 'unavailable';
      if (snapshot.tickers.length) {
        const stock = snapshot.tickers.find(x => x.ticker === 'NVDA') || snapshot.tickers[0];
        await navigate('screenerpro');
        await page.locator('#resetScreen').click();
        await page.locator('#proQuery').fill(stock.ticker);
        await page.locator('[data-mode="table"]').click();
        assert.equal(await page.locator(`#proResults [data-stock="${stock.ticker}"]`).count(), 1, `${name}: real stock filter`);
        await page.locator(`#proResults [data-stock="${stock.ticker}"]`).click();
        assert.equal(await page.locator('#quickView').isVisible(), true, `${name}: quick view opens`);
        const quick = await page.locator('#quickContent').textContent();
        assert(quick.includes(stock.price.as_of), `${name}: quote date visible`);
        assert(quick.includes(stock.price.source), `${name}: actual quote source visible`);
        await page.locator('#fullResearchButton').click();
        assert.equal(await page.locator('#unifiedTicker').inputValue(), stock.ticker, `${name}: selected stock reaches research`);
        await page.locator('[data-research="Chart"]').click();
        assert.equal(await page.locator('#unifiedBody canvas').isVisible(), true, `${name}: real stock chart`);
        await page.screenshot({path:path.join(out, `${name}-stock-research.png`), fullPage:true});
        await navigate('screenerpro');
        const csvPromise = page.waitForEvent('download');
        await page.locator('#exportScreen').click();
        const csvFile = path.join(out, `${name}-stock.csv`);
        await (await csvPromise).saveAs(csvFile);
        const stockCSV = fs.readFileSync(csvFile, 'utf8');
        assert(stockCSV.includes(stock.ticker) && stockCSV.includes(String(stock.price.close)), `${name}: filtered stock CSV contains verified quote`);
        await page.locator('#resetScreen').click();
        stockFlow = 'passed';
      }
      const funds = Object.entries(snapshot.macro_v9?.commodities?.etfs || {}).filter(([,x]) => x.value != null);
      if (funds.length) {
        await navigate('commodities');
        assert.equal(await page.locator('#commodityFunds [data-history]').count(), Object.keys(snapshot.macro_v9.commodities.etfs).length, `${name}: commodity fund cards`);
        const [id, fund] = funds[0];
        const card = page.locator(`#commodityFunds [data-history="${id}"]`);
        assert((await card.textContent()).includes('$/share'), `${name}: fund units stay separate from futures`);
        assert((await card.textContent()).includes(fund.date), `${name}: fund observation date`);
        await page.screenshot({path:path.join(out, `${name}-commodity-funds.png`), fullPage:true});
        await card.click();
        await page.waitForFunction(id => document.querySelector('#historySeries').value === id && document.querySelector('#historyRows').children.length > 0, id);
        assert.equal(await page.locator('#historyexplorer').isVisible(), true, `${name}: fund history opens`);
      }
      const routes = await page.locator('.sidebar-nav button').evaluateAll(bs => bs.map(b => b.dataset.tab));
      for (const route of routes) {
        await navigate(route);
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
      const expected = JSON.parse(fs.readFileSync(path.join(root,'history/fred/DGS10.json'))).history;
      await page.waitForFunction(total => document.querySelector('#historyPager').textContent.includes(total.toLocaleString()),expected.length);
      const rows = await page.locator('#historyRows tr').count();
      assert.equal(rows, 200, `${name}: history table uses bounded pages`);
      assert((await page.locator('#historyRows').textContent()).includes(expected.at(-1).date),`${name}: newest observation loads`);
      await page.locator('[data-history-page="last"]').click();
      assert((await page.locator('#historyRows').textContent()).includes(expected[0].date),`${name}: oldest observation remains accessible`);
      const exportPromise = page.waitForEvent('download');
      await page.locator('#historyExportButton').click();
      const exported = await exportPromise;
      const exportPath = path.join(out,`${name}-history.csv`);
      await exported.saveAs(exportPath);
      const csv = fs.readFileSync(exportPath,'utf8');
      assert.equal(csv.split('\r\n').length,expected.length+1,`${name}: CSV must export all selected observations`);
      assert(csv.includes(expected[0].date)&&csv.includes(expected.at(-1).date),`${name}: CSV retains both history endpoints`);
      assert.deepEqual(errors, [], `${name}: JavaScript runtime errors`);
      const overflow = await page.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
      assert(overflow.content <= overflow.viewport + 1, `${name}: page-wide overflow ${JSON.stringify(overflow)}`);
      report.push({viewport:name, routes:routes.length, verifiedStocks:snapshot.tickers.length,stockFlow,commodityFunds:funds.length,renderedHistoryRows:rows, availableHistoryRows:expected.length,fullCSVExport:'passed',runtimeErrors:errors, overflow, status:'passed'});
      await page.close();
    }
    fs.writeFileSync(path.join(out,'browser-report.json'), JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); server.close(); }
})().catch(e => {console.error(e); server.close(); process.exitCode=1;});
