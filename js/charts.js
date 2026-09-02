function drawACWIChart(history, period, canvasId="acwiChart") {
  const canvas=document.getElementById(canvasId);
  if(!canvas||!history||!Array.isArray(history.acwi)) return;
  const points=filterPeriod(history,period).filter(p=>Number.isFinite(Number(p.value)));
  if(points.length<2)return;
  const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  const width=Math.max(300,Math.round(rect.width||canvas.clientWidth||600)),height=Math.max(140,Math.round(rect.height||canvas.clientHeight||155));
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  const ctx=canvas.getContext("2d");if(!ctx)return;
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
  const pad={left:42,right:16,top:18,bottom:28};
  const vals=points.map(p=>Number(p.value));
  const min=Math.min(...vals),max=Math.max(...vals),range=max-min||1;
  const x=i=>pad.left+i*(width-pad.left-pad.right)/Math.max(1,points.length-1),y=v=>height-pad.bottom-(v-min)/range*(height-pad.top-pad.bottom);
  ctx.strokeStyle="#223743";ctx.lineWidth=1;
  for(let i=0;i<4;i++){const yy=pad.top+i*(height-pad.top-pad.bottom)/3;ctx.beginPath();ctx.moveTo(pad.left,yy);ctx.lineTo(width-pad.right,yy);ctx.stroke()}
  ctx.strokeStyle="#e85b5b";ctx.lineWidth=2.2;ctx.beginPath();points.forEach((p,i)=>{const xx=x(i),yy=y(Number(p.value));if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy)});ctx.stroke();
  ctx.fillStyle="#8fa4b2";ctx.font="10px system-ui,sans-serif";
  ctx.fillText(points[0].date||"",pad.left,height-8);ctx.fillText(points[points.length-1].date||"",Math.max(pad.left,width-70),height-8);ctx.fillText(max.toFixed(0),6,pad.top+4);ctx.fillText(min.toFixed(0),6,height-pad.bottom);
}
function filterPeriod(history,period){const values=Array.isArray(history?.acwi)?history.acwi:[],dates=Array.isArray(history?.dates)?history.dates:[];const n={"1y":252,"3y":756,"5y":1260,"all":values.length}[period]||252;const start=Math.max(0,values.length-n);return values.slice(start).map((value,i)=>({value,date:dates[start+i]||""}))}
(function(){
  const ABOUT={
    "ACWI":"Broad global equity trend versus the 200-day moving average. It answers a simple question: is the world equity market currently moving with the longer-term trend or against it?",
    "US equities":"S&P 500 trend versus its 200-day moving average. It is useful for judging whether the largest developed equity market is supporting or weakening the global trend.",
    "Europe":"European equity trend versus its 200-day moving average. It helps show whether Europe is participating in the broader global equity trend.",
    "Emerging markets":"Emerging-market equity trend versus its 200-day moving average. EM can diverge materially from developed markets, so this adds diversification context.",
    "US volatility (VIX)":"Option-implied expected volatility for US equities over roughly the next 30 days. Higher readings mean investors are paying more for protection and uncertainty is more strongly priced.",
    "Europe volatility (VSTOXX)":"Option-implied expected volatility for European equities. A high reading means a larger amount of near-term uncertainty is already reflected in option prices.",
    "Emerging-market volatility (VXEEM)":"Option-implied expected volatility for emerging-market equities. It is particularly useful for spotting whether EM risk is being priced materially above normal conditions.",
    "ACWI drawdown":"Distance of ACWI from its running high. Near zero means the market is close to a recent peak; a large negative value means a meaningful decline is already underway.",
    "US CAPE":"S&P 500 valuation relative to ten years of inflation-adjusted earnings. It is a slow-moving valuation measure, mainly useful for judging long-term return expectations rather than short-term timing.",
    "US 10Y yield":"Benchmark US government bond yield. It affects discount rates, borrowing costs and the relative attractiveness of bonds versus equities.",
    "Gold":"Gold price as a cross-asset signal. It can reflect a mix of inflation concerns, real-rate expectations, currency confidence and defensive demand."
  };
  function esc(v){return String(v??"—").replace(/[&<>\"']/g,s=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]))}
  function ensure(){
    if(!document.getElementById("metricModal"))document.body.insertAdjacentHTML("beforeend",'<div id="metricModal" class="metric-modal" hidden><div class="metric-modal-backdrop" data-close-modal></div><section class="metric-modal-dialog"><button class="metric-modal-close" data-close-modal aria-label="Close">×</button><div class="eyebrow">INDICATOR DETAIL</div><h2 id="metricModalTitle"></h2><div id="metricModalBody"></div></section></div>');
    if(!document.getElementById("chartModal"))document.body.insertAdjacentHTML("beforeend",'<div id="chartModal" class="metric-modal" hidden><div class="metric-modal-backdrop" data-close-chart></div><section class="metric-modal-dialog chart-modal-dialog"><button class="metric-modal-close" data-close-chart aria-label="Close">×</button><div class="eyebrow">GLOBAL EQUITY HISTORY</div><h2>ACWI</h2><div class="chart-modal-card"><canvas id="acwiChartModal"></canvas></div></section></div>');
  }
  function rangeFor(item){return {"ACWI":[-5,10],"US equities":[-5,10],"Europe":[-7,10],"Emerging markets":[-7,12],"US volatility (VIX)":[12,20],"Europe volatility (VSTOXX)":[15,25],"Emerging-market volatility (VXEEM)":[18,28],"ACWI drawdown":[-10,0],"US CAPE":[15,25],"US 10Y yield":[2,4.5],"Gold":[1500,3000]}[item.name]||null}
  function formatRangeValue(v,item){if(!Number.isFinite(v))return "—";if(item.name==="Gold")return `$${Number(v).toLocaleString()}`;if(item.name==="US 10Y yield")return `${Number(v).toFixed(1)}%`;return Number.isInteger(v)?String(v):Number(v).toFixed(1)}
  function band(item,caption=true){
    if(!item?.band)return'';const b=item.band,min=+b.p05,max=+b.p95,now=+item.current,r=rangeFor(item);
    if(!r||![min,max,now].every(Number.isFinite)||max===min)return'';
    const lo=Math.min(...r),hi=Math.max(...r),pct=v=>Math.max(0,Math.min(100,(v-min)/(max-min)*100)),l=pct(lo),w=Math.max(0,pct(hi)-l),p=pct(now);
    const labels=`<div class="band-label-row"><span style="left:0">${esc(formatRangeValue(min,item))}</span><span style="left:${l}%;transform:translateX(-50%)">${esc(formatRangeValue(lo,item))}</span><span style="left:${pct(hi)}%;transform:translateX(-50%)">${esc(formatRangeValue(hi,item))}</span><span style="left:100%;transform:translateX(-100%)">${esc(formatRangeValue(max,item))}</span></div>`;
    const cap=caption?`<div class="band-caption modal-typical-only"><span>Typical range: ${esc(formatRangeValue(lo,item))} – ${esc(formatRangeValue(hi,item))}</span></div>`:'';
    return `${labels}<div class="band"><div class="band-track"></div><div class="band-typical" style="left:${l}%;width:${w}%"></div><div class="band-now" style="left:${p}%"></div></div>${cap}`;
  }
  function analysis(it){
    const r=rangeFor(it),v=Number(it.current),name=it.name;if(!r||!Number.isFinite(v))return "No current reading is available for a conclusion.";
    const lo=Math.min(...r),hi=Math.max(...r),mid=(lo+hi)/2;
    if(name.includes("volatility")){if(v<lo)return "Volatility is below the typical zone. The market is relatively calm, so there is little stress priced in. Conclusion: this is not a strong defensive signal; continue with the normal long-term plan.";if(v>hi)return "Volatility is above the typical zone. More uncertainty and demand for protection are already priced in. Conclusion: risk has risen, but higher volatility alone is not a reason to stop a disciplined investment plan.";return "Volatility is inside the typical zone. Stress is neither unusually low nor unusually high. Conclusion: no strong volatility-based reason to change the long-term plan."}
    if(name==="ACWI drawdown"){if(v>=-3)return "ACWI is close to its recent high. The market has not experienced a meaningful pullback. Conclusion: there is little drawdown-based evidence of a broad stress event.";if(v<=lo)return "ACWI is in a deep drawdown relative to its recent high. A substantial decline is already visible. Conclusion: the market is stressed, but the dashboard cannot tell us where the bottom is; follow the predefined investment rule rather than trying to time it.";return `ACWI is ${Math.abs(v).toFixed(1)}% below its running high. That is a noticeable pullback, but not an extreme one. Conclusion: some stress is present, yet the reading alone does not justify changing a long-term DCA plan.`}
    if(name==="US CAPE"){if(v>hi)return "Valuation is well above the typical long-term zone. This points to expensive US equities and lower prospective long-term returns than at normal valuations. Conclusion: avoid treating strong recent performance as proof that equities are cheap.";if(v<lo)return "Valuation is below the typical long-term zone. That suggests better long-term expected returns than normal, although timing remains uncertain. Conclusion: valuation is supportive rather than a short-term timing signal.";return "Valuation is inside the typical long-term zone. Conclusion: the US market is neither obviously cheap nor at an extreme by this dashboard's rule, so other signals matter more for the next decision."}
    if(name==="US 10Y yield"){if(v>hi)return "The 10-year yield is above the typical zone. Higher yields generally tighten financial conditions and make future cash flows less valuable. Conclusion: this is a headwind for expensive assets, although it does not by itself call for a change in a long-term allocation.";if(v<lo)return "The 10-year yield is below the typical zone. Financial conditions are relatively supportive from a discount-rate perspective. Conclusion: bond yields are not currently an obvious valuation headwind.";return `The 10-year yield is within the typical zone at ${v.toFixed(2)}%. Conclusion: bond pricing is not at an extreme level by this dashboard's range, so it should be read together with equity valuation and risk.`}
    if(name==="Gold"){if(v>hi)return "Gold is above the typical zone. That can indicate unusually strong defensive demand, inflation concern or low confidence in real assets/currencies. Conclusion: useful as a warning about cross-asset uncertainty, but not a standalone equity sell signal.";if(v<lo)return "Gold is below the typical zone. Defensive demand is relatively subdued. Conclusion: gold is not currently signalling an unusual flight to safety.";return "Gold is within the typical zone. Conclusion: it is providing background diversification information rather than a strong directional signal for equities."}
    if(name.includes("equities")||name==="Europe"||name==="Emerging markets"||name==="ACWI"){
      if(v<lo)return "The equity trend is below its typical zone and therefore weaker than normal. Conclusion: trend conditions are a headwind; be cautious about interpreting short-term rebounds as a confirmed trend change.";
      if(v>hi)return "The equity trend is above its typical zone and therefore unusually strong. Conclusion: momentum is supportive, but the strength itself is not evidence that valuations are attractive.";
      if(v>=mid)return "The equity trend is inside the typical zone and on the stronger side of it. Conclusion: the trend is supportive, but not extreme.";
      return "The equity trend is inside the typical zone but on the weaker side. Conclusion: the market is not in a major trend break, but conditions are less supportive than normal.";
    }
    return `Current value ${v} sits within the dashboard's typical zone. Conclusion: treat this as context rather than a standalone buy or sell signal.`;
  }
  const stores={metrics:[],priced:[]};
  function render(data){
    stores.metrics=[...(data.equities||[]),...(data.risk||[]),...(data.valuation||[]),...(data.cross_asset||[])];
    const groups=[['equityGrid',data.equities||[],0],['riskGrid',data.risk||[],(data.equities||[]).length],['valuationGrid',data.valuation||[],(data.equities||[]).length+(data.risk||[]).length],['crossAssetGrid',data.cross_asset||[],(data.equities||[]).length+(data.risk||[]).length+(data.valuation||[]).length]];
    groups.forEach(([id,arr,offset])=>{const el=document.getElementById(id);if(el)el.innerHTML=arr.map((it,i)=>`<article class="metric-card" tabindex="0" role="button" data-midx="${offset+i}"><div class="metric-top"><div class="metric-name">${esc(it.name)}</div></div><div class="metric-value">${esc(it.display)}</div><div class="metric-meta">${esc(it.detail)}</div>${band(it,true)}</article>`).join('')});
    const pe=document.getElementById('pricedInGrid');stores.priced=data.priced_in||[];if(pe)pe.innerHTML=stores.priced.map((it,i)=>`<article class="priced-card" tabindex="0" role="button" data-pidx="${i}"><h4>${esc(it.name)}</h4><div class="big">${esc(it.display)}</div><p>${esc(it.explanation)}</p></article>`).join('');
  }
  function openMetric(it,priced=false){
    ensure();document.getElementById('metricModalTitle').textContent=it.name||'Indicator';
    if(priced)document.getElementById('metricModalBody').innerHTML=`<div class="modal-top"><div class="modal-value-side"><div class="modal-big-value">${esc(it.display)}</div></div><aside class="modal-info"><div class="eyebrow">ABOUT / CONCLUSION</div><p>${esc(it.explanation||'Market-derived signal used for context.')}</p></aside></div>`;
    else document.getElementById('metricModalBody').innerHTML=`<div class="modal-top"><div class="modal-value-side"><div class="modal-big-value">${esc(it.display)}</div><p class="modal-detail">${esc(it.detail||'')}</p></div><aside class="modal-info"><div class="eyebrow">ABOUT / CONCLUSION</div><p>${esc(ABOUT[it.name]||it.detail||'This indicator provides context for current market conditions.')}</p><p class="modal-conclusion"><strong>Current reading:</strong> ${esc(analysis(it))}</p></aside></div><div class="modal-tracker">${band(it,true)}</div>`;
    const m=document.getElementById('metricModal');m.hidden=false;m.setAttribute('aria-hidden','false');document.body.classList.add('modal-open');
  }
  function openChart(){ensure();const m=document.getElementById('chartModal');m.hidden=false;m.setAttribute('aria-hidden','false');document.body.classList.add('modal-open');requestAnimationFrame(()=>drawACWIChart(window.historyDataForChart,document.querySelector('.period-button.active')?.dataset.period||'1y','acwiChartModal'))}
  document.addEventListener('DOMContentLoaded',()=>{ensure();document.addEventListener('click',e=>{const m=e.target.closest('[data-midx]');if(m){openMetric(stores.metrics[+m.dataset.midx]);return}const p=e.target.closest('[data-pidx]');if(p){openMetric(stores.priced[+p.dataset.pidx],true);return}if(e.target.closest('[data-close-modal]')){document.getElementById('metricModal').hidden=true;document.body.classList.remove('modal-open');return}if(e.target.closest('[data-close-chart]')){document.getElementById('chartModal').hidden=true;document.body.classList.remove('modal-open');return}if(e.target.closest('.chart-card')){openChart()}});document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelectorAll('.metric-modal').forEach(m=>m.hidden=true);document.body.classList.remove('modal-open')}});});
  window.dashboardMetricUI={init:render,bind:function(){}};
})();
function repaintACWI(){if(window.historyDataForChart)requestAnimationFrame(()=>drawACWIChart(window.historyDataForChart,document.querySelector('.period-button.active')?.dataset.period||'1y','acwiChart'))}
window.addEventListener('resize',repaintACWI);window.addEventListener('load',repaintACWI);