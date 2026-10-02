
let DATA=null, filtered=[], selected=null;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];

async function load(){
 try{let r=await fetch("latest.json",{cache:"no-store"});if(!r.ok)throw 0;DATA=await r.json();if(DATA.meta?.demo||/demo/i.test(DATA.source||'')||!Array.isArray(DATA.tickers)||!DATA.market)throw Error('Unverified snapshot')}
 catch(e){DATA={meta:{demo:false,status:"unavailable",load_error:"latest.json unavailable"},market:{regime:"Unavailable",breadth:{},quality:{}},tickers:[],groups:[],sources:{},macro_v8:{},macro_v9:{},signal_backtests:{}}}
 init();
}
function init(){
 renderMarket(); initFilters(); renderList(); renderMarketHealth(); renderMacroFull(); renderCommodities(); initCalendar(); initHistoryExplorer(); renderGroups(); initIntelligence(); initResearch(); renderRanks(); initReplay(); initMonitor(); renderToday(); renderSetups(); initCompare(); initScreenLab(); initGlobalCommand(); renderDataFreshness();
 setTimeout(()=>{renderV11FocusTabs();renderDataHealth()},0);
 selected=DATA.tickers[0]?.ticker; selectStock(selected); drawRS(); activate("today");
}
function renderMarket(){
 let m=DATA.market, b=m.breadth||{}, q=m.quality||{};
 $("#marketStrip").innerHTML=[
  ["Market regime",`<span class="regime ${m.regime}">${m.regime}</span>${DATA.meta.demo?'<div class="demo-banner">ILLUSTRATIVE DEMO</div>':""}`],
  ["Market quality",`${q.score??"—"} <small>${q.state||""}</small>`],["Above 200DMA",`${b.above_200??"—"}%`],
  ["A/D ratio",b.ad_ratio??"—"],["Setups",m.setup_count??"—"]
 ].map(([k,v])=>`<div class="metric"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
}
function initFilters(){
 let secs=[...new Set(DATA.tickers.map(x=>x.sector))].sort();
 $("#sectorFilter").innerHTML='<option value="">All sectors</option>'+secs.map(x=>`<option>${x}</option>`).join("");
 $("#search").oninput=renderList;$("#sectorFilter").onchange=renderList;
}

function screenBadges(x){
 const f=x.screeners?.flags||{}, defs=[
  ["trend_leader","TREND"],["growth_leader","GROWTH"],["vcp_ready","VCP"],
  ["volume_breakthrough","VOL"],["rs_new_high_before_price","RS→PRICE"],["rs_new_high","RS HIGH"]
 ];
 return defs.filter(([k])=>f[k]).slice(0,3).map(([k,l])=>`<span class="screen-badge ${k==="rs_new_high_before_price"?"hot":""}">${l}</span>`).join("");
}

function renderList(){
 let q=$("#search").value.toLowerCase(),sec=$("#sectorFilter").value;
 filtered=DATA.tickers.filter(x=>(!q||x.ticker.toLowerCase().includes(q)||x.company.toLowerCase().includes(q))&&(!sec||x.sector===sec));
 filtered.sort((a,b)=>(b.scores.strength+b.scores.setup)-(a.scores.strength+a.scores.setup));
 $("#resultCount").textContent=filtered.length;
 $("#stockList").innerHTML=filtered.map(x=>`<div class="row ${x.ticker===selected?"active":""}" data-t="${esc(x.ticker)}">
 <div><div class="ticker-line"><span class="ticker">${esc(x.ticker)}</span><span class="status ${x.entry?.label||x.scores.status}">${x.entry?.label||x.scores.status}</span></div><div class="company">${esc(x.company)}</div>
 <div class="screen-badges">${screenBadges(x)}</div></div>
 <div class="mini-score"><b>${x.scores.strength}</b><small>STRENGTH</small></div>
 <div class="mini-score entry-mini"><b>${x.scores.entry??"—"}</b><small>ENTRY</small></div></div>`).join("");
 $$("#stockList .row").forEach(r=>r.onclick=()=>selectStock(r.dataset.t));
}
function selectStock(t){
 selected=t;let x=DATA.tickers.find(z=>z.ticker===t);if(!x)return;
 renderList();
 $("#heroHead").innerHTML=`<div class="hero-title"><div><div class="eyebrow">${esc(x.sector)}</div><h2>${esc(x.ticker)}</h2><p>${esc(x.company)} · ${esc(x.industry)}</p></div>
 <div class="hero-price"><b>$${x.price.close.toFixed(2)}</b><div class="${x.price.change_pct>=0?"pos":"neg"}">${x.price.change_pct>=0?"+":""}${x.price.change_pct.toFixed(2)}%</div></div></div>`;
 $("#heroStats").innerHTML=[["Strength",x.scores.strength],["Setup",x.scores.setup],["Entry",x.scores.entry],["RS",x.rs.score]].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b??"—"}</b></div>`).join("");
 let pr=x.period_returns||{};
 $("#periodStrip").innerHTML=["1W","1M","3M","6M","12M"].map(k=>{let v=pr[k];return `<div class="period"><small>${k}</small><b class="${v==null?"":v>=0?"pos":"neg"}">${v==null?"—":(v>=0?"+":"")+v+"%"}</b></div>`}).join("");
 let fg=x.factor_grades||{};
 $("#factorGrades").innerHTML=["RS","Trend","Setup","Volume","Growth"].map(k=>`<div class="grade"><small>${k}</small><b>${fg[k]||"—"}</b></div>`).join("");
 let warns=x.warnings||[]; $("#warningCount").textContent=warns.length;
 $("#warnings").innerHTML=warns.length?warns.map(w=>`<div class="warning ${w.level||"medium"}">${w.text}</div>`).join(""):`<div class="warning none">✓ No computed technical warning flag</div>`;
 drawHistory(x);

 $("#heroStatus").textContent=x.entry?.label||x.scores.status;
 let v=x.patterns.vcp||{}, why=[];
 if(x.rs.score>=90)why.push(["Elite RS",`Top relative-strength cohort: ${x.rs.score}`]);
 if(x.trend_template.passed>=7)why.push(["Trend aligned",`${x.trend_template.passed}/${x.trend_template.total} trend checks pass`]);
 if(v.detected)why.push(["VCP detected",`Quality ${v.score}/100 · contractions ${(v.contractions||[]).map(z=>Math.round(z*100)+"%").join(" → ")}`]);
 if(v.distance_pct!=null)why.push(["Pivot distance",`${v.distance_pct}% from pivot`]);
 if(v.volume_dryup!=null)why.push(["Volume dry-up",`${v.volume_dryup}× recent/base volume`]);
 if(x.rs.before_price)why.push(["RS leads price","RS line is at a 52W high before price"]);
 if(x.technicals?.volume_breakthrough?.detected)why.push(["Volume breakthrough",`${x.technicals.volume_breakthrough.relative_volume}× 20D average volume`]);
 why.push(["Stage",`Stage ${x.stage.value??"—"} · ${x.rs.quadrant}`]);
 let mf=x.v8?.macro_fit;if(mf)why.push(["Macro fit",`${mf.score}/100 · ${mf.state}`]);
 let risk=x.risk||{};
 if(risk.atr14_pct!=null)why.push(["Risk",`ATR ${risk.atr14_pct}% · 90D drawdown ${risk.max_drawdown_90d_pct??"—"}%`]);
 $("#whyList").innerHTML=why.slice(0,6).map(([a,b])=>`<div class="why"><strong>${a}</strong>${b}</div>`).join("");
 drawPrice(x);drawRadar(x);renderInsights(x);
}
function renderInsights(x){
 let axes=x.scores.radar||{};
 $("#insightCards").innerHTML=Object.entries(axes).map(([k,v])=>`<div class="insight"><div class="top"><span>${k}</span><b>${v}</b></div><div class="bar"><i style="width:${v}%"></i></div></div>`).join("");
}
function drawPrice(x){
 let can=$("#priceCanvas"),r=can.getBoundingClientRect(),d=window.devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);
 let arr=x.chart||[];if(arr.length<2)return;let p=26,w=r.width,h=r.height,vals=arr.map(z=>z.c),mn=Math.min(...vals),mx=Math.max(...vals),den=Math.max(mx-mn,.01);
 let X=i=>p+i/(arr.length-1)*(w-2*p),Y=v=>h-p-(v-mn)/den*(h-2*p);
 c.clearRect(0,0,w,h);c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");c.lineWidth=1;
 for(let i=0;i<4;i++){let y=p+i*(h-2*p)/3;c.beginPath();c.moveTo(p,y);c.lineTo(w-p,y);c.stroke()}
 c.strokeStyle="#7ad7ff";c.lineWidth=2;c.beginPath();arr.forEach((z,i)=>i?c.lineTo(X(i),Y(z.c)):c.moveTo(X(i),Y(z.c)));c.stroke();
 c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.font="10px system-ui";c.fillText(mx.toFixed(1),3,p+4);c.fillText(mn.toFixed(1),3,h-p);
}
function drawRadar(x){
 let can=$("#radarCanvas"),r=can.getBoundingClientRect(),d=window.devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);c.clearRect(0,0,r.width,r.height);
 let data=x.scores.radar||{},keys=["RS","Trend","Setup","Growth","Volume"],cx=r.width/2,cy=r.height/2,R=Math.min(r.width,r.height)*.34;
 let pt=(i,val)=>{let a=-Math.PI/2+i*2*Math.PI/5,rr=R*val/100;return [cx+Math.cos(a)*rr,cy+Math.sin(a)*rr]};
 c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.font="10px system-ui";c.textAlign="center";
 [25,50,75,100].forEach(l=>{c.beginPath();keys.forEach((_,i)=>{let [x1,y1]=pt(i,l);i?c.lineTo(x1,y1):c.moveTo(x1,y1)});c.closePath();c.stroke()});
 keys.forEach((k,i)=>{let [x1,y1]=pt(i,116);c.fillText(`${k} ${data[k]??0}`,x1,y1)});
 c.strokeStyle="#7ad7ff";c.fillStyle="rgba(122,215,255,.16)";c.lineWidth=2;c.beginPath();keys.forEach((k,i)=>{let [x1,y1]=pt(i,data[k]??0);i?c.lineTo(x1,y1):c.moveTo(x1,y1)});c.closePath();c.fill();c.stroke();
}


function fmtMoney(v){
 if(v==null)return "—";let a=Math.abs(v),s=v<0?"-":"";
 if(a>=1e9)return `${s}$${(a/1e9).toFixed(1)}B`;if(a>=1e6)return `${s}$${(a/1e6).toFixed(1)}M`;if(a>=1e3)return `${s}$${(a/1e3).toFixed(0)}K`;return `${s}$${a.toFixed(0)}`;
}

