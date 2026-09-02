(() => {
  const originalDraw = window.drawACWIChart;

  function periodPoints(history, period) {
    const values = Array.isArray(history?.acwi) ? history.acwi : [];
    const dates = Array.isArray(history?.dates) ? history.dates : [];
    const n = {"1y":252,"3y":756,"5y":1260,"all":values.length}[period] || 252;
    const start = Math.max(0, values.length - n);
    return values.slice(start).map((value, i) => ({
      value: Number(value),
      date: dates[start + i] || ""
    })).filter(p => Number.isFinite(p.value));
  }

  function drawEnhanced(history, period, canvasId = "acwiChart") {
    if (typeof originalDraw === "function") originalDraw(history, period, canvasId);

    const canvas = document.getElementById(canvasId);
    if (!canvas || !history) return;
    const points = periodPoints(history, period);
    if (points.length < 2) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(300, Math.round(rect.width || canvas.clientWidth || 600));
    const height = Math.max(140, Math.round(rect.height || canvas.clientHeight || 155));
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const pad = {left:42,right:16,top:18,bottom:28};
    const vals = points.map(p => p.value);
    const min = Math.min(...vals), max = Math.max(...vals), range = max - min || 1;
    const x = i => pad.left + i * (width - pad.left - pad.right) / Math.max(1, points.length - 1);
    const y = v => height - pad.bottom - (v - min) / range * (height - pad.top - pad.bottom);

    // 200-day moving average; only plot where enough history exists.
    const fullValues = Array.isArray(history.acwi) ? history.acwi.map(Number) : [];
    const start = Math.max(0, fullValues.length - ({"1y":252,"3y":756,"5y":1260,"all":fullValues.length}[period] || 252));
    const ma = points.map((p, localIndex) => {
      const globalIndex = start + localIndex;
      if (globalIndex < 199) return null;
      const window = fullValues.slice(globalIndex - 199, globalIndex + 1);
      if (window.length < 200 || window.some(v => !Number.isFinite(v))) return null;
      return window.reduce((a, b) => a + b, 0) / window.length;
    });

    ctx.strokeStyle = "#f1c85b";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ma.forEach((v, i) => {
      if (!Number.isFinite(v)) return;
      const xx = x(i), yy = y(v);
      if (i === 0 || !Number.isFinite(ma[i - 1])) ctx.moveTo(xx, yy);
      else ctx.lineTo(xx, yy);
    });
    ctx.stroke();

    // Compact legend and regime marker.
    const current = points[points.length - 1].value;
    const currentMA = ma[ma.length - 1];
    const regime = Number.isFinite(currentMA) ? (current >= currentMA ? "UPTREND" : "DOWNTREND") : "REGIME UNKNOWN";
    const gap = Number.isFinite(currentMA) ? ((current / currentMA) - 1) * 100 : null;

    ctx.font = "700 9px system-ui,sans-serif";
    ctx.fillStyle = "#edf4f7";
    ctx.fillText("ACWI", pad.left, 11);
    ctx.fillStyle = "#f1c85b";
    ctx.fillText("200DMA", pad.left + 36, 11);
    ctx.fillStyle = regime === "UPTREND" ? "#48d597" : "#ed6666";
    ctx.fillText(regime, width - 76, 11);

    if (Number.isFinite(gap)) {
      ctx.font = "9px system-ui,sans-serif";
      ctx.fillStyle = "#8fa4b2";
      const text = `${gap >= 0 ? "+" : ""}${gap.toFixed(1)}% vs 200DMA`;
      ctx.fillText(text, width - 118, height - 8);
    }
  }

  window.drawACWIChart = drawEnhanced;
})();
