/* DOM contract tests, not visual/layout tests. Fixtures never enter published data. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'../web');
async function run(fixture=false,failFetch=false,demoResponse=false){
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));vc.on('error',(...a)=>errors.push(a.map(x=>x?.stack||String(x)).join(' ')));
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://localhost/',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc});
 const w=dom.window;w.addEventListener('error',e=>errors.push(e.message));w.structuredClone=structuredClone;w.fetch=async p=>{
  if(failFetch&&p==='latest.json')return {ok:false,status:503,json:async()=>{throw Error('503')}};
  if(demoResponse&&p==='latest.json')return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,'../examples/demo-latest.json')))};
  if(fixture&&p==='latest.json'){let d=JSON.parse(fs.readFileSync(path.join(root,'../examples/demo-latest.json')));d.meta.demo=false;d.meta.status='fixture-only';return {ok:true,json:async()=>d}}
  try{let d=JSON.parse(fs.readFileSync(path.join(root,p)));return {ok:true,status:200,json:async()=>d}}catch{return {ok:false,status:404,json:async()=>{throw Error('404')}}}
 };
 w.HTMLCanvasElement.prototype.getContext=()=>new Proxy({},{get:()=>()=>{}});
 const source=w.document.createElement('script');source.textContent=fs.readFileSync(path.join(root,'app.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'terminal.js'),'utf8');w.document.body.append(source);
 await new Promise(r=>setTimeout(r,80));
 const eventClock=w.eval("currentCalendar({events:[{date:'2026-10-02',datetime_utc:'2026-10-02T12:30:00Z',days_from_today:1,importance:'HIGH'}]},new Date('2026-10-02T07:00:00Z'))");
 assert.equal(eventClock.events[0].days_from_today,0,'cached calendar countdown must use current ET date');
 assert.equal(eventClock.high_impact_next_7d,1,'unreleased event must count');
 const afterRelease=w.eval("currentCalendar({events:[{date:'2026-10-02',datetime_utc:'2026-10-02T12:30:00Z',days_from_today:1,importance:'HIGH'}]},new Date('2026-10-02T13:00:00Z'))");
 assert.equal(afterRelease.high_impact_next_7d,0,'released event must leave upcoming risk');
 const etMidnight=w.eval("currentCalendar({events:[{date:'2026-10-02',importance:'HIGH'}]},new Date('2026-10-02T02:00:00Z'))");
 assert.equal(etMidnight.events[0].days_from_today,1,'countdown must respect ET, not UTC midnight');
 const aligned=w.eval("alignHistoryComparison([{date:'2025-01-01',value:10},{date:'2025-01-02',value:11}],[{date:'2025-01-02',value:100},{date:'2025-01-03',value:120}])");
 assert.equal(aligned.primary.length,1,'comparison must use shared dates');assert.equal(aligned.primary[0].date,aligned.overlay[0].date,'comparison baselines must align');
 assert(w.document.querySelectorAll('.sidebar-nav button').length>=45,'navigation missing: '+errors.join(' | '));
 for(const b of w.document.querySelectorAll('.sidebar-nav button')){b.click();await new Promise(r=>setTimeout(r,5));assert(w.document.querySelectorAll('.view.active').length===1,'incorrect active view');assert(w.document.getElementById(b.dataset.tab),'missing view '+b.dataset.tab)}
 if(fixture){
  w.eval("activate('screenerpro');SCREEN.query='NVDA';renderPro()");assert(w.document.querySelectorAll('#proResults tbody tr').length===1,'ticker filter failed');
  w.eval("SCREEN.query='';SCREEN.field='quality';SCREEN.min=101;renderPro()");assert(w.document.querySelector('#proResults').textContent.includes('No matching'),'range filter failed');
  w.eval("SCREEN.min='';SCREEN.view='heatmap';renderPro()");assert(w.document.querySelectorAll('.pro-heatmap button').length>0,'heatmap missing');
  w.eval("openQuick('NVDA')");assert(!w.document.querySelector('#quickView').hidden,'quick view missing');w.document.querySelector('#fullResearchButton').click();assert(w.document.querySelector('#stockresearch').classList.contains('active'),'research navigation failed');
  w.eval("RESEARCH_TAB='Short';renderUnified()");assert(w.document.querySelector('#unifiedBody').textContent.includes('not short interest'),'short data caveat missing');
  w.eval("activate('screenerpro');SCREEN.view='table';renderPro()");w.document.querySelector('#savedName').value='test-screen';w.document.querySelector('#saveScreen').click();assert(w.localStorage.getItem('rs_saved_screens').includes('test-screen'),'saved screen missing');
 }
 if(failFetch||demoResponse){assert(!w.document.querySelector('.demo-banner'),'silent demo fallback');assert.strictEqual(w.eval('DATA.tickers.length'),0,'unverified stocks must not appear')}
 if(!fixture&&!failFetch&&!demoResponse){
  const archive=w.eval('HISTORY_CAL'),currentYear=w.eval("new Intl.DateTimeFormat('en',{timeZone:'America/New_York',year:'numeric'}).format(new Date())");
  assert.equal(w.document.querySelector('#archiveYear').value,currentYear,'archive must prefer the current year over future schedules');
  const archiveYears=archive.events.map(e=>e.date.slice(0,4)).sort();
  assert(w.document.querySelector('#archiveSummary').textContent.includes(archiveYears.at(-1)),'schedule coverage must include the actual final year');
  w.eval("$('#archiveYear').value='ALL';renderArchive()");
  assert.equal(w.document.querySelectorAll('#archiveEvents .archive-row').length,archive.events.length,'All years must show every saved schedule');
  w.eval('initArchiveControls()');
  const history=JSON.parse(fs.readFileSync(path.join(root,'history/fred/DGS10.json'))).history;
  w.eval("renderHistoryRows(HISTORY_CACHE.DGS10?.history||[],{unit:'%'})");
  w.eval(`renderHistoryRows(${JSON.stringify(history)},{unit:'%'})`);
  assert.equal(w.document.querySelectorAll('#historyRows tr').length,200,'MAX table must keep a bounded DOM');
  assert(w.document.querySelector('#historyRows').textContent.includes(history.at(-1).date),'first page must show newest observations');
  w.document.querySelector('[data-history-page="last"]').click();
  assert(w.document.querySelector('#historyRows').textContent.includes(history[0].date),'oldest observations must remain accessible');
  w.document.querySelector('#historyPageNumber').value='2';w.document.querySelector('#historyPageNumber').dispatchEvent(new w.Event('change'));
  assert(w.document.querySelector('#historyRows').textContent.includes(history.at(-201).date),'page jump must use the correct offset');
  w.eval("HISTORY_CACHE.DGS10={source:'FRED',history:[{date:'2025-01-01',value:true}]} ");
  assert.equal(await w.eval("fetchHistoryItem('DGS10')"),null,'boolean observations must be rejected');
  const fetch=w.fetch;w.fetch=async p=>String(p).includes('DGS10.json')?{ok:false,status:503}:fetch(p);
  w.document.querySelector('#historySeries').value='DGS10';await w.eval('loadHistorySelected()');
  assert.equal(w.document.querySelector('#historyRows').children.length,0,'failed history must not retain previous table');
  assert.equal(w.document.querySelector('#historyLatest').textContent,'N/A','failed history must not show prior value');w.fetch=fetch;
 }
 await new Promise(r=>setTimeout(r,80));assert.deepStrictEqual(errors,[],`runtime errors (${fixture?'fixture':'live'})`);const routeCount=w.document.querySelectorAll('.sidebar-nav button').length;dom.window.close();
 return {scenario:demoResponse?'demo rejected':failFetch?'503 fallback':fixture?'fixture interactions':'real snapshot',routes:routeCount,status:'passed'};
}
(async()=>{let report=[];for(const args of [[false,false],[true,false],[false,true],[false,false,true]])report.push(await run(...args));console.log(JSON.stringify({kind:'DOM contract; visual layout unverified',results:report}));})().catch(e=>{console.error(e);process.exit(1)});