function initResearch(){
 let sel=$("#researchTicker");if(!sel)return;
 sel.innerHTML=DATA.tickers.map(x=>`<option value="${esc(x.ticker)}">${esc(x.ticker)} · ${esc(x.company)}</option>`).join("");
 sel.value=DATA.tickers[0]?.ticker||"";sel.onchange=renderResearch;renderResearch();
}
function renderResearch(){
 let x=DATA.tickers.find(z=>z.ticker===$("#researchTicker").value);if(!x)return;
 let v=x.v6||{},e=v.estimates||{},rp=e.revision_pulse||{},ss=e.surprise_summary||{},d=v.reverse_dcf||{};
 $("#revisionCards").innerHTML=[
  ["30D EPS rev.",rp.change_30d_pct==null?"—":`${rp.change_30d_pct>0?"+":""}${rp.change_30d_pct}%`],
  ["Net revisions",rp.net_30d??"—"],["Last surprise",ss.last_surprise_pct==null?"—":`${ss.last_surprise_pct}%`],
  ["Next earnings",e.next_earnings||"—"]
 ].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join("");
 if(d.available){
   $("#reverseDcfPanel").innerHTML=`<div class="dcf-hero">
    <div class="dcf-big"><small>Implied 5Y revenue growth</small><b>${d.implied_revenue_growth_pct}%</b><div class="fine">Current EV solved under the assumptions below.</div></div>
    <div class="dcf-big"><small>FCF margin held constant</small><b>${d.fcf_margin_pct}%</b><div class="fine">WACC ${d.wacc_pct}% · terminal ${d.terminal_growth_pct}%</div></div>
   </div><p class="fine">${d.interpretation||"Reverse DCF is an expectation tool, not a target price."}</p>`;
 } else $("#reverseDcfPanel").innerHTML=`<div class="formula-box">Unavailable: ${d.reason||"missing inputs"}</div>`;
 $("#revisionPanel").innerHTML=`<div class="revision-grid">
  <div class="revision-box"><small>Current EPS est.</small><b>${rp.eps_current??"—"}</b></div>
  <div class="revision-box"><small>30 days ago</small><b>${rp.eps_30d_ago??"—"}</b></div>
  <div class="revision-box"><small>90 days ago</small><b>${rp.eps_90d_ago??"—"}</b></div>
  <div class="revision-box"><small>Up revisions 30D</small><b>${rp.up_30d??"—"}</b></div>
  <div class="revision-box"><small>Down revisions 30D</small><b>${rp.down_30d??"—"}</b></div>
  <div class="revision-box"><small>Positive last 4</small><b>${ss.positive_last4??"—"}</b></div>
 </div>`;
 let c7=x.v7?.catalyst||{},gap=x.v7?.expectation_gap||{};
 if(c7.score!=null){
   $("#reverseDcfPanel").innerHTML += `<div class="section-title"><span>CATALYST SCORE</span><span>${c7.score} · ${c7.state}</span></div>
   <div class="catalyst-layers">${Object.entries(c7.layers||{}).map(([k,v])=>`<div class="catalyst-layer"><small>${k}</small><b>${v}</b></div>`).join("")}</div>
   ${gap.available?`<div class="formula-box">Reported revenue YoY ${gap.reported_revenue_yoy_pct}% vs implied 5Y growth ${gap.implied_5y_growth_pct}% → context gap ${gap.context_gap_pct}%<br>${gap.caveat||""}</div>`:""}`;
 }
 let cats=v.catalysts||[];
 $("#catalystTimeline").innerHTML=cats.length?cats.map(c=>`<div class="timeline-item ${c.direction||""}">
  <div class="date">${c.date||"CURRENT"}</div><div class="node"></div><div class="timeline-card"><b>${esc(c.title)}</b><span>${c.detail||""}</span></div>
 </div>`).join(""):`<div class="fine">No catalyst items yet.</div>`;
}

function renderRanks(){
 let rows=DATA.revision_rankings||[];
 $("#revisionRankTable").innerHTML=rows.map(r=>{let g=r.expectation_gap||{},gap=g.available?`${g.context_gap_pct>0?"+":""}${g.context_gap_pct}%`:"—";
 return `<div class="rank-row" data-t="${esc(r.ticker)}"><span><b>${r.revision_rank}</b></span><span class="ticker-cell"><b>${esc(r.ticker)}</b><small>${esc(r.company)}</small></span>
 <span>${r.revision_score}</span><span class="${(r.change_30d_pct||0)>=0?"pos":"neg"}">${r.change_30d_pct==null?"—":(r.change_30d_pct>=0?"+":"")+r.change_30d_pct+"%"}</span>
 <span>${r.net_30d??"—"}</span><span>${r.last_surprise_pct==null?"—":r.last_surprise_pct+"%"}</span><span>${r.catalyst_score??"—"}</span><span>${gap}</span></div>`}).join("");
 $$("#revisionRankTable .rank-row").forEach(e=>e.onclick=()=>{activate("research");$("#researchTicker").value=e.dataset.t;renderResearch()})
}
function renderSignalScorecards(){
 let s=DATA.signal_backtests||{};
 $("#signalScorecards").innerHTML=Object.entries(s).map(([name,x])=>{let z=x["20d"]||{};
 return `<div class="signal-card"><h3>${name.replaceAll("_"," ")}</h3><div class="metrics">
  <div><small>Signals</small><b>${x.count??0}</b></div><div><small>20D win rate</small><b>${z.win_rate==null?"—":z.win_rate+"%"}</b></div>
  <div><small>Avg 20D</small><b class="${(z.avg_return_pct||0)>=0?"pos":"neg"}">${z.avg_return_pct==null?"—":z.avg_return_pct+"%"}</b></div>
  <div><small>Avg max move</small><b>${z.avg_max_move_pct==null?"—":z.avg_max_move_pct+"%"}</b></div>
 </div></div>`}).join("");
}

