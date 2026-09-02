function drawACWIChart(history, period) {
  const canvas = document.getElementById("acwiChart");
  if (!canvas || !history || !Array.isArray(history.acwi) || !history.acwi.length) return;
  const points = filterPeriod(history, period);
  if (points.length < 2) return;

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(300, Math.round(rect.width || canvas.clientWidth || 600));
  const height = Math.max(140, Math.round(rect.height || canvas.clientHeight || 155));
  canvas.width = Math.round(width*dpr);
  canvas.height = Math.round(height*dpr);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,width,height);

  const pad = {left:42,right:16,top:18,bottom:28};
  const vals = points.map(p => Number(p.value)).filter(Number.isFinite);
  if (vals.length < 2) return;
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = max-min || 1;
  const x = i => pad.left + i*(width-pad.left-pad.right)/(points.length-1);
  const y = v => height-pad.bottom-(v-min)/range*(height-pad.top-pad.bottom);

  ctx.strokeStyle = "#223743"; ctx.lineWidth = 1;
  for(let i=0;i<4;i++){
    const yy=pad.top+i*(height-pad.top-pad.bottom)/3;
    ctx.beginPath(); ctx.moveTo(pad.left,yy); ctx.lineTo(width-pad.right,yy); ctx.stroke();
  }
  ctx.strokeStyle = "#e85b5b"; ctx.lineWidth = 2.2; ctx.beginPath();
  points.forEach((p,i)=>{ const value=Number(p.value); if(!Number.isFinite(value)) return; const xx=x(i), yy=y(value); i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy); }); ctx.stroke();
  ctx.fillStyle="#8fa4b2"; ctx.font="10px system-ui,sans-serif";
  ctx.fillText(points[0].date || "",pad.left,height-8); ctx.fillText(points[points.length-1].date || "",Math.max(pad.left,width-70),height-8);
  ctx.fillText(max.toFixed(0),6,pad.top+4); ctx.fillText(min.toFixed(0),6,height-pad.bottom);
}

function filterPeriod(history, period){
  const values=Array.isArray(history?.acwi)?history.acwi:[];
  const dates=Array.isArray(history?.dates)?history.dates:[];
  const n={"1y":252,"3y":756,"5y":1260,"all":values.length}[period] || 252;
  const start=Math.max(0,values.length-n);
  return values.slice(start).map((value,i)=>({value,date:dates[start+i] || ""}));
}

window.addEventListener("resize",()=>{ if(window.historyDataForChart) requestAnimationFrame(()=>drawACWIChart(window.historyDataForChart, document.querySelector(".period-button.active")?.dataset.period || "1y")); });
