let latest = null;
let history = null;

const esc = value => String(value ?? "—").replace(/[&<>\"']/g, s => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]));

async function loadJson(path) {
  const response = await fetch(`${path}?v=${Date.now()}`);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function modeText(data) {
  const mode = data?.mode || "UNKNOWN";
  const badge = document.getElementById("modeBadge");
  badge.textContent = mode;
  badge.className = `mode-badge mode-${mode.toLowerCase()}`;
}

function briefClass(status) {
  return status === "MAJOR RISK" ? "status-red" : status === "WARNING" ? "status-yellow" : "status-green";
}

function renderBrief(data) {
  const brief = data.brief || {};
  const panel = document.getElementById("marketBrief");
  panel.className = `market-brief ${briefClass(brief.status)}`;
  document.getElementById("briefLabel").textContent = brief.label || "MARKET CONDITION";
  document.getElementById("briefText").textContent = brief.reason || "No summary available.";
  document.getElementById("briefAction").textContent = data.rules?.action || "NORMAL DCA";
}

function bandHtml(item) {
  if (item.current == null || !item.band) return '<div class="empty">No current data.</div>';
  const b = item.band;
  const min = Number(b.p05), max = Number(b.p95), q1 = Number(b.p25), q3 = Number(b.p75), now = Number(item.current);
  if (![min,max,q1,q3,now].every(Number.isFinite) || max === min) return '<div class="empty">Historical range unavailable.</div>';
  const pos = Math.max(0, Math.min(100, (now-min)/(max-min)*100));
  const left = Math.max(0, Math.min(100, (q1-min)/(max-min)*100));
  const width = Math.max(0, Math.min(100-left, (q3-q1)/(max-min)*100));
  return `<div class="band"><div class="band-track"></div><div class="band-typical" style="left:${left}%;width:${width}%"></div><div class="band-now" style="left:${pos}%"></div></div><div class="band-scale"><span>P05 ${esc(b.p05_label)}</span><span>P95 ${esc(b.p95_label)}</span></div><div class="band-caption"><span>Typical P25–P75</span><strong>${esc(item.percentile_label || item.percentile + "th pct")}</strong></div>`;
}

function metricCard(item) {
  return `<article class="metric-card"><div class="metric-top"><div class="metric-name">${esc(item.name)}</div></div><div class="metric-value">${esc(item.display)}</div><div class="metric-meta">${esc(item.detail || "")}</div>${bandHtml(item)}</article>`;
}

function renderMetricGrid(id, items) {
  const el = document.getElementById(id);
  el.innerHTML = (items || []).map(metricCard).join("") || '<div class="empty">No data.</div>';
}

function renderValueCards(id, items) {
  const el = document.getElementById(id);
  el.innerHTML = (items || []).map(item => `<div class="info-card"><div class="metric-name">${esc(item.name)}</div><div class="metric-value">${esc(item.display)}</div><div class="metric-meta">${esc(item.detail || "")}</div>${bandHtml(item)}</div>`).join("") || '<div class="empty">No data.</div>';
}

function renderPricedIn(data) {
  const items = data.priced_in || [];
  document.getElementById("pricedInGrid").innerHTML = items.map(item => `<article class="priced-card"><h4>${esc(item.name)}</h4><div class="big">${esc(item.display)}</div><p>${esc(item.explanation)}</p></article>`).join("") || '<div class="empty">No market-pricing data.</div>';
}

function renderRules(data) {
  document.getElementById("rulesSummary").textContent = data.rules?.detail || "Rules are not yet configured. The dashboard currently reports market conditions only.";
}

function renderSources(data) {
  document.getElementById("sources").textContent = `Sources: ${data.sources?.join(" · ") || "Market data providers"}`;
}

async function start() {
  try {
    [latest, history] = await Promise.all([loadJson("data/latest.json"), loadJson("data/history.json")]);
    modeText(latest);
    document.getElementById("updatedAt").textContent = `Updated ${latest.updated_at || "—"}`;
    document.getElementById("dataThrough").textContent = `Market data through ${latest.data_through || "—"}`;
    renderBrief(latest);
    renderMetricGrid("equityGrid", latest.equities);
    renderMetricGrid("riskGrid", latest.risk);
    renderValueCards("valuationGrid", latest.valuation);
    renderValueCards("crossAssetGrid", latest.cross_asset);
    renderPricedIn(latest);
    renderRules(latest);
    renderSources(latest);
    setupPeriods();
    drawACWIChart(history, "1y");
  } catch (error) {
    console.error(error);
    document.getElementById("briefLabel").textContent = "DATA UNAVAILABLE";
    document.getElementById("briefText").textContent = "The dashboard could not load the latest market data.";
    document.getElementById("briefAction").textContent = "CHECK DATA SOURCE";
    document.getElementById("marketBrief").className = "market-brief status-red";
    document.getElementById("modeBadge").textContent = "ERROR";
    document.getElementById("modeBadge").className = "mode-badge mode-stale";
  }
}

function setupPeriods() {
  document.querySelectorAll(".period-button").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".period-button").forEach(b => b.classList.remove("active"));
    button.classList.add("active");
    drawACWIChart(history, button.dataset.period);
  }));
}

document.addEventListener("DOMContentLoaded", start);