function initReplay(){
 let s=$("#replayTicker");if(!s)return;
 s.innerHTML=DATA.tickers.map(x=>`<option value="${esc(x.ticker)}">${esc(x.ticker)}</option>`).join("");s.value=DATA.tickers[0]?.ticker||"";s.onchange=renderReplay;renderSignalScorecards();renderReplay();
}
function renderReplay(){
 let x=DATA.tickers.find(z=>z.ticker===$("#replayTicker").value);if(!x)return;let r=x.v6?.replay||{};
 $("#replayStats").innerHTML=[
  ["Signals",r.count??"—"],["Win rate",r.win_rate==null?"—":r.win_rate+"%"],["Avg +20D",r.avg_return_pct==null?"—":r.avg_return_pct+"%"],["Avg max move",r.avg_max_move_pct==null?"—":r.avg_max_move_pct+"%"]
 ].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join("");
 $("#replayCaveats").textContent=(r.caveats||["Replay data unavailable."]).join(" · ");
 let sb=x.v7?.signal_backtest||{};
 let signalHtml=Object.entries(sb).map(([name,z])=>{if(!z||z.error)return "";let d=z["20d"]||{};return `<div class="replay-row"><span>${name.replaceAll("_"," ")}</span><b>${z.count??0} signals</b><span>${d.win_rate==null?"—":d.win_rate+"% wins"}</span><span>${d.avg_return_pct==null?"—":d.avg_return_pct+"% avg 20D"}</span></div>`}).join("");
 $("#replayTrades").innerHTML=signalHtml+((r.trades||[]).slice().reverse().map(t=>`<div class="replay-row"><span>${t.date}</span><b class="${(t.return_pct||0)>=0?"pos":"neg"}">${t.return_pct}%</b><span>score ${t.score??"—"}</span><span>legacy composite replay</span></div>`).join("")||'<div class="fine">No replayed signals.</div>');
}
function watchGet(){try{return JSON.parse(localStorage.getItem("rsradar_watch")||"[]")}catch(e){return[]}}
function watchSet(a){localStorage.setItem("rsradar_watch",JSON.stringify(a))}
function initMonitor(){
 let s=$("#watchTicker");if(!s)return;s.innerHTML=DATA.tickers.map(x=>`<option value="${esc(x.ticker)}">${esc(x.ticker)} · ${esc(x.company)}</option>`).join("");
 $("#addWatch").onclick=()=>{let a=watchGet(),t=s.value;if(!a.includes(t)){a.push(t);watchSet(a)}renderWatch()};
 $("#notifyBtn").onclick=async()=>{if("Notification" in window)await Notification.requestPermission();renderWatch()};
 $("#analyzePortfolio").onclick=renderPortfolio;
 let existing=localStorage.getItem("rsradar_portfolio");if(existing)$("#portfolioInput").value=existing;
 $("#portfolioInput").addEventListener("input",()=>localStorage.setItem("rsradar_portfolio",$("#portfolioInput").value));
 renderWatch();renderPortfolio();
}
function renderWatch(){
 let a=watchGet(),rows=a.map(t=>DATA.tickers.find(x=>x.ticker===t)).filter(Boolean);
 $("#watchList").innerHTML=rows.map(x=>{let triggers=[];
   if(x.entry?.label==="READY")triggers.push("READY");
   if((x.rs?.score||0)>=90)triggers.push("RS≥90");
   if(x.patterns?.vcp?.detected)triggers.push("VCP");
   if(x.rs?.before_price)triggers.push("RS→PRICE");
   return `<div class="watch-row"><b>${esc(x.ticker)}</b><small>${triggers.join(" · ")||"Watching"}</small><span>RS ${x.rs.score}</span><span>${x.entry?.label||"—"}</span><button class="icon-btn watch-remove" data-t="${esc(x.ticker)}">×</button></div>`
 }).join("")||'<div class="fine">Add stocks to your watchlist.</div>';
 $$(".watch-remove").forEach(b=>b.onclick=()=>{watchSet(watchGet().filter(t=>t!==b.dataset.t));renderWatch()});
 if("Notification" in window&&Notification.permission==="granted"){
   rows.forEach(x=>{
    let k=`rsradar_alert_${new Date().toISOString().slice(0,10)}_${esc(x.ticker)}`;
    if(!localStorage.getItem(k)&&(x.entry?.label==="READY"||x.rs?.before_price)){
      new Notification(`RS Radar · ${esc(x.ticker)}`,{body:`${x.entry?.label||""}${x.rs?.before_price?" · RS new high before price":""}`});
      localStorage.setItem(k,"1");
    }
   })
 }
}
function renderPortfolio(){
 let raw=$("#portfolioInput")?.value||"";if(!$("#portfolioStats"))return;
 let items=raw.split(/\n+/).map(l=>l.split(",")).filter(z=>z.length>=2).map(([t,s])=>({ticker:t.trim().toUpperCase(),shares:+s||0}));
 let rows=[],total=0,sectors={};
 items.forEach(h=>{let x=DATA.tickers.find(z=>z.ticker===h.ticker);if(!x||h.shares<=0)return;let v=h.shares*x.price.close;total+=v;rows.push({x,v,shares:h.shares});sectors[x.sector]=(sectors[x.sector]||0)+v});
 let weighted=(key)=>total&&rows.every(r=>key(r.x)!=null)?rows.reduce((a,r)=>a+key(r.x)*r.v,0)/total:null;
 let maxw=total?Math.max(0,...rows.map(r=>r.v/total*100)):0,hhi=total?rows.reduce((a,r)=>a+Math.pow(r.v/total,2),0):0;
 $("#portfolioStats").innerHTML=[
  ["Market value",total?`$${Math.round(total).toLocaleString()}`:"—"],["Weighted RS",weighted(x=>x.rs.score)?.toFixed(1)||"—"],
  ["Weighted strength",weighted(x=>x.scores.strength)?.toFixed(1)||"—"],["Largest position",total?maxw.toFixed(1)+"%":"—"]
 ].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join("");
 $("#sectorExposure").innerHTML=Object.entries(sectors).sort((a,b)=>b[1]-a[1]).map(([k,v])=>{let p=100*v/total;return `<div class="exposure-bar"><small>${k}</small><div class="track"><i style="width:${p}%"></i></div><b>${p.toFixed(1)}%</b></div>`}).join("")+
 (total?`<p class="fine">Concentration HHI ${hhi.toFixed(3)} · holdings ${rows.length}</p>`:"");

 // Align chart returns (up to 120 sessions) and calculate correlation/covariance in-browser.
 let series={};rows.forEach(r=>{series[r.x.ticker]=(r.x.chart||[]).map(z=>({d:z.d,c:+z.c}))});
 let tickers=rows.map(r=>r.x.ticker),dateSets=tickers.map(t=>new Set(series[t].map(z=>z.d)));
 let common=tickers.length?[...dateSets[0]].filter(d=>dateSets.every(s=>s.has(d))).sort():[];
 let returns={};tickers.forEach(t=>{let map=Object.fromEntries(series[t].map(z=>[z.d,z.c]));let vals=common.map(d=>map[d]);returns[t]=vals.slice(1).map((v,i)=>v/vals[i]-1)});
 function mean(a){return a.length?a.reduce((x,y)=>x+y,0)/a.length:0}
 function cov(a,b){let ma=mean(a),mb=mean(b);return a.length>1?a.reduce((s,v,i)=>s+(v-ma)*(b[i]-mb),0)/(a.length-1):0}
 function corr(a,b){if(a.length<20)return null;let c=cov(a,b),sa=Math.sqrt(cov(a,a)),sb=Math.sqrt(cov(b,b));return sa&&sb?c/(sa*sb):null}
 let n=tickers.length,matrix=tickers.map(a=>tickers.map(b=>corr(returns[a]||[],returns[b]||[])));
 if(n){
   $("#corrMatrix").innerHTML=`<div class="corr-grid" style="grid-template-columns:70px repeat(${n},minmax(42px,1fr))"><div class="corr-cell head"></div>${tickers.map(t=>`<div class="corr-cell head">${t}</div>`).join("")}${tickers.map((a,i)=>`<div class="corr-cell head">${a}</div>${tickers.map((b,j)=>{let v=matrix[i][j],cl=v>=.7?"poshi":v>=.25?"poslo":v<=-.5?"neghi":v<0?"neglo":"";return `<div class="corr-cell ${cl}">${v==null?"N/A":v.toFixed(2)}</div>`}).join("")}`).join("")}</div>`;
 } else $("#corrMatrix").innerHTML='<div class="fine">Add holdings with price history.</div>';

 // Marginal risk contribution from daily covariance.
 let weights=rows.map(r=>r.v/(total||1)),covm=tickers.map(a=>tickers.map(b=>cov(returns[a]||[],returns[b]||[])*252));
 let portVar=0;for(let i=0;i<n;i++)for(let j=0;j<n;j++)portVar+=weights[i]*weights[j]*covm[i][j];
 let vol=Math.sqrt(Math.max(0,portVar)),rawrc=[];
 for(let i=0;i<n;i++){let cw=0;for(let j=0;j<n;j++)cw+=covm[i][j]*weights[j];rawrc.push(vol?weights[i]*cw/vol:0)}
 let rcsum=rawrc.reduce((a,b)=>a+b,0)||1,rcp=rawrc.map(v=>100*v/rcsum);
 $("#riskContribution").innerHTML=tickers.map((t,i)=>`<div class="risk-row"><small>${t}</small><div class="risk-track"><i style="width:${Math.max(0,Math.min(100,rcp[i]))}%"></i></div><b>${common.length<21?"N/A":rcp[i].toFixed(1)+"%"}</b></div>`).join("")+
 (n?`<p class="fine">Estimated annualized volatility ${common.length<21?"N/A":(vol*100).toFixed(1)+"%"} · ${common.length} aligned sessions.</p>`:"");

 // Historical stored stress + transparent hypothetical shocks.
 let scenarios={"COVID_CRASH":null,"2022_BEAR_LEG":null,"2023_BANK_STRESS":null};
 Object.keys(scenarios).forEach(s=>{if(rows.length&&rows.every(r=>r.x.v7?.stress_returns?.[s]!=null))scenarios[s]=rows.reduce((v,r)=>v+r.v/(total||1)*r.x.v7.stress_returns[s],0)});
 let hypo={
   "MARKET -10%":-10,
   "TECH SHOCK":rows.reduce((a,r)=>a+r.v/(total||1)*(r.x.sector==="Technology"?-20:-5),0),
   "RATE SHOCK":rows.reduce((a,r)=>a+r.v/(total||1)*({"Technology":-12,"Real Estate":-15,"Utilities":-10,"Financials":-4}[r.x.sector]??-7),0),
   "ENERGY SPIKE":rows.reduce((a,r)=>a+r.v/(total||1)*({"Energy":15,"Consumer Cyclical":-8,"Industrials":-5}[r.x.sector]??-4),0)
 };
 let all=total?{...scenarios,...hypo}:scenarios;
 $("#stressPanel").innerHTML=Object.entries(all).map(([k,v])=>{let w=v==null?0:Math.min(100,Math.abs(v)*3);return `<div class="stress-row ${v>=0?"pos":"neg"}"><small>${k.replaceAll("_"," ")}</small><div class="stress-track"><i style="width:${w}%"></i></div><b>${v==null?"N/A":(v>=0?"+":"")+v.toFixed(1)+"%"}</b></div>`}).join("")+
 `<p class="fine">Historical windows use stored ticker returns when available. Hypothetical scenarios are simple sector shocks, not forecasts.</p>`;
}

function initIntelligence(){
 let sel=$("#intelTicker");if(!sel)return;
 sel.innerHTML=DATA.tickers.map(x=>`<option value="${esc(x.ticker)}">${esc(x.ticker)} · ${esc(x.company)}</option>`).join("");
 sel.value=DATA.tickers[0]?.ticker||"";sel.onchange=renderIntelligence;renderIntelligence();renderMacro();
}
function box(lines){return `<div class="intel-box">${lines.map(([a,b])=>`<div class="intel-line"><span>${a}</span><b>${b??"—"}</b></div>`).join("")}</div>`}
function renderIntelligence(){
 let t=$("#intelTicker").value,x=DATA.tickers.find(z=>z.ticker===t);if(!x)return;
 let v=x.v5||{},fq=v.fundamental_quality||{},m=fq.margins||{},q=fq.quality||{},val=fq.valuation||{},ins=v.insider||{},inst=v.institutional_13f||{},sh=v.short_volume||{};
 $("#intelSummary").innerHTML=[
  ["Quality",fq.quality_score??"—"],["Strength",x.scores.strength],["Entry",x.scores.entry??"—"],["RS",x.rs.score]
 ].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join("");
 $("#qualityPanel").innerHTML=box([
   ["Quality score",fq.quality_score],["Gross margin",m.gross_margin_pct==null?"—":m.gross_margin_pct+"%"],
   ["Operating margin",m.operating_margin_pct==null?"—":m.operating_margin_pct+"%"],["FCF margin",m.fcf_margin_pct==null?"—":m.fcf_margin_pct+"%"],
   ["ROE",q.roe_pct==null?"—":q.roe_pct+"%"],["Debt / equity",q.debt_to_equity],["Interest coverage",q.interest_coverage],
   ["FCF yield",val.fcf_yield_pct==null?"—":val.fcf_yield_pct+"%"]
 ]);
 $("#insiderPanel").innerHTML=box([
   ["Open-market buys",ins.purchase_count],["Open-market sales",ins.sale_count],
   ["Purchase value",fmtMoney(ins.purchase_value)],["Sale value",fmtMoney(ins.sale_value)],
   ["Net open-market",`<span class="${(ins.net_open_market_value||0)>=0?"pos":"neg"}">${fmtMoney(ins.net_open_market_value)}</span>`]
 ]);
 $("#institutionPanel").innerHTML=box([
   ["13F match confidence",inst.match_confidence==null?"—":inst.match_confidence+"%"],["Matched issuer",inst.matched_issuer],
   ["Holding rows",inst.manager_rows],["Reported value",inst.reported_value_thousands==null?"—":fmtMoney(inst.reported_value_thousands*1000)],
   ["Reported shares",inst.reported_shares==null?"—":Number(inst.reported_shares).toLocaleString()]
 ]);
 $("#shortPanel").innerHTML=box([
   ["Latest short volume",sh.latest_ratio_pct==null?"—":sh.latest_ratio_pct+"%"],["5D avg",sh.avg5_ratio_pct==null?"—":sh.avg5_ratio_pct+"%"],
   ["20D avg",sh.avg20_ratio_pct==null?"—":sh.avg20_ratio_pct+"%"],["Trend",sh.trend],["Observations",sh.observations]
 ])+`<p class="fine">${sh.caveat||"FINRA short-sale volume is distinct from short interest."}</p>`;
}
function renderMacro(){
 let m=DATA.macro||{};
 $("#macroGrid").innerHTML=Object.entries(m).filter(([k,v])=>v&&typeof v==="object").map(([k,v])=>`<div class="macro-card">
 <div class="top"><div><b>${v.label||k}</b><div class="company">${k}</div></div><strong>${v.value??"—"}</strong></div>
 <div class="section-title"><span class="${(v.change_1d_pct||0)>=0?"pos":"neg"}">1D ${v.change_1d_pct==null?"—":(v.change_1d_pct>=0?"+":"")+v.change_1d_pct+"%"}</span>
 <span class="${(v.change_1m_pct||0)>=0?"pos":"neg"}">1M ${v.change_1m_pct==null?"—":(v.change_1m_pct>=0?"+":"")+v.change_1m_pct+"%"}</span></div></div>`).join("");
}

