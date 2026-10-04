/* Localized presentation only. Financial values and source histories are never altered. */
(() => {
  const KEY_LANGUAGE = "rsradar_language";
  const KEY_DESIGN = "rsradar_design";
  const designs = ["terminal", "paper", "contrast"];
  const ko = {
    "MARKET DISCOVERY TERMINAL":"시장 탐색 터미널","HOME":"홈","STOCKS":"주식","MACRO":"거시경제",
    "COMMODITIES":"원자재","RESEARCH":"기업 분석","PORTFOLIO":"포트폴리오",
    "Today":"오늘","Dashboard":"대시보드","Data Health":"데이터 상태","Screener":"종목 검색",
    "RS":"상대강도","RS Map":"RS 지도","Setups":"매매 준비 신호","Rankings":"순위",
    "Groups":"그룹","Sector":"섹터","Research":"종목 분석","Compare":"비교","Intelligence":"종목 정보",
    "Screen Lab":"조건 검색실","Workbench":"분석 작업대","Macro Overview":"거시경제 개요",
    "Rates":"금리","Yield Curve":"수익률 곡선","Inflation":"물가","Growth":"성장",
    "Labor":"고용","Liquidity":"유동성","Credit":"신용","Financial Conditions":"금융 여건",
    "FX":"외환","Housing":"주택","Calendar":"경제 일정","History":"전체 이력",
    "Overview":"개요","Energy":"에너지","Metals":"금속","Agriculture":"농산물",
    "EIA Inventories":"EIA 재고","Intermarket":"자산 간 비교","Earnings":"실적",
    "Estimates":"시장 예상치","Valuation":"가치평가","Ownership":"보유 현황",
    "Insider":"내부자 거래","Short":"공매도","Catalysts":"주요 변수",
    "Replay":"과거 재현","Signal Scorecard":"신호 성적표","Watchlist":"관심 종목",
    "Alerts":"알림","Portfolio":"포트폴리오","Correlation":"상관관계",
    "Risk":"위험","Stress Test":"스트레스 테스트","Design":"디자인","Language":"언어",
    "Terminal":"터미널","Editorial":"리포트","High contrast":"고대비",
    "Verified stocks":"검증된 종목","Available series":"사용 가능한 시계열",
    "Retained cached series":"이전 수집값 유지","Unavailable series":"사용 불가 시계열",
    "SOURCE · FRESHNESS · COVERAGE":"출처 · 최신성 · 범위",
    "What is loaded, where it came from, and how much history is available.":"수집된 데이터의 출처, 시점과 이력 범위를 확인하세요.",
    "Refresh status":"상태 새로고침","PROVIDERS":"제공처","provenance":"출처",
    "HISTORY COVERAGE":"이력 범위","series / observations":"시계열 / 관측값",
    "Source":"출처","Status":"상태","Available / OK":"사용 가능 / 정상",
    "Last success":"마지막 성공","Last attempt":"마지막 시도","Duration":"소요 시간",
    "Error":"오류","Series":"시계열","As of":"기준일","Cache age":"저장값 경과",
    "Observations":"관측값","ok":"정상","stale":"이전 수집값","unavailable":"사용 불가",
    "PARTIAL DATA":"일부 데이터","VERIFIED SNAPSHOT":"검증된 데이터",
    "UNAVAILABLE":"사용 불가","Loading verified data…":"검증된 데이터를 불러오는 중…",
    "TICKER":"종목","Ticker":"종목","Company":"회사","Industry":"산업",
    "Price $":"가격 $","Price":"가격","Strength":"강도","Setup":"준비 신호",
    "Entry":"진입","Quality":"품질","Revision":"예상치 변화","Catalyst":"주요 변수",
    "Macro Fit":"거시환경 적합도","Stage":"단계","Market cap $":"시가총액 $",
    "Revenue YoY %":"매출 전년비 %","EPS YoY %":"EPS 전년비 %",
    "Net margin %":"순이익률 %","FCF $":"잉여현금흐름 $",
    "Insider net $":"내부자 순거래 $","Institutional shares":"기관 보유주식",
    "Short-sale %":"공매도 거래량 %","Short RS":"단기 RS",
    "Stock Screener":"종목 검색","UNIVERSE EXPLORER":"전체 종목 탐색",
    "Sector Rotation":"섹터 순환","CONSTITUENT GROUP RANKINGS":"구성 종목 그룹 순위",
    "separate RS calculation":"별도 RS 계산",
    "Materials Sector ETF":"소재 섹터 ETF","Communication Services Sector ETF":"커뮤니케이션 섹터 ETF",
    "Energy Sector ETF":"에너지 섹터 ETF","Financials Sector ETF":"금융 섹터 ETF",
    "Industrials Sector ETF":"산업재 섹터 ETF","Technology Sector ETF":"기술주 섹터 ETF",
    "Consumer Staples Sector ETF":"필수소비재 섹터 ETF","Real Estate Sector ETF":"부동산 섹터 ETF",
    "Utilities Sector ETF":"유틸리티 섹터 ETF","Health Care Sector ETF":"헬스케어 섹터 ETF",
    "Consumer Discretionary Sector ETF":"경기소비재 섹터 ETF",
    "Nasdaq-100 ETF":"나스닥100 ETF","Russell 2000 ETF":"러셀2000 ETF",
    "Sector and broad-market ETF prices are USD per share. Fund returns exclude cash distributions and are separate from the constituent group RS rankings below.":"섹터 및 시장 ETF 가격은 1주당 달러입니다. 수익률은 현금 분배금을 제외하며, 아래 구성 종목 그룹의 RS 순위와 별개입니다.",
    "Search":"검색","Metric":"지표","Minimum":"최솟값","Maximum":"최댓값",
    "Signal":"신호","Any":"무관","Any signal":"모든 신호","VCP Ready":"VCP 준비",
    "Volume Breakout":"거래량 돌파","RS Before Price":"가격보다 앞선 RS",
    "RS New High":"RS 신고가","Trend Leader":"추세 주도주","Entry Ready":"진입 준비",
    "Table":"표","Chart":"차트","Heatmap":"히트맵","Columns":"열",
    "Screen name":"검색식 이름","Save screen":"검색식 저장","Saved screens":"저장한 검색식",
    "Delete saved":"저장본 삭제","Export CSV":"CSV 내보내기","Reset":"초기화",
    "All sectors":"전체 섹터","All industries":"전체 산업",
    "Missing metrics are excluded by numeric filters. Short-sale volume is distinct from short interest. Saved screens stay on this browser.":"값이 없는 지표는 수치 필터에서 제외됩니다. 공매도 거래량과 공매도 잔고는 다릅니다. 저장한 검색식은 이 브라우저에만 남습니다.",
    "No matching verified stocks":"조건에 맞는 검증된 종목이 없습니다",
    "Adjust filters or inspect Data Health.":"조건을 바꾸거나 데이터 상태를 확인하세요.",
    "Stock data unavailable":"종목 데이터를 사용할 수 없습니다",
    "No verified stock signals available.":"검증된 종목 신호가 없습니다.",
    "Sector ranking requires validated equity prices.":"섹터 순위에는 검증된 주가가 필요합니다.",
    "MARKET REGIME":"시장 국면","Market regime":"시장 국면","MARKET QUALITY":"시장 품질","Market quality":"시장 품질",
    "ABOVE 200DMA":"200일선 위","Above 200DMA":"200일선 위","A/D RATIO":"상승/하락 비율","A/D ratio":"상승/하락 비율",
    "BREADTH":"시장 확산도","EVENT RISK":"일정 위험","CREDIT":"신용",
    "MACRO REGIME":"거시경제 국면","OFFICIAL SOURCE OBSERVATIONS":"공식 출처 관측값",
    "Macro Pulse":"거시경제 주요 지표","Macro overview":"거시경제 개요",
    "NEXT MARKET MOVERS":"예정된 주요 발표","Upcoming Events":"예정된 일정",
    "Full calendar":"전체 일정","CHANGE DETECTION":"변화 감지","What Changed":"달라진 점",
    "NEW / READY":"신규 / 준비","Stock Signals":"종목 신호",
    "LEADERSHIP":"주도 업종","Sector Rotation":"섹터 순환",
    "ENGINE VALIDATION":"신호 검증","Resolved signals":"결과 확정 신호",
    "Win rate":"승률","Avg +20D":"20거래일 평균","Avg max move":"최대 상승폭 평균",
    "Signals are resolved after 20 trading days.":"신호 결과는 20거래일 후 확정됩니다.",
    "Each tile shows its observation date and collection status. Open a tile for its full history.":"각 지표에 관측일과 수집 상태가 표시됩니다. 클릭하면 전체 이력을 볼 수 있습니다.",
    "No prior snapshot yet. Changes appear after the next daily build.":"이전 스냅샷이 없습니다. 다음 일일 수집 후 변화가 표시됩니다.",
    "MIXED":"혼조","PRESSURE":"압박","UPTREND":"상승세","DOWNTREND":"하락세",
    "REFLATION":"재팽창","BALANCED":"균형","READY":"준비","HIGH":"높음",
    "US Treasury 2Y":"미국 국채 2년","US Treasury 10Y":"미국 국채 10년",
    "Core CPI YoY":"근원 소비자물가 전년비","Unemployment Rate":"실업률",
    "Broad Trade-Weighted Dollar Index":"무역가중 달러지수","WTI Spot Price":"WTI 현물유가",
    "CBOE VIX Daily Close":"VIX 일일 종가",
    "Information Technology":"정보기술","Health Care":"헬스케어","Industrials":"산업재",
    "Financials":"금융","Communication Services":"커뮤니케이션",
    "Materials":"소재","Consumer Discretionary":"경기소비재",
    "MEDIUM":"보통","LOW":"낮음","cached inputs":"이전 수집값 포함",
    "OUR CALCULATIONS":"자체 계산","PARTICIPATION, NOT JUST INDEX PRICE":"지수보다 시장 참여도",
    "Market Health":"시장 상태","ADVANCE PARTICIPATION":"상승 종목 참여",
    "STOCKBEE-STYLE PARTICIPATION":"시장 참여 지표","our calculations":"자체 계산",
    "MARKET QUALITY COMPONENTS":"시장 품질 구성","0–100 total":"총점 0–100",
    "GROWTH × INFLATION × LIQUIDITY":"성장 × 물가 × 유동성",
    "Macro Regime":"거시경제 국면","MACRO HISTORY":"거시경제 이력",
    "daily snapshot score":"일별 스냅샷 점수","OFFICIAL + MARKET DATA":"공식 및 시장 데이터",
    "Macro Tape":"거시경제 지표","MARKET PROXIES":"시장 대용 지표",
    "RATES & CURVE":"금리와 수익률 곡선","GROWTH & LABOR":"성장과 고용",
    "SECTOR MACRO FIT":"섹터별 거시환경 적합도","heuristic context":"참고용 추정",
    "FULL HISTORICAL DATABASE":"전체 과거 데이터베이스","History Explorer":"이력 탐색",
    "Dataset":"데이터셋","All datasets":"전체 데이터셋","Macro / FRED":"거시경제 / FRED",
    "Intermarket ratios":"자산 간 비율","EIA inventories":"EIA 재고",
    "Market proxies":"시장 대용 지표","Overlay / normalize":"겹쳐 비교 / 정규화",
    "None":"없음","RANGE":"기간","Export selected history CSV":"선택 이력 CSV 내보내기",
    "HISTORICAL CALENDAR":"과거 경제 일정","Year":"연도","Historical series":"과거 시계열",
    "OBSERVATIONS":"관측값","all rows in selected range · newest first":"선택 기간 전체 · 최신순",
    "SCHEDULE ARCHIVE":"발표 일정 보관함","Date":"날짜","Value":"값","Raw":"원자료",
    "First":"처음","Previous":"이전","Next":"다음","Last":"마지막","Page":"페이지",
    "Newest observations":"최신 관측값","Oldest observations":"가장 오래된 관측값",
    "ENERGY · METALS · AGRICULTURE":"에너지 · 금속 · 농산물",
    "Commodity Board":"원자재 현황","COMMODITY-LINKED ETFs":"원자재 연계 ETF",
    "USD per fund share":"펀드 1주당 USD","FUTURES CONTRACTS":"선물 계약",
    "separate price feed":"별도 가격 수집원","INTERMARKET RATIOS":"자산 간 비율",
    "derived":"계산값","weekly":"주간","weekly history":"주간 이력",
    "WHAT CAN MOVE THE MARKET NEXT?":"다가오는 시장 일정",
    "Macro Event Calendar":"거시경제 발표 일정","All":"전체","High impact":"영향 큼",
    "Economic":"경제지표","Central Bank":"중앙은행","Treasury":"미 국채",
    "NEXT 7 DAYS":"향후 7일","event risk":"일정 위험","CALENDAR SOURCES":"일정 출처",
    "official":"공식","Date ET":"미 동부 날짜","Time ET / KST":"미 동부 / 한국 시간",
    "Event":"발표","Importance":"중요도","Forecast":"예상","Actual":"실제",
    "Surprise":"예상 대비","No verified events loaded for the next week.":"향후 일주일에 검증된 일정이 없습니다.",
    "CONNECTED COMPANY RESEARCH":"연결된 기업 분석","Stock Research":"종목 분석",
    "Select company in Research":"분석할 기업 선택","Manage watchlist & holdings":"관심 종목과 보유 수량 관리",
    "No verified data":"검증된 데이터 없음","Loading":"불러오는 중",
    "Close stock quick view":"종목 빠른 보기 닫기","Search ticker, company, or economic series":"종목·회사·경제 시계열 검색",
    "Open navigation":"메뉴 열기","Toggle density":"화면 밀도 전환","Refresh":"새로고침",
    "Next design":"다음 디자인","Stock quick view":"종목 빠른 보기",
    "TICKER / COMPANY":"종목 / 회사","Rank":"순위","Group":"그룹",
    "Nasdaq historical quotes":"Nasdaq 과거 시세",
    "full history via FRED":"전체 이력 FRED 제공",
    "Market Dashboard":"시장 대시보드","Market breadth":"시장 확산도",
    "Stock universe":"종목 범위","Macro risk":"거시경제 위험",
    "Stock screener":"종목 검색","Select company in Research":"분석할 기업 선택",
    "Ready":"준비","Export":"내보내기","N/A":"N/A"
  };
  const phrases = [
    [/^End-of-day quotes: (\d+) stocks · ([\d.]+)% universe coverage\. Price returns exclude cash dividends\. Check source dates and Data Health\.$/g, "장마감 시세: $1개 종목 · 대상 종목 $2% 확보. 가격 수익률에는 현금 배당이 포함되지 않습니다. 관측일과 데이터 상태를 확인하세요."],
    [/^(\w+) · quality (\d+)$/g, "$1 · 품질 $2"],
    [/^risk ([\d.]+) · (\w+)\s*· cached inputs$/g, "위험 $1 · $2 · 이전 수집값 포함"],
    [/^([\d.]+)% advancing$/g, "상승 종목 $1%"],
    [/^credit axis ([\d.]+)$/g, "신용 점수 $1"],
    [/^(\d+) high$/g, "높은 위험 $1건"],
    [/^(\d+) in 30D$/g, "30일 내 $1건"],
    [/^(\d+) names · (\d+) ready$/g, "$1개 종목 · $2개 준비"],
    [/^ok · full history via FRED$/g, "정상 · 전체 이력 FRED 제공"],
    [/\bMIXED\b/g, "혼조"],[/\bBALANCED\b/g, "균형"],
    [/\bStocks (\d{4}-\d{2}-\d{2}|N\/A) · build\b/g, "주식 $1 · 생성"],
    [/\b(\d[\d,]*) stocks\b/g, "$1개 종목"],
    [/\b(\d[\d,]*) observations\b/g, "$1개 관측값"],
    [/\bAs of (\d{4}-\d{2}-\d{2})\b/g, "$1 기준"],
    [/\bUpdated (\d{4}-\d{2}-\d{2})\b/g, "$1 업데이트"],
    [/\bPrior observation Δ\b/g, "직전 관측값 대비 Δ"],
    [/\bMethod:\s*/g, "방법: "],
    [/\b(\d[\d,]*) of (\d[\d,]*) observations\b/g, "$2개 관측값 중 $1번째"],
    [/\bNo verified events loaded for the next week\.\b/g, "향후 일주일에 검증된 일정이 없습니다."]
  ];
  let language;
  try { language = localStorage.getItem(KEY_LANGUAGE) === "en" ? "en" : "ko"; }
  catch { language = "ko"; }
  let design;
  try { design = localStorage.getItem(KEY_DESIGN) || "terminal"; } catch { design = "terminal"; }
  if (!designs.includes(design)) design = "terminal";
  const read = new WeakMap(), shown = new WeakMap();
  const attrRead = new WeakMap(), attrShown = new WeakMap();
  const translate = value => {
    if (language === "en") return value;
    const trimmed = value.trim();
    if (!trimmed) return value;
    if (Object.hasOwn(ko, trimmed)) return value.replace(trimmed, ko[trimmed]);
    return phrases.reduce((s, [pattern, replacement]) => s.replace(pattern, replacement), value);
  };
  function translateText(node) {
    const previous = shown.get(node);
    if (!read.has(node) || (node.nodeValue !== previous && node.nodeValue !== read.get(node))) read.set(node, node.nodeValue);
    const result = translate(read.get(node));
    if (node.nodeValue !== result) node.nodeValue = result;
    shown.set(node, result);
  }
  function translateAttributes(el) {
    let originals = attrRead.get(el), rendered = attrShown.get(el);
    if (!originals) { originals = {}; rendered = {}; attrRead.set(el, originals); attrShown.set(el, rendered); }
    for (const name of ["placeholder", "title", "aria-label"]) {
      if (!el.hasAttribute(name)) continue;
      const current = el.getAttribute(name);
      if (!(name in originals) || (current !== rendered[name] && current !== originals[name])) originals[name] = current;
      const result = translate(originals[name]);
      if (current !== result) el.setAttribute(name, result);
      rendered[name] = result;
    }
  }
  function walk(root) {
    if (root.nodeType === Node.TEXT_NODE) { translateText(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(root.tagName)) return;
    translateAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.nodeType === Node.TEXT_NODE) {
        if (!/^(SCRIPT|STYLE|NOSCRIPT)$/.test(node.parentElement?.tagName)) translateText(node);
      } else translateAttributes(node);
    }
  }
  function applyLanguage() {
    document.documentElement.lang = language;
    document.querySelector("#languageSelect").value = language;
    for (const el of document.querySelectorAll("[data-pref-label]")) {
      el.textContent = el.dataset.prefLabel === "design" ? (language === "ko" ? "디자인" : "Design") : (language === "ko" ? "언어" : "Language");
    }
    walk(document.body);
  }
  function applyDesign() {
    document.body.dataset.design = design;
    document.querySelector("#designSelect").value = design;
    // Existing canvas charts use CSS variables; redraw only charts already visible.
    if (typeof selected !== "undefined" && selected && typeof selectStock === "function") selectStock(selected);
    if (document.querySelector("#rsmap.active") && typeof drawRS === "function") drawRS();
  }
  document.querySelector("#languageSelect").addEventListener("change", event => {
    language = event.target.value === "en" ? "en" : "ko";
    try { localStorage.setItem(KEY_LANGUAGE, language); } catch {}
    applyLanguage();
  });
  document.querySelector("#designSelect").addEventListener("change", event => {
    design = designs.includes(event.target.value) ? event.target.value : "terminal";
    try { localStorage.setItem(KEY_DESIGN, design); } catch {}
    applyDesign();
  });
  document.querySelector("#themeBtn").onclick = () => {
    design = designs[(designs.indexOf(design) + 1) % designs.length];
    try { localStorage.setItem(KEY_DESIGN, design); } catch {}
    applyDesign();
  };
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === "characterData") translateText(record.target);
      else if (record.type === "attributes") translateAttributes(record.target);
      else for (const node of record.addedNodes) walk(node);
    }
  }).observe(document.body, { childList:true, characterData:true, attributes:true, attributeFilter:["placeholder","title","aria-label"], subtree:true });
  applyDesign();
  applyLanguage();
})();
