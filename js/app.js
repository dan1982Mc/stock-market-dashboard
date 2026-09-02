let latest=null,history=null;
const metricStore=new Map();
const pricedStore=new Map();
let metricId=0;
const esc=v=>String(v??"—").replace(/[&<>\"']/g,s=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]));
async function loadJson(path){const r=await fetch(`${path}?v=${Date.now()}`);if(!r.ok)throw new Error(`${path}: HTTP ${r.status}`);return r.json()}
function setMode(data){const b=document.getElementById("modeBadge"),m=data?.mode||"UNKNOWN";b.textContent=m;b.className=`mode-badge mode-${m.toLowerCase()}`}
function briefClass(s){return s==="MAJOR RISK"?"status-red":s==="WARNING"?"status-yellow":"status-green"}
function renderBrief(data){const b=data.brief||{},p=document.getElementById("marketBrief");p.className=`market-brief ${briefClass(b.status)}`;document.getElementById("briefLabel").textContent=b.label||"MARKET CONDITION";document.getElementById("briefText").textContent=b.reason||"No summary available.";document.getElementById("briefAction").textContent=data.rules?.action||"NORMAL DCA"}
const TYPICAL_RANGES={"ACWI":[-5,10],"US equities":[-5,10],"Europe":[-7,10],"Emerging markets":[-7,12],"US volatility (VIX)":[12,20],"Europe volatility (VSTOXX)":[15,25],"Emerging-market volatility (VXEEM)":[18,28],"ACWI drawdown":[-10,0],"US CAPE":[15,25],"US 10Y yield":[2,4.5],"Gold":[1500,3000]};
function formatRangeValue(v,item){if(!Number.isFinite(v))return "—";if(item.name==="Gold")return `$${v.toLocaleString()}`;if(item.name==="US 10Y yield")return `${v.toFixed(1)}%`;if(["US CAPE","ACWI drawdown"].includes(item.name))return v.toFixed(1);return Number.isInteger(v)?String(v):v.toFixed(1)}
function bandHtml(item,caption=true){
  if(item.current==null||!item.band)return '<div class="empty">No historical range available.</div>';
  const b=item.band,min=+b.p05,max=+b.p95,now=+item.current,range=TYPICAL_RANGES[item.name];
  if(![min,max,now].every(Number.isFinite)||max===min)return '<div class="empty">Historical range unavailable.</div>';
  if(!range)return '<div class="empty">Typical range unavailable.</div>';
  const low=Math.min(range[0],range[1]),high=Math.max(range[0],range[1]);
  const pct=x=>Math.max(0,Math.min(100,(x-min)/(max-min)*100));
  const pos=pct(now),left=pct(low),right=pct(high),width=Math.max(0,right-left);
  const labelRow=`<div class="band-label-row"><span style="position:absolute;left:0;transform:translateX(0)">${esc(formatRangeValue(min,item))}</span><span style="position:absolute;left:${left}%;transform:translateX(-50%)">${esc(formatRangeValue(low,item))}</span><span style="position:absolute;left:${right}%;transform:translateX(-50%)">${esc(formatRangeValue(high,item))}</span><span style="position:absolute;left:100%;transform:translateX(-100%)">${esc(formatRangeValue(max,item))}</span></div>`;
  const captionHtml=caption?`<div class="band-caption"><span>Typical range: ${esc(formatRangeValue(low,item))} – ${esc(formatRangeValue(high,item))}</span><strong>${esc(item.percentile_label||`P${item.percentile}`)}</strong></div>`:"";
  return `${labelRow}<div class="band"><div class="band-track"></div><div class="band-typical" style="left:${left}%;width:${width}%"></div><div class="band-now" style="left:${pos}%"></div></div>${captionHtml}`;
}
function metricCard(item){const id=String(++metricId);metricStore.set(id,item);return `<article class="metric-card" tabindex="0" role="button" aria-label="Open details for ${esc(item.name)}" data-metric-id="${id}"><div class="metric-top"><div class="metric-name">${esc(item.name)}</div></div><div class="metric-value">${esc(item.display)}</div><div class="metric-meta">${esc(item.detail)}</div>${bandHtml(item)}</article>`}
function renderGrid(id,items){document.getElementById(id).innerHTML=(items||[]).map(metricCard).join("")||'<div class="empty">No data.</div>'}
function renderInfo(id,items){document.getElementById(id).innerHTML=(items||[]).map(metricCard).join("")||'<div class="empty">No data.</div>'}
function renderPricedIn(data){pricedStore.clear();document.getElementById("pricedInGrid").innerHTML=(data.priced_in||[]).map((i,n)=>{const id=String(n+1);pricedStore.set(id,i);return `<article class="priced-card" tabindex="0" role="button" aria-label="Open details for ${esc(i.name)}" data-priced-id="${id}"><h4>${esc(i.name)}</h4><div class="big">${esc(i.display)}</div><p>${esc(i.explanation)}</p></article>`}).join("")||'<div class="empty">No market-pricing data.</div>'}
function setupPeriods(){document.querySelectorAll(".period-button").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".period-button").forEach(x=>x.classList.remove("active"));b.classList.add("active");safeDrawChart(b.dataset.period)}))}
function safeDrawChart(period="1y"){try{if(history&&typeof drawACWIChart==="function")drawACWIChart(history,period)}catch(e){console.error("ACWI chart error",e)}}
function openMetricModal(item,type="indicator"){
  const modal=document.getElementById("metricModal"),title=document.getElementById("metricModalTitle"),body=document.getElementById("metricModalBody");
  if(!modal||!title||!body)return;
  title.textContent=item.name||"Indicator";
  if(type==="priced"){
    body.innerHTML=`<div class="modal-layout"><div class="modal-main"><div class="modal-big-value">${esc(item.display||"—")}</div><p class="modal-detail">${esc(item.explanation||"")}</p></div><aside class="modal-info"><div class="eyebrow">ABOUT THIS INDICATOR</div><p>${esc(item.explanation||"Market-derived indicator used to provide context for current market pricing.")}</p></aside></div>`;
  }else{
    body.innerHTML=`<div class="modal-layout"><div class="modal-main"><div class="modal-big-value">${esc(item.display||"—")}</div><div class="modal-detail"><strong>Details</strong><br>${esc(item.detail||"No detail available.")}</div>${item.band?`<div class="modal-band">${bandHtml(item,false)}</div>`:""}<div class="modal-stats"><span>Historical percentile</span><strong>${esc(item.percentile_label||(`P${item.percentile}`))}</strong></div>${item.source?`<div class="modal-note">Source: ${esc(item.source)}</div>`:""}</div><aside class="modal-info"><div class="eyebrow">ABOUT THIS INDICATOR</div><p>${esc(item.definition||item.detail||"This indicator provides market context within its historical range.")}</p></aside></div>`;
  }
  modal.hidden=false;modal.setAttribute("aria-hidden","false");document.body.classList.add("modal-open");document.querySelector(".metric-modal-close")?.focus();
}
function closeMetricModal(){const modal=document.getElementById("metricModal");if(!modal)return;modal.hidden=true;modal.setAttribute("aria-hidden","true");document.body.classList.remove("modal-open")}
function setupMetricModals(){if(window.__metricModalsReady)return;window.__metricModalsReady=true;document.addEventListener("click",function(e){const close=e.target.closest("[data-close-modal]");if(close){closeMetricModal();return}const metric=e.target.closest("[data-metric-id]");if(metric){const item=metricStore.get(metric.dataset.metricId);if(item)openMetricModal(item);return}const priced=e.target.closest("[data-priced-id]");if(priced){const item=pricedStore.get(priced.dataset.pricedId);if(item)openMetricModal(item,"priced");return}});document.addEventListener("keydown",function(e){if(e.key==="Escape"){closeMetricModal();return}const el=document.activeElement;if((e.key==="Enter"||e.key===" ")&&el?.matches?.("[data-metric-id],[data-priced-id]")){e.preventDefault();const item=el.matches("[data-metric-id]")?metricStore.get(el.dataset.metricId):pricedStore.get(el.dataset.pricedId);if(item)openMetricModal(item,el.matches("[data-priced-id]")?"priced":"indicator")}})}
async function start(){
  setupMetricModals();
  try{
    metricStore.clear();metricId=0;
    [latest,history]=await Promise.all([loadJson("data/latest.json"),loadJson("data/history.json")]);
    window.historyDataForChart=history;
    setMode(latest);
    document.getElementById("updatedAt").textContent=`Updated ${latest.updated_at||"—"}`;
    document.getElementById("dataThrough").textContent=`Market data through ${latest.data_through||"—"}`;
    renderBrief(latest);
    renderGrid("equityGrid",latest.equities);
    renderGrid("riskGrid",latest.risk);
    renderInfo("valuationGrid",latest.valuation);
    renderInfo("crossAssetGrid",latest.cross_asset);
    renderPricedIn(latest);
    document.getElementById("rulesSummary").textContent=latest.rules?.detail||"Rules are not yet configured.";
    document.getElementById("sources").textContent=`Sources: ${(latest.sources||[]).join(" · ")}`;
    setupPeriods();
    safeDrawChart("1y");
  }catch(e){
    console.error(e);
    const p=document.getElementById("marketBrief");
    p.className="market-brief status-red";
    document.getElementById("briefLabel").textContent="DATA UNAVAILABLE";
    document.getElementById("briefText").textContent="The latest market data could not be loaded.";
    document.getElementById("briefAction").textContent="CHECK DATA SOURCE";
    document.getElementById("modeBadge").textContent="ERROR";
    document.getElementById("modeBadge").className="mode-badge mode-stale";
  }
}
document.addEventListener("DOMContentLoaded",start);