function renderMarketHealth(){
 let m=DATA.market||{},b=m.breadth||{},q=m.quality||{};
 $("#qualityBadge").innerHTML=`<div class="quality-badge ${q.state||""}"><small>QUALITY</small><b>${q.score??"—"}</b>${q.state||""}</div>`;
 let kpis=[["Adv / Dec",`${b.advance??"—"} / ${b.decline??"—"}`],["A/D ratio",b.ad_ratio??"—"],["Up/Down volume",b.up_down_volume_ratio??"—"],["> 50DMA",`${b.above_50??"—"}%`],
 ["52W H / L",`${b.new_high_52w??"—"} / ${b.new_low_52w??"—"}`],["Breadth thrust",`${b.breadth_thrust_10ema??"—"}%`],["T2108-like >40D",`${b.above_40??"—"}%`],["3×ATR ext.",`${b.atr_3x_extended_up??"—"} / ${b.atr_3x_extended_down??"—"}`]];
 $("#breadthKpis").innerHTML=kpis.map(([k,v])=>`<div class="breadth-kpi"><small>${k}</small><b>${v}</b></div>`).join("");
 let sb=[["Up / Down 4%+",`${b.up_4pct??"—"} / ${b.down_4pct??"—"}`,`ratio ${b.daily_4pct_ratio??"—"}`],
 ["Up / Down 25% Q",`${b.up_25pct_quarter??"—"} / ${b.down_25pct_quarter??"—"}`,`ratio ${b.quarter_bull_bear_ratio??"—"}`],
 ["Net new highs",b.new_high_low_net??"—","52-week high minus low"],
 ["Breadth thrust",b.breadth_thrust_flag?"TRIGGERED":"No trigger",`${b.breadth_thrust_10ema??"—"}% 10EMA advancers`]];
 $("#stockbeeGrid").innerHTML=sb.map(([k,v,n])=>`<div class="sb-card"><small>${k}</small><b>${v}</b><span>${n}</span></div>`).join("");
 $("#marketComponents").innerHTML=Object.entries(q.components||{}).map(([k,v])=>`<div class="insight"><div class="top"><span>${k}</span><b>${v}</b></div><div class="bar"><i style="width:${Math.min(100,v/40*100)}%"></i></div></div>`).join("");
 drawBreadth();
}
function drawBreadth(){
 let can=$("#breadthCanvas");if(!can)return;let r=can.getBoundingClientRect();if(r.width<20)return;let d=devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);
 let a=DATA.market?.breadth?.advance_history||[];c.clearRect(0,0,r.width,r.height);if(a.length<2)return;
 let p=24,w=r.width,h=r.height,X=i=>p+i/(a.length-1)*(w-2*p),Y=v=>h-p-v/100*(h-2*p);
 c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");[25,50,75].forEach(v=>{c.beginPath();c.moveTo(p,Y(v));c.lineTo(w-p,Y(v));c.stroke()});
 c.strokeStyle="#7ad7ff";c.lineWidth=2;c.beginPath();a.forEach((z,i)=>i?c.lineTo(X(i),Y(z.advance_pct)):c.moveTo(X(i),Y(z.advance_pct)));c.stroke();
}

function fmtMacro(v,unit){
 if(v==null)return "—";
 let n=Number(v),s=Math.abs(n)>=1000?n.toLocaleString(undefined,{maximumFractionDigits:1}):n.toFixed(Math.abs(n)<10?2:1);
 return `${s}${unit==="%"?"%":unit==="pp"?" pp":unit==="bp"?" bp":unit==="k"?"k":unit==="$bn"?"B":""}`;
}
function macroRows(keys){
 let f=DATA.macro_v8?.fred||{};
 return keys.map(k=>{let x=f[k]||{};return `<div class="macro-data-row history-clickable" data-history="${k}"><span>${x.label||k}</span><b>${fmtMacro(x.value,x.unit)}</b><span class="date">${x.date||""}</span></div>`}).join("");
}
function renderMacroFull(){
 let m=DATA.macro_v8||{},r=m.regime||{},a=r.axes||{},ny=m.nyfed||{},g=m.gdpnow||{},mk=m.market||{};
 let badge=$("#macroRegimeBadge");if(!badge)return;
 badge.innerHTML=`<div class="macro-regime-badge"><small>REGIME</small><b>${r.regime||"—"}</b><small>risk ${r.macro_risk_score??"—"} · ${r.risk_state||""}</small></div>`;
 $("#macroAxes").innerHTML=Object.entries(a).map(([k,v])=>`<div class="macro-axis"><small>${k.replaceAll("_"," ")}</small><b>${v??"N/A"}</b><div class="bar"><i style="width:${v==null?0:Math.max(0,Math.min(100,v))}%"></i></div></div>`).join("");
 $("#regimeDot").hidden=a.growth==null||a.inflation==null;
 let gx=Math.max(4,Math.min(96,a.growth??50)),iy=Math.max(4,Math.min(96,100-(a.inflation??50)));
 $("#regimeDot").style.left=gx+"%";$("#regimeDot").style.top=iy+"%";
 let f=m.fred||{};
 $("#macroHeadline").innerHTML=[
   ["GDPNow",g.value==null?"—":g.value+"%"],["SOFR",ny.SOFR?.value==null?"—":ny.SOFR.value+"%"],
   ["Fed Funds",f.DFF?.value==null?"—":f.DFF.value+"%"],["HY OAS",f.BAMLH0A0HYM2?.value==null?"—":f.BAMLH0A0HYM2.value+"%"]
 ].map(([k,v])=>`<div class="macro-head"><small>${k}</small><b>${v}</b></div>`).join("");
 $("#macroMarketTape").innerHTML=Object.entries(mk).filter(([k,v])=>v&&typeof v==="object"&&v.value!=null).map(([k,v])=>`<div class="macro-proxy"><div class="top"><div><b>${v.label||k}</b><small>${k}</small></div><strong>${v.value}</strong></div><div class="section-title"><span class="${(v.change_1d_pct||0)>=0?"pos":"neg"}">1D ${v.change_1d_pct??"—"}%</span><span class="${(v.change_1m_pct||0)>=0?"pos":"neg"}">1M ${v.change_1m_pct??"—"}%</span></div></div>`).join("");
 $("#macroRates").innerHTML=macroRows(["DFF","DGS2","DGS10","DGS30","T10Y2Y","T10Y3M","DFII10"])+
   `<div class="macro-data-row"><span>SOFR</span><b>${ny.SOFR?.value==null?"—":ny.SOFR.value+"%"}</b><span class="date">${ny.SOFR?.date||""}</span></div>
    <div class="macro-data-row"><span>SOFR-EFFR basis</span><b>${ny.SOFR_EFFR_SPREAD_BP?.value==null?"—":ny.SOFR_EFFR_SPREAD_BP.value+" bp"}</b><span class="date"></span></div>`;
 $("#macroInflation").innerHTML=macroRows(["CPIAUCSL","CPILFESL","PCEPILFE","T10YIE"]);
 $("#macroGrowth").innerHTML=`<div class="macro-data-row"><span>Atlanta Fed GDPNow</span><b>${g.value==null?"—":g.value+"%"}</b><span class="date">${g.date_text||""}</span></div>`+macroRows(["UNRATE","PAYEMS","INDPRO","RSAFS","HOUST"]);
 $("#macroLiquidity").innerHTML=macroRows(["WALCL","RRPONTSYD","WRESBAL","WTREGEN","M2SL"]);
 $("#macroCredit").innerHTML=macroRows(["BAMLH0A0HYM2","BAMLC0A0CM"]);
 let bySec={};DATA.tickers.forEach(x=>{let z=x.v8?.macro_fit;if(!z||z.score==null)return;(bySec[x.sector]??=[]).push(z.score)});
 let sr=Object.entries(bySec).map(([sec,v])=>[sec,v.reduce((a,b)=>a+b,0)/v.length]).sort((a,b)=>b[1]-a[1]);
 $("#macroSectorFit").innerHTML=sr.map(([sec,v])=>`<div class="sector-fit-row"><small>${sec}</small><div class="track"><i style="width:${v}%"></i></div><b>${v.toFixed(0)}</b></div>`).join("");
 $$("#macrofull [data-history]").forEach(el=>el.onclick=()=>openHistorySeries(el.dataset.history));
 drawMacroHistory();
}
function drawMacroHistory(){
 let can=$("#macroHistoryCanvas");if(!can)return;let r=can.getBoundingClientRect();if(r.width<20)return;let d=devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);c.clearRect(0,0,r.width,r.height);
 let h=DATA.macro_history_v8||[];if(h.length<2)return;let p=25,w=r.width,ht=r.height,X=i=>p+i/(h.length-1)*(w-2*p),Y=v=>ht-p-v/100*(ht-2*p);
 c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");[25,50,75].forEach(v=>{c.beginPath();c.moveTo(p,Y(v));c.lineTo(w-p,Y(v));c.stroke()});
 [["growth","#35d07f"],["inflation","#e9c85a"],["liquidity","#7ad7ff"],["risk","#f06b6b"]].forEach(([k,col])=>{c.strokeStyle=col;c.lineWidth=2;c.beginPath();h.forEach((z,i)=>i?c.lineTo(X(i),Y(z[k]??0)):c.moveTo(X(i),Y(z[k]??0)));c.stroke()});
 c.font="9px system-ui";c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.fillText("Growth",p,10);c.fillText("Inflation",p+45,10);c.fillText("Liquidity",p+92,10);c.fillText("Risk",p+140,10);
}


