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
 await new Promise(r=>setTimeout(r,80));assert.deepStrictEqual(errors,[],`runtime errors (${fixture?'fixture':'live'})`);const routeCount=w.document.querySelectorAll('.sidebar-nav button').length;dom.window.close();
 return {scenario:demoResponse?'demo rejected':failFetch?'503 fallback':fixture?'fixture interactions':'real snapshot',routes:routeCount,status:'passed'};
}
(async()=>{let report=[];for(const args of [[false,false],[true,false],[false,true],[false,false,true]])report.push(await run(...args));console.log(JSON.stringify({kind:'DOM contract; visual layout unverified',results:report}));})().catch(e=>{console.error(e);process.exit(1)});