function signedPct(v){if(v==null)return "N/A";return `${v>=0?"+":""}${Number(v).toFixed(1)}%`}
function renderCommodities(){
 let m=DATA.macro_v9||{},c=m.commodities||{},rows=c.contracts||{},b=c.breadth||{};
 let el=$("#commodityBreadth");if(!el)return;
 el.innerHTML=`<div class="commodity-breadth"><small>COMMODITY BREADTH</small><b>${b.above_50dma_pct??"—"}%</b><small>above 50DMA · ${b.positive_1m_pct??"—"}% positive 1M</small></div>`;
 let cats={};Object.entries(rows).forEach(([t,x])=>{(cats[x.category]??=[]).push([t,x])});
 $("#commodityCategories").innerHTML=Object.entries(cats).map(([cat,arr])=>`<div class="commodity-section"><div class="section-title"><span>${cat.toUpperCase()}</span><span>${arr.length} contracts</span></div><div class="commodity-grid">${arr.map(([t,x])=>`<div class="commodity-card history-clickable" data-history="${t}"><div class="top"><div><b>${x.label}</b><small>${t} · ${x.unit}</small></div><strong>${x.value==null?"N/A":Number(x.value).toLocaleString(undefined,{maximumFractionDigits:3})}</strong></div><div class="commodity-returns"><span class="${(x.return_1d_pct||0)>=0?"pos":"neg"}">1D ${signedPct(x.return_1d_pct)}</span><span class="${(x.return_1m_pct||0)>=0?"pos":"neg"}">1M ${signedPct(x.return_1m_pct)}</span><span class="${(x.return_3m_pct||0)>=0?"pos":"neg"}">3M ${signedPct(x.return_3m_pct)}</span></div><div class="commodity-returns"><span>1W ${signedPct(x.return_1w_pct)}</span><span>6M ${signedPct(x.return_6m_pct)}</span><span>1Y ${signedPct(x.return_12m_pct)}</span></div><div class="fine">20 / 50 / 200 DMA: ${display(x.ma20)} / ${display(x.ma50)} / ${display(x.ma200)}</div><div class="fine">52W low / high: ${display(x.low_52w)} / ${display(x.high_52w)} · Vol ${display(x.volatility20_ann_pct)}%</div><div class="metric-provenance">${esc(x.source||"Unavailable")} · As of ${esc(x.date||"N/A")} · ${esc(x.status||"unverified")}<br>Updated ${esc(x.last_update||"N/A")}<br>${esc(x.method||"source observations")}</div></div>`).join("")}</div></div>`).join("");
 let d=c.derived||{};$("#commodityRatios").innerHTML=`<div class="ratio-grid">${Object.values(d).map(x=>`<div class="ratio-card"><small>${x.label}</small><b>${x.value??"—"} ${x.unit||""}</b></div>`).join("")}</div>`;
 let inv=m.eia_inventories||{};$("#eiaInventory").innerHTML=`<div class="inventory-grid">${Object.entries(inv).filter(([k,x])=>x&&x.label).map(([k,x])=>`<div class="inventory-card history-clickable" data-history="${k}"><small>${x.label} · ${x.date||""}</small><b>${x.value==null?"—":Number(x.value).toLocaleString()} ${x.unit||""}</b><div class="inventory-change ${((x.weekly_change||0)<=0)?"pos":"neg"}">Weekly ${x.weekly_change==null?"—":(x.weekly_change>=0?"+":"")+Number(x.weekly_change).toLocaleString()} · vs 52W avg ${x.vs_52w_avg_pct==null?"—":signedPct(x.vs_52w_avg_pct)}</div></div>`).join("")}</div>`;
 $$("#commodities [data-history]").forEach(el=>el.onclick=()=>openHistorySeries(el.dataset.history));
}
let CAL_FILTER="ALL";
function initCalendar(){
 if(!$("#eventCalendar"))return;
 $$(".calendar-filters .recipe").forEach(b=>b.onclick=()=>{CAL_FILTER=b.dataset.cal; $$(".calendar-filters .recipe").forEach(x=>x.classList.toggle("active",x===b));renderCalendar()});
 renderCalendar();
}
function currentCalendar(calendar,clock=new Date()){
 const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(clock);
 const part=type=>parts.find(p=>p.type===type).value;
 const today=Date.UTC(+part('year'),+part('month')-1,+part('day'));
 const events=(calendar.events||[]).map(e=>({...e,days_from_today:Math.round((Date.parse(e.date+'T00:00:00Z')-today)/86400000),has_passed:e.datetime_utc?Date.parse(e.datetime_utc)<=clock.getTime():false}));
 const upcoming=events.filter(e=>e.days_from_today>=0&&!e.has_passed);
 const available=events.length>0||(calendar.providers||[]).some(p=>p.status==='ok'||p.status==='stale');
 return {...calendar,events,high_impact_next_7d:available?upcoming.filter(e=>e.importance==='HIGH'&&e.days_from_today<=7).length:null,high_impact_next_30d:available?upcoming.filter(e=>e.importance==='HIGH'&&e.days_from_today<=30).length:null};
}
function eventTimeLabel(e){
 return (e.time_et?e.time_et+' ET':'Date only (ET)')+(e.datetime_kst?' · '+e.datetime_kst.slice(0,10)+' '+e.datetime_kst.slice(11,16)+' KST':'');
}
function renderCalendar(){
 let c=currentCalendar(DATA.macro_v9?.calendar||{}),events=c.events||[];
 $("#calendarRisk").innerHTML=`<div class="calendar-risk"><small>HIGH IMPACT</small><b>${c.high_impact_next_7d??0}</b><small>next 7D · ${c.high_impact_next_30d??0} next 30D</small></div>`;
 let rows=events.filter(e=>CAL_FILTER==="ALL"||(CAL_FILTER==="HIGH"?e.importance==="HIGH":e.category===CAL_FILTER));
 $("#eventCalendar").innerHTML=rows.map(e=>{let dd=e.days_from_today===0?"TODAY":e.days_from_today>0?`D-${e.days_from_today}`:`D+${Math.abs(e.days_from_today)}`;return `<div class="event-row"><div class="event-date"><b>${e.date.slice(5)}</b><small>${esc(eventTimeLabel(e))}</small></div><span class="impact ${e.importance}">${e.importance}</span><span class="event-category fine">${e.category}</span><div class="event-title"><b>${esc(e.title)}</b><small>${e.notes||""}</small></div><span class="event-source">${esc(e.source)}<br><span class="d-day ${e.days_from_today===0?"today":""}">${dd}${e.has_passed?' · passed':''}</span></span></div>`}).join("")||'<div class="fine">No matching upcoming events.</div>';
 let week=events.filter(e=>e.days_from_today>=0&&e.days_from_today<=7&&!e.has_passed);$("#nextWeekEvents").innerHTML=week.map(e=>`<div class="week-event"><span class="d-day ${e.days_from_today===0?"today":""}">${e.days_from_today===0?"TODAY":"D-"+e.days_from_today}</span><div><b>${esc(e.title)}</b><small>${e.date} · ${esc(eventTimeLabel(e))} · ${esc(e.source)}</small></div></div>`).join("")||'<div class="fine">No events in the next 7 days.</div>';
}


let HISTORY_INDEX=null,HISTORY_CACHE={},HISTORY_RANGE="1Y",HISTORY_CAL=null,HISTORY_TOKEN=0;
async function initHistoryExplorer(){
 if(!$("#historySeries"))return;
 try{HISTORY_INDEX=await (await fetch((DATA.history_v10?.index_path)||"history/index.json",{cache:"no-store"})).json()}catch(e){HISTORY_INDEX={items:[]}}
 let kind=$("#historyKind");kind.onchange=()=>{populateHistorySeries();loadHistorySelected()};
 $("#historySeries").onchange=loadHistorySelected;$("#historyOverlay").onchange=loadHistorySelected;
 $$("#historyRanges .recipe").forEach(b=>b.onclick=()=>{HISTORY_RANGE=b.dataset.range;$$('#historyRanges .recipe').forEach(x=>x.classList.toggle('active',x===b));loadHistorySelected()});
 populateHistorySeries();
 try{HISTORY_CAL=await (await fetch((DATA.history_v10?.calendar_path)||"history/calendar_archive.json",{cache:"no-store"})).json()}catch(e){HISTORY_CAL={events:[]}}
 initArchiveControls();
 await loadHistorySelected();
 if(typeof renderV11FocusTabs==="function")renderV11FocusTabs();
 if(typeof renderDataHealth==="function")renderDataHealth();
}
function historyItems(){return (HISTORY_INDEX?.items||[]).filter(x=>x.path)}
function populateHistorySeries(preselect=null){
 let kind=$("#historyKind")?.value||"ALL",items=historyItems().filter(x=>kind==="ALL"||x.kind===kind);
 items.sort((a,b)=>(a.category+" "+a.label).localeCompare(b.category+" "+b.label));
 let opts=items.map(x=>`<option value="${x.id}">${x.category} · ${x.label}</option>`).join("");
 $("#historySeries").innerHTML=opts;
 if(preselect&&items.some(x=>x.id===preselect))$("#historySeries").value=preselect;
 let primary=$("#historySeries").value;
 $("#historyOverlay").innerHTML='<option value="">None</option>'+historyItems().filter(x=>x.id!==primary).map(x=>`<option value="${x.id}">${x.label}</option>`).join("");
}
async function fetchHistoryItem(id){
 let meta=historyItems().find(x=>x.id===id);if(!meta||!meta.path)return null;
 if(HISTORY_CACHE[id])return HISTORY_CACHE[id];
 try{let r=await fetch(meta.path,{cache:"no-store"});if(!r.ok)throw 0;let d=await r.json();HISTORY_CACHE[id]=d;return d}catch(e){return null}
}
function rangeStart(lastDate,range){
 let d=new Date(lastDate+"T00:00:00Z");if(range==="MAX")return null;
 let days={"3M":93,"1Y":366,"5Y":365.25*5,"10Y":365.25*10}[range]||366;return new Date(d.getTime()-days*86400000)
}
function filterHistory(hist,range){
 if(!hist?.length)return[];let start=rangeStart(hist[hist.length-1].date,range);return start?hist.filter(x=>new Date(x.date+"T00:00:00Z")>=start):hist.slice()
}
function histFmt(v){if(v==null||!Number.isFinite(+v))return"—";let n=+v;return Math.abs(n)>=1000?n.toLocaleString(undefined,{maximumFractionDigits:2}):n.toFixed(Math.abs(n)<10?3:2)}
async function loadHistorySelected(){
 if(!HISTORY_INDEX)return;let token=++HISTORY_TOKEN,id=$("#historySeries").value;if(!id)return;
 let meta=historyItems().find(x=>x.id===id),overlayId=$("#historyOverlay").value;
 $("#historyTitle").textContent=meta?.label||id;$("#historyLatest").textContent="Loading…";$("#historyStats").innerHTML="";
 renderHistoryRows([],meta||{});let canvas=$("#fullHistoryCanvas");canvas.getContext("2d").clearRect(0,0,canvas.width,canvas.height);
 let [data,overlay]=await Promise.all([fetchHistoryItem(id),overlayId?fetchHistoryItem(overlayId):Promise.resolve(null)]);if(token!==HISTORY_TOKEN)return;
 if(!data){$("#historyLatest").textContent="N/A";$("#historyMeta").textContent="History could not be loaded. Reselect the series to retry.";$("#historyCompareNote").textContent="No verified observations available for this series.";return}
 $("#historyCompareNote").textContent=overlayId&&!overlay?"Overlay could not be loaded. The primary series remains available.":"";
 let hist=filterHistory(data.history||[],HISTORY_RANGE),oh=overlay?filterHistory(overlay.history||[],HISTORY_RANGE):[];
 $("#historyCategory").textContent=(meta.category||meta.kind||"SERIES").toUpperCase();$("#historyTitle").textContent=meta.label||id;
 $("#historyRangeLabel").textContent=HISTORY_RANGE;let last=hist[hist.length-1];
 $("#historyLatest").innerHTML=last?`<small>${last.date}</small><b>${histFmt(last.value)} ${meta.unit||""}</b>`:"";
 $("#historyMeta").innerHTML=`<b>${meta.source||data.source||""}</b><br>${meta.start||""} → ${meta.end||""}<br>${(meta.count||data.history?.length||0).toLocaleString()} observations${data.caveat?`<br>${esc(data.caveat)}`:""}<br><span class="fine">Historical macro values use the latest revised source history unless vintage data is explicitly added.</span>`;
 renderHistoryStats(hist,meta);renderHistoryRows(hist,meta);drawFullHistory(hist,meta,oh,overlayId);renderArchive();
}
function renderHistoryStats(hist,meta){
 if(!hist.length){$("#historyStats").innerHTML='';return}let vals=hist.map(x=>+x.value).filter(Number.isFinite),first=vals[0],last=vals[vals.length-1],chg=first?((last/first-1)*100):null;
 let stats=[["Observations",vals.length],["Start",hist[0].date],["Min",histFmt(Math.min(...vals))],["Max",histFmt(Math.max(...vals))],["Range change",chg==null?"—":`${chg>=0?"+":""}${chg.toFixed(1)}%`]];
 $("#historyStats").innerHTML=stats.map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join("");
}
function renderHistoryRows(hist,meta){
 $("#historyRows").innerHTML=hist.slice(-120).reverse().map(x=>`<tr><td>${x.date}</td><td>${histFmt(x.value)} ${meta.unit||""}</td><td>${x.raw==null?"—":histFmt(x.raw)}</td></tr>`).join("");
}
function drawFullHistory(hist,meta,overlay,overlayId){
 let can=$("#fullHistoryCanvas"),r=can.getBoundingClientRect();if(r.width<20)return;let d=devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);c.clearRect(0,0,r.width,r.height);if(hist.length<2)return;
 let pL=54,pR=18,pT=24,pB=30,w=r.width,h=r.height;
 let hasOverlay=overlay?.length>1;
 let pSeries=hist.map(x=>({date:x.date,t:new Date(x.date+"T00:00:00Z").getTime(),value:+x.value})).filter(x=>Number.isFinite(x.value));
 let oSeries=hasOverlay?overlay.map(x=>({date:x.date,t:new Date(x.date+"T00:00:00Z").getTime(),value:+x.value})).filter(x=>Number.isFinite(x.value)):[];
 if(hasOverlay){let pb=pSeries[0]?.value||1,ob=oSeries[0]?.value||1;pSeries=pSeries.map(x=>({...x,plot:x.value/pb*100}));oSeries=oSeries.map(x=>({...x,plot:x.value/ob*100}))}else pSeries=pSeries.map(x=>({...x,plot:x.value}));
 let allT=[...pSeries.map(x=>x.t),...oSeries.map(x=>x.t)],t0=Math.min(...allT),t1=Math.max(...allT),X=t=>pL+(t-t0)/Math.max(1,t1-t0)*(w-pL-pR);
 let plots=[...pSeries.map(x=>x.plot),...oSeries.map(x=>x.plot)].filter(Number.isFinite),mn=Math.min(...plots),mx=Math.max(...plots);if(mx===mn){mx+=1;mn-=1}let Y=v=>pT+(mx-v)/(mx-mn)*(h-pT-pB);
 c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.font="9px system-ui";c.textAlign="right";
 for(let i=0;i<=4;i++){let v=mx-(mx-mn)*i/4,y=Y(v);c.beginPath();c.moveTo(pL,y);c.lineTo(w-pR,y);c.stroke();c.fillText(hasOverlay?`${v.toFixed(1)}`:histFmt(v),pL-5,y+3)}
 let draw=(arr,col,width)=>{c.strokeStyle=col;c.lineWidth=width;c.beginPath();arr.forEach((z,i)=>i?c.lineTo(X(z.t),Y(z.plot)):c.moveTo(X(z.t),Y(z.plot)));c.stroke()};draw(pSeries,"#7ad7ff",2);if(hasOverlay)draw(oSeries,"#e9c85a",1.8);
 c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.textAlign="left";c.fillText(pSeries[0].date,pL,h-8);c.textAlign="right";c.fillText(pSeries[pSeries.length-1].date,w-pR,h-8);
 c.textAlign="left";c.fillStyle="#7ad7ff";c.fillText(hasOverlay?`${meta.id||meta.label} · indexed 100`:`${meta.label||"Series"}`,pL+8,pT+10);if(hasOverlay){c.fillStyle="#e9c85a";c.fillText(`${overlayId} · indexed 100`,pL+145,pT+10)}
}
function initArchiveControls(){
 const years=[...new Set((HISTORY_CAL?.events||[]).map(e=>e.date?.slice(0,4)).filter(Boolean))].sort().reverse(),currentYear=new Intl.DateTimeFormat('en',{timeZone:'America/New_York',year:'numeric'}).format(new Date());
 $('#archiveYear').innerHTML='<option value="ALL">All years</option>'+years.map(y=>`<option>${y}</option>`).join('');
 $('#archiveYear').value=years.find(y=>y<=currentYear)||'ALL';$('#archiveYear').onchange=renderArchive;$('#archiveSearch').oninput=renderArchive;renderArchive();
}
function renderArchive(){
 if(!$('#archiveEvents'))return;
 const year=$('#archiveYear')?.value||'ALL',q=($('#archiveSearch')?.value||'').toLowerCase(),events=HISTORY_CAL?.events||[],years=events.map(e=>e.date?.slice(0,4)).filter(Boolean).sort();
 const rows=events.filter(e=>(year==='ALL'||e.date?.startsWith(year))&&(!q||(e.title||'').toLowerCase().includes(q)||(e.source||'').toLowerCase().includes(q))).sort((a,b)=>(b.date||'').localeCompare(a.date||''));
 $('#archiveCount').textContent=`${rows.length} events`;
 $('#archiveSummary').textContent=years.length?`Official schedules ${years[0]}–${years.at(-1)}`:'No verified schedules available';
 $('#archiveEvents').innerHTML=rows.map(e=>`<div class="archive-row"><b>${esc(e.date)}</b><span class="impact ${esc(e.importance||'LOW')}">${esc(e.importance||'')}</span><div><b>${esc(e.title||'')}</b><small>${esc(e.time_et||'')} ${e.time_et?'ET':''}</small></div><small>${esc(e.source||'')}</small></div>`).join('')||'<div class="fine">No schedules match.</div>';
}
async function openHistorySeries(id){
 activate("historyexplorer");if(!HISTORY_INDEX)await initHistoryExplorer();let item=historyItems().find(x=>x.id===id);if(!item)return;$("#historyKind").value=item.kind;populateHistorySeries(id);$("#historySeries").value=id;await loadHistorySelected();
}


const V11_FOCUS={
 ratesfocus:["DFF","EFFR","SOFR","DGS3MO","DGS2","DGS5","DGS10","DGS30","T10Y2Y","T10Y3M","DFII5","DFII10","T5YIE","T10YIE"],
 inflationfocus:["CPIAUCSL","CPILFESL","PCEPILFE","WPSFD4","T10YIE","CES0500000003"],
 growthfocus:["A191RL1Q225SBEA","UNRATE","U6RATE","CIVPART","PAYEMS","ICSA","JTSJOL","INDPRO","RSAFS","HOUST","PERMIT","UMCSENT"],
 liquidityfocus:["WALCL","WRESBAL","RRPONTSYD","WTREGEN","M2SL","NFCI"],
 creditfocus:["BAMLH0A0HYM2","BAMLC0A0CM","AAA10Y","BAA10Y","NFCI","STLFSI4","HYG"],
 fxfocus:["DEXKOUS","DX-Y.NYB"],
 housingfocus:["MORTGAGE30US","HOUST","PERMIT"],
 energyfocus:["DCOILWTICO","DCOILBRENTEU","DHHNGSP","CL=F","BZ=F","NG=F","RB=F","HO=F"],
 metalsfocus:["GC=F","SI=F","HG=F","PL=F","PA=F"],
 agrifocus:["ZC=F","ZW=F","ZS=F","KC=F","CC=F","SB=F","CT=F","LE=F"]
};
function pctChange(hist,days){if(!hist?.length)return null;let last=hist[hist.length-1],t=new Date(last.date+"T00:00:00Z").getTime()-days*86400000;let p=hist.reduce((best,x)=>Math.abs(new Date(x.date+"T00:00:00Z").getTime()-t)<Math.abs(new Date(best.date+"T00:00:00Z").getTime()-t)?x:best,hist[0]);return p?.value?((last.value/p.value-1)*100):null}
function sparkBars(hist){let a=(hist||[]).slice(-30).map(x=>+x.value).filter(Number.isFinite);if(a.length<2)return'';let mn=Math.min(...a),mx=Math.max(...a),den=Math.max(mx-mn,.0001);return `<div class="sparkline">${a.map(v=>`<i style="height:${15+85*(v-mn)/den}%"></i>`).join('')}</div>`}
async function renderFocusTarget(target,ids){let el=$(target);if(!el||!HISTORY_INDEX)return;let rows=await Promise.all(ids.map(async id=>{let meta=historyItems().find(x=>x.id===id),d=meta?await fetchHistoryItem(id):null;return {id,meta,d}}));el.innerHTML=rows.filter(x=>x.meta&&x.d?.history?.length).map(({id,meta,d})=>{let h=d.history,last=h[h.length-1],c30=pctChange(h,30),c365=pctChange(h,365);return `<div class="focus-metric" data-history-id="${id}"><div class="fm-top"><div class="fm-label">${esc(meta.label)}</div><div class="fm-source">${meta.source||d.source||''}</div></div><div class="fm-value">${histFmt(+last.value)} <small>${meta.unit||''}</small></div><div class="fm-meta"><span>${last.date}</span><span class="fm-change ${(c30||0)>=0?'pos':'neg'}">1M ${c30==null?'—':(c30>=0?'+':'')+c30.toFixed(1)+'%'}</span><span>1Y ${c365==null?'—':(c365>=0?'+':'')+c365.toFixed(1)+'%'}</span></div>${sparkBars(h)}</div>`}).join('')||'<div class="fine">Historical data unavailable.</div>';el.querySelectorAll('[data-history-id]').forEach(x=>x.onclick=()=>openHistorySeries(x.dataset.historyId))}
async function renderV11FocusTabs(){if(!HISTORY_INDEX){setTimeout(renderV11FocusTabs,250);return}await Promise.all([renderFocusTarget('#ratesFocusGrid',V11_FOCUS.ratesfocus),renderFocusTarget('#inflationFocusGrid',V11_FOCUS.inflationfocus),renderFocusTarget('#growthFocusGrid',V11_FOCUS.growthfocus),renderFocusTarget('#liquidityFocusGrid',V11_FOCUS.liquidityfocus),renderFocusTarget('#creditFocusGrid',V11_FOCUS.creditfocus),renderFocusTarget('#fxFocusGrid',V11_FOCUS.fxfocus),renderFocusTarget('#housingFocusGrid',V11_FOCUS.housingfocus),renderFocusTarget('#energyFocusGrid',V11_FOCUS.energyfocus),renderFocusTarget('#metalsFocusGrid',V11_FOCUS.metalsfocus),renderFocusTarget('#agriFocusGrid',V11_FOCUS.agrifocus),renderFocusTarget('#energyInventoryGrid',["crude_ex_spr","total_crude","gasoline","distillate"])]);$$('[data-open-history]').forEach(b=>b.onclick=()=>openHistorySeries(b.dataset.openHistory))}
function renderDataFreshness(){let m=DATA.meta||{},asof=m.as_of||m.generated_at||m.generated||'latest';let demo=m.demo?'DEMO':'LIVE / BUILD';$('#dataFreshness').innerHTML=`<b>${demo}</b><br>as of ${asof}`}
function initGlobalCommand(){let g=$('#globalSearch');if(!g)return;g.onkeydown=e=>{if(e.key!=='Enter')return;let q=g.value.trim().toLowerCase();if(!q)return;let stock=DATA.tickers.find(x=>x.ticker.toLowerCase()===q||x.company.toLowerCase().includes(q));if(stock){activate('workbench');selectStock(stock.ticker);g.value='';return}let h=historyItems().find(x=>x.id.toLowerCase()===q||x.label.toLowerCase().includes(q));if(h){openHistorySeries(h.id);g.value=''}}}
function renderDataHealth(){let box=$('#dataHealthSummary');if(!box)return;let hc=DATA.history_v10?.counts||{},items=historyItems(),obs=items.reduce((s,x)=>s+(+x.count||0),0);box.innerHTML=[["Stocks",DATA.tickers.length],["History series",items.length||Object.values(hc).reduce((a,b)=>a+(+b||0),0)],["Observations",obs.toLocaleString()],["Sources",Object.keys(DATA.sources||{}).length]].map(([a,b])=>`<div class="stat"><small>${a}</small><b>${b}</b></div>`).join('');let src=DATA.sources||{};$('#providerHealth').innerHTML=Object.entries(src).map(([k,v])=>{let text=typeof v==='string'?v:(v.provider||v.source||v.FRED||v.engine||JSON.stringify(v).slice(0,90));let demo=/DEMO/i.test(text);return `<div class="health-row"><b>${k}</b><small>${text}</small><span class="${demo?'source-demo':'source-ok'}">${demo?'DEMO':'CONNECTED / DECLARED'}</span></div>`}).join('');let kinds={};items.forEach(x=>{let k=x.kind||'other';kinds[k]??={series:0,obs:0};kinds[k].series++;kinds[k].obs+=+x.count||0});$('#historyHealth').innerHTML=Object.entries(kinds).map(([k,v])=>`<div class="health-row"><b>${k}</b><small>${v.series} series</small><span>${v.obs.toLocaleString()} obs</span></div>`).join('');let r=$('#reloadDataHealth');if(r)r.onclick=()=>renderDataHealth()}

function renderGroups(){
 let g=DATA.groups||[];
 $("#groupTable").innerHTML=g.map(x=>{let rc=x.rank_change,rm=rc==null?"":`<span class="rank-move ${rc>0?"up":rc<0?"down":""}">${rc>0?"▲":rc<0?"▼":"—"}${Math.abs(rc||0)||""}</span>`;
 return `<div class="group-row"><span class="rank">${x.rank}${rm}</span><span><b>${esc(x.group)}</b><div class="company">${x.count} names</div></span><span>${x.avg_rs}</span><span>${x.avg_short_rs}</span>
 <span class="${(x.return_1m||0)>=0?"pos":"neg"}">${x.return_1m==null?"—":x.return_1m+"%"}</span><span class="${(x.return_3m||0)>=0?"pos":"neg"}">${x.return_3m==null?"—":x.return_3m+"%"}</span>
 <span>${x.above50_pct}%</span><span>${x.setup_count}</span><span>${x.ready_count}</span></div>`}).join("");
}

function renderToday(){
 let m=DATA.market||{},q=m.quality||{},b=m.breadth||{},mac=DATA.macro_v8?.regime||{},cal=currentCalendar(DATA.macro_v9?.calendar||{});
 let hero=[["MARKET REGIME",m.regime||"—",`${q.state||""} · quality ${q.score??"—"}`,'primary'],["MACRO REGIME",mac.regime||"—",`risk ${mac.macro_risk_score??"—"} · ${mac.risk_state||""}`],["BREADTH",b.above_200==null?"—":b.above_200+"%",`${b.advance_pct??"—"}% advancing`],["CREDIT",DATA.macro_v8?.fred?.BAMLH0A0HYM2?.value==null?"—":DATA.macro_v8.fred.BAMLH0A0HYM2.value+"% HY OAS",`credit axis ${mac.axes?.credit??"—"}`],["EVENT RISK",`${cal.high_impact_next_7d??"N/A"} high`,`${cal.high_impact_next_30d??"N/A"} in 30D`]];
 $("#todayHero").innerHTML=hero.map(([k,v,s,c])=>`<div class="today-hero-card ${c||""}"><small>${k}</small><b>${v}</b><div class="sub">${s}</div></div>`).join("");
 let events=(cal.events||[]).filter(e=>(e.days_from_today??999)>=0&&!e.has_passed).sort((a,b)=>(a.days_from_today??999)-(b.days_from_today??999)).slice(0,7);
 $("#todayEvents").innerHTML=events.map(e=>`<div class="today-item"><div><b>${e.days_from_today===0?'TODAY':'D-'+e.days_from_today}</b><small>${e.date}</small></div><div><b>${esc(e.title)}</b><small>${esc(eventTimeLabel(e))} · ${esc(e.source||'')}</small></div><span class="impact ${e.importance||'LOW'}">${e.importance||''}</span></div>`).join("")||'<div class="fine">No upcoming events loaded.</div>';
 let changes=DATA.today_changes||[];
 $("#changesList").innerHTML=changes.length?changes.slice(0,10).map(x=>`<div class="change-row"><b>${esc(x.ticker)}</b><div class="change-pills">${x.changes.map(c=>`<span class="pill">${c}</span>`).join("")}</div></div>`).join(""):`<div class="fine">No prior snapshot yet. Changes appear after the next daily build.</div>`;
 let sig=DATA.tickers.filter(x=>x.entry?.label==='READY'||x.rs?.before_price||x.screeners?.flags?.vcp_ready).sort((a,b)=>(b.scores.entry??0)-(a.scores.entry??0)).slice(0,10);
 $("#todaySignals").innerHTML=sig.map(x=>`<div class="today-signal-row" data-t="${esc(x.ticker)}"><b>${esc(x.ticker)}</b><div>${screenBadges(x)}<small>${esc(x.company)}</small></div><span>RS ${x.rs.score}</span><span>${x.entry?.label||'—'}</span></div>`).join("");
 $$("#todaySignals .today-signal-row").forEach(e=>e.onclick=()=>{activate('workbench');selectStock(e.dataset.t)});
 $("#todaySectors").innerHTML=(DATA.groups||[]).slice(0,8).map(x=>`<div class="today-sector-row"><b>${x.rank}</b><div><b>${esc(x.group)}</b><small>${x.count} names · ${x.ready_count} ready</small></div><span>RS ${x.avg_rs}</span><span class="${(x.return_1m||0)>=0?'pos':'neg'}">${x.return_1m==null?'—':x.return_1m+'%'}</span></div>`).join("");
 let s=DATA.signal_scorecard||{};
 $("#scorecard").innerHTML=`<div class="scorecard-grid"><div class="stat"><small>Resolved signals</small><b>${s.resolved??0}</b></div><div class="stat"><small>Win rate</small><b>${s.win_rate==null?'—':s.win_rate+'%'}</b></div><div class="stat"><small>Avg +20D</small><b>${s.avg_20d==null?'—':s.avg_20d+'%'}</b></div><div class="stat"><small>Avg max move</small><b>${s.avg_max_move==null?'—':s.avg_max_move+'%'}</b></div></div>`;
 $$('[data-jump]').forEach(b=>b.onclick=()=>activate(b.dataset.jump));
}
function renderSetups(){
 let rows=DATA.tickers.filter(x=>x.patterns.primary).sort((a,b)=>b.scores.setup-a.scores.setup);
 $("#setupGrid").innerHTML=rows.map(x=>`<div class="setup-card" data-t="${esc(x.ticker)}"><div class="head"><div><b>${esc(x.ticker)}</b><div class="company">${esc(x.company)}</div></div><span class="status ${x.scores.status}">${x.scores.status}</span></div>
 <div class="section-title"><span>${x.patterns.primary}</span><span>RS ${x.rs.score}</span></div><div class="dual"><div><b>${x.scores.strength}</b><small>STRENGTH</small></div><div><b>${x.scores.setup}</b><small>SETUP</small></div></div></div>`).join("");
 $$("#setupGrid .setup-card").forEach(e=>e.onclick=()=>{activate("workbench");selectStock(e.dataset.t)});
}
function drawRS(){
 let can=$("#rsCanvas");if(!can)return;let r=can.getBoundingClientRect();if(r.width<50)return;let d=devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d),p=34,w=r.width,h=r.height;
 let X=v=>p+v/100*(w-2*p),Y=v=>h-p-v/100*(h-2*p),col=q=>({leading:"#35d07f",improving:"#5ea7ff",weakening:"#e9c85a",lagging:"#f06b6b"}[q]||"#aaa");
 c.clearRect(0,0,w,h);c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");c.beginPath();c.moveTo(X(50),p);c.lineTo(X(50),h-p);c.moveTo(p,Y(50));c.lineTo(w-p,Y(50));c.stroke();
 DATA.tickers.forEach(s=>{let x=X(s.rs.score||0),y=Y(s.rs.short||0);c.fillStyle=col(s.rs.quadrant);c.beginPath();c.arc(x,y,4,0,Math.PI*2);c.fill();c.fillStyle=getComputedStyle(document.body).getPropertyValue("--text");c.font="600 9px system-ui";c.fillText(s.ticker,x+6,y+3)});
}
function initCompare(){
 let top=DATA.tickers.slice(0,4).map(x=>x.ticker),opts=DATA.tickers.map(x=>`<option value="${esc(x.ticker)}">${esc(x.ticker)} · ${esc(x.company)}</option>`).join("");
 $("#compareSelectors").innerHTML=[0,1,2,3].map(i=>`<select data-i="${i}">${opts}</select>`).join("");
 $$("#compareSelectors select").forEach((s,i)=>{s.value=top[i]||DATA.tickers[0]?.ticker||"";s.onchange=renderCompare});renderCompare();
}
function renderCompare(){
 if(!DATA.tickers.length){$("#compareTable").innerHTML='<div class="empty-state">N/A — no verified stocks available.</div>';return}
 let names=$$("#compareSelectors select").map(s=>s.value),xs=names.map(n=>DATA.tickers.find(x=>x.ticker===n));
 let rows=[["Strength",x=>x.scores.strength],["Setup",x=>x.scores.setup],["Entry",x=>x.scores.entry],["Screen hits",x=>x.screeners?.count??0],["RS Score",x=>x.rs.score],["Short RS",x=>x.rs.short],["Trend",x=>`${x.trend_template.passed}/${x.trend_template.total}`],["Stage",x=>x.stage.value],["Pattern",x=>x.patterns.primary||"—"],["Pivot distance",x=>x.patterns.vcp?.distance_pct==null?"—":x.patterns.vcp.distance_pct+"%"],["EPS growth",x=>x.earnings?.eps_growth_yoy==null?"—":x.earnings.eps_growth_yoy+"%"],["Revenue growth",x=>x.earnings?.revenue_growth_yoy==null?"—":x.earnings.revenue_growth_yoy+"%"],["Macro fit",x=>x.v8?.macro_fit?.score==null?"—":x.v8.macro_fit.score+" · "+x.v8.macro_fit.state],["Status",x=>x.scores.status]];
 $("#compareTable").innerHTML=`<table><thead><tr><th>Metric</th>${xs.map(x=>`<th>${esc(x.ticker)}<div class="radar-mini">${esc(x.company)}</div></th>`).join("")}</tr></thead><tbody>${rows.map(([k,f])=>`<tr><td>${k}</td>${xs.map(x=>`<td>${f(x)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function drawHistory(x){
 let can=$("#historyCanvas"); if(!can)return;
 let r=can.getBoundingClientRect(),d=devicePixelRatio||1;can.width=r.width*d;can.height=r.height*d;let c=can.getContext("2d");c.scale(d,d);
 let h=x.score_history||[]; c.clearRect(0,0,r.width,r.height); if(h.length<2){c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.fillText("History builds from daily snapshots.",10,30);return}
 let p=20,w=r.width,ht=r.height,X=i=>p+i/(h.length-1)*(w-2*p),Y=v=>ht-p-v/100*(ht-2*p);
 c.strokeStyle=getComputedStyle(document.body).getPropertyValue("--line");c.beginPath();c.moveTo(p,Y(50));c.lineTo(w-p,Y(50));c.stroke();
 [["strength","#7ad7ff"],["setup","#35d07f"],["entry","#b68cff"],["rs","#e9c85a"]].forEach(([k,col])=>{c.strokeStyle=col;c.lineWidth=2;c.beginPath();h.forEach((z,i)=>i?c.lineTo(X(i),Y(z[k]??0)):c.moveTo(X(i),Y(z[k]??0)));c.stroke()});
 c.font="9px system-ui";c.fillStyle=getComputedStyle(document.body).getPropertyValue("--muted");c.fillText("Strength",p,11);c.fillText("Setup",p+58,11);c.fillText("Entry",p+96,11);c.fillText("RS",p+130,11);
}

function initScreenLab(){
 $("#nlQuery").addEventListener("input",runScreen);
 $$(".recipe").forEach(b=>b.onclick=()=>{$("#nlQuery").value=b.dataset.q;runScreen()});
 $("#nlQuery").value="RS 90 이상, VCP, pivot 5% 이내"; runScreen();
}
function parseScreen(q){
 q=(q||"").toLowerCase();
 let f={};
 let m=q.match(/rs\s*[>=]?\s*(\d{2})/); if(m)f.rs=+m[1];
 m=q.match(/setup\s*[>=]?\s*(\d{2})/); if(m)f.setup=+m[1];
 m=q.match(/strength\s*[>=]?\s*(\d{2})/); if(m)f.strength=+m[1];
 m=q.match(/stage\s*(\d)/); if(m)f.stage=+m[1];
 m=q.match(/pivot[^0-9]*(\d+(?:\.\d+)?)/); if(m)f.pivot=+m[1];
 if(q.includes("vcp"))f.vcp=true;
 if(q.includes("rs new high")||q.includes("rs신고가")||q.includes("rs 신고가"))f.rsnew=true;
 if(q.includes("volume breakthrough")||q.includes("거래량 돌파"))f.volbreak=true;
 if(q.includes("growth leader")||q.includes("성장주"))f.growth=true;
 if(q.includes("improving")||q.includes("개선"))f.quadrant="improving";
 if(q.includes("leading")||q.includes("주도"))f.quadrant="leading";
 if(q.includes("ready"))f.status="READY";
 if(q.includes("macro tailwind")||q.includes("매크로 순풍"))f.macroTailwind=true;
 if(q.includes("macro headwind")||q.includes("매크로 역풍"))f.macroHeadwind=true;
 if(q.includes("warning none")||q.includes("경고 없음"))f.noWarnings=true;
 return f;
}
function formulaText(f){
 let a=[]; if(f.rs)a.push(`RS ≥ ${f.rs}`); if(f.strength)a.push(`Strength ≥ ${f.strength}`); if(f.setup)a.push(`Setup ≥ ${f.setup}`);
 if(f.stage)a.push(`Stage = ${f.stage}`); if(f.vcp)a.push("VCP detected"); if(f.pivot!=null)a.push(`Pivot distance 0–${f.pivot}%`);
 if(f.rsnew)a.push("RS new high");if(f.volbreak)a.push("Volume breakthrough");if(f.growth)a.push("Growth leader");
 if(f.macroTailwind)a.push("Macro fit ≥ 62");if(f.macroHeadwind)a.push("Macro fit ≤ 38");
 if(f.quadrant)a.push(`Quadrant = ${f.quadrant}`); if(f.status)a.push(`Status = ${f.status}`); if(f.noWarnings)a.push("Warning count = 0");
 return a.length?a.join("  AND  "):"Recognized filters will appear here.";
}
function runScreen(){
 let f=parseScreen($("#nlQuery").value), rows=DATA.tickers.filter(x=>{
   if(f.rs && (x.rs.score||0)<f.rs)return false;if(f.strength && (x.scores.strength||0)<f.strength)return false;if(f.setup && (x.scores.setup||0)<f.setup)return false;
   if(f.stage && x.stage.value!==f.stage)return false;if(f.vcp && !x.patterns.vcp?.detected)return false;
   if(f.pivot!=null){let d=x.patterns.vcp?.distance_pct;if(d==null||d<0||d>f.pivot)return false}
   if(f.rsnew && !x.rs.rs_new_high)return false;if(f.volbreak && !x.technicals?.volume_breakthrough?.detected)return false;
   if(f.growth && !x.screeners?.flags?.growth_leader)return false;
   if(f.macroTailwind && (x.v8?.macro_fit?.score??0)<62)return false;
   if(f.macroHeadwind && (x.v8?.macro_fit?.score??100)>38)return false;
   if(f.quadrant && x.rs.quadrant!==f.quadrant)return false;if(f.status && x.scores.status!==f.status)return false;if(f.noWarnings && (x.warnings||[]).length)return false;
   return true
 }).sort((a,b)=>(b.scores.strength+b.scores.setup)-(a.scores.strength+a.scores.setup));
 $("#parsedFormula").textContent=formulaText(f);$("#screenCount").textContent=`${rows.length} names`;
 $("#screenResults").innerHTML=rows.slice(0,80).map(x=>`<div class="row" data-t="${esc(x.ticker)}"><div><div class="ticker-line"><span class="ticker">${esc(x.ticker)}</span><span class="status ${x.scores.status}">${x.scores.status}</span></div><div class="company">${esc(x.company)}</div></div><div class="mini-score"><b>${x.scores.strength}</b><small>STR</small></div><div class="mini-score"><b>${x.scores.setup}</b><small>SETUP</small></div></div>`).join("");
 $$("#screenResults .row").forEach(e=>e.onclick=()=>{activate("workbench");selectStock(e.dataset.t)})
}

function activate(id){$$(".tabs button").forEach(b=>b.classList.toggle("active",b.dataset.tab===id));$$(".view").forEach(v=>v.classList.toggle("active",v.id===id));if(id==="rsmap")setTimeout(drawRS,30);if(id==="markethealth")setTimeout(drawBreadth,30);if(id==="macrofull")setTimeout(drawMacroHistory,30);if(id==="historyexplorer")setTimeout(loadHistorySelected,30);if(V11_FOCUS[id])setTimeout(renderV11FocusTabs,20);if(id==="datahealth")setTimeout(renderDataHealth,20)}
$$(".tabs button").forEach(b=>b.onclick=()=>activate(b.dataset.tab));
$("#refreshBtn").onclick=()=>location.reload();$("#themeBtn").onclick=()=>{document.body.classList.toggle("light");selectStock(selected);drawRS()};$("#densityBtn").onclick=()=>document.body.classList.toggle("compact-ui");
window.addEventListener("resize",()=>{if(selected)selectStock(selected);if($("#rsmap").classList.contains("active"))drawRS()});
