# -*- coding: utf-8 -*-
"""Template HTML della pagina 'Mercati Energetici' (brand LMS / Logica Media Service).

Segnaposto sostituiti da pun_gme.write_viewer():
  /*__ELEC__*/  -> JSON { 'YYYY-MM-DD': [24 valori PUN €/MWh] }
  /*__GAS__*/   -> JSON { 'YYYY-MM-DD': prezzo gas PSV €/MWh }
  __GEN__       -> timestamp di generazione

Per inserire i loghi delle certificazioni: popola l'array CERTS nel JS in fondo
con oggetti {src, alt}. Per sostituire il logo: rimpiazza il blocco <svg class=logo>.
"""

VIEWER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Mercati Energetici — Logica Media Service</title>
<meta name="description" content="PUN elettrico e gas PSV ufficiali GME, aggiornati ogni giorno. A cura di Logica Media Service (LMS)."/>
<style>
  :root{
    --bg:#0e1116; --panel:#161d27; --panel2:#1d2733; --line:#2a3744; --txt:#e9eef4;
    --muted:#92a1b2; --brand:#1f6feb; --elec:#16a34a; --gas:#f59e0b; --chip:#222e3c;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.45}
  a{color:var(--brand);text-decoration:none} a:hover{text-decoration:underline}
  /* ---------- header brand ---------- */
  header.brand{display:flex;align-items:center;gap:16px;padding:16px 22px;
    border-bottom:1px solid var(--line);background:linear-gradient(180deg,#121a25,#0e1116);flex-wrap:wrap}
  .logo{flex:0 0 auto}
  .brandtxt{display:flex;flex-direction:column;line-height:1.1}
  .brandtxt .co{font-size:13px;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;font-weight:600}
  .brandtxt h1{margin:2px 0 0;font-size:21px;font-weight:700}
  .brandtxt .sub{font-size:12px;color:var(--muted);margin-top:2px}
  .hspacer{flex:1}
  .updated{font-size:12px;color:var(--muted);text-align:right}
  /* ---------- layout ---------- */
  .wrap{max-width:1080px;margin:0 auto;padding:18px 22px 30px}
  .domains{display:flex;gap:10px;margin:6px 0 14px}
  .dom{display:flex;align-items:center;gap:8px;padding:10px 16px;border:1px solid var(--line);
    background:var(--panel);color:var(--txt);border-radius:11px;cursor:pointer;font-size:15px;font-weight:600}
  .dom .dot{width:10px;height:10px;border-radius:50%}
  .dom.elec.active{border-color:var(--elec);box-shadow:inset 0 0 0 1px var(--elec)}
  .dom.gas.active{border-color:var(--gas);box-shadow:inset 0 0 0 1px var(--gas)}
  .dom.active{background:var(--panel2)}
  .tabs{display:flex;gap:8px;margin:0 0 16px}
  .tab{padding:8px 15px;border:1px solid var(--line);background:var(--panel);color:var(--txt);
    border-radius:9px;cursor:pointer;font-size:14px}
  .tab.active{background:var(--accent);border-color:var(--accent);color:#08121d;font-weight:700}
  .nav{display:flex;align-items:center;gap:12px;margin-bottom:14px}
  .nav button{background:var(--panel);border:1px solid var(--line);color:var(--txt);
    width:38px;height:38px;border-radius:9px;cursor:pointer;font-size:18px}
  .nav button:hover{background:var(--panel2)}
  .nav .label{font-size:17px;font-weight:600;min-width:190px;text-align:center;text-transform:capitalize}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
  .dow,.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
  .dow div{color:var(--muted);font-size:12px;text-align:center;padding:4px 0;text-transform:uppercase}
  .cell{aspect-ratio:1/1;border:1px solid var(--line);border-radius:10px;padding:7px;display:flex;
    flex-direction:column;justify-content:space-between;background:var(--panel2)}
  .cell.empty{background:transparent;border:none}
  .cell.has{cursor:pointer;transition:transform .06s}
  .cell.has:hover{transform:translateY(-2px);outline:2px solid var(--accent)}
  .cell .d{font-size:13px;color:var(--muted)} .cell .v{font-size:15px;font-weight:700}
  .cell .u{font-size:10px;color:var(--muted)}
  .stats{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 16px}
  .stat{background:var(--chip);border:1px solid var(--line);border-radius:11px;padding:10px 14px;min-width:120px}
  .stat .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
  .stat .val{font-size:20px;font-weight:700;margin-top:3px}
  .stat .val small{font-size:12px;color:var(--muted);font-weight:500}
  .bars{display:flex;align-items:flex-end;gap:3px;height:220px;margin-top:8px;border-bottom:1px solid var(--line);padding-bottom:2px}
  .bar{flex:1;border-radius:3px 3px 0 0;position:relative;min-height:2px;background:var(--accent)}
  .bar:hover{outline:2px solid #fff}
  .bar .tip{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);
    background:#000;border:1px solid var(--line);padding:4px 7px;border-radius:6px;font-size:11px;white-space:nowrap;z-index:5;margin-bottom:4px}
  .bar:hover .tip{display:block}
  .xlabels{display:flex;gap:3px;margin-top:4px}
  .xlabels div{flex:1;text-align:center;font-size:9px;color:var(--muted)}
  .hint{color:var(--muted);font-size:13px;margin-top:10px}
  table{border-collapse:collapse;width:100%;margin-top:14px;font-size:13px}
  th,td{border:1px solid var(--line);padding:5px 8px;text-align:right}
  th:first-child,td:first-child{text-align:left}
  th{color:var(--muted);font-weight:600;background:var(--panel2)}
  .empty-note{color:var(--muted);padding:30px;text-align:center}
  .bigprice{font-size:40px;font-weight:800;margin:6px 0}
  /* ---------- certificazioni + footer ---------- */
  .certs{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:center;
    padding:18px;margin-top:22px;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
  .certs img{height:54px;width:auto;background:#fff;border-radius:8px;padding:6px}
  .certs .lbl{width:100%;text-align:center;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
  footer.brand{margin-top:22px;border-top:1px solid var(--line);background:#0c1218;color:var(--muted);font-size:13px}
  .foot-in{max-width:1080px;margin:0 auto;padding:22px;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:22px}
  footer .co{color:var(--txt);font-weight:700;letter-spacing:.04em;margin-bottom:6px}
  footer .lab{color:var(--txt);font-weight:600;margin-bottom:3px}
  footer .row{margin:2px 0}
  .legal{max-width:1080px;margin:0 auto;padding:0 22px 22px;color:#5f6f7e;font-size:11px}
</style>
</head>
<body>
<header class="brand">
  <!-- LOGO segnaposto LMS (sostituibile col logo ufficiale) -->
  <svg class="logo" width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg" aria-label="LMS">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1f6feb"/><stop offset="1" stop-color="#16a34a"/></linearGradient></defs>
    <rect x="2" y="2" width="56" height="56" rx="14" fill="url(#g)"/>
    <path d="M33 12 L20 33 H29 L27 48 L41 25 H32 Z" fill="#fff" opacity="0.95"/>
  </svg>
  <div class="brandtxt">
    <span class="co">Logica Media Service</span>
    <h1>Mercati Energetici</h1>
    <span class="sub">PUN elettrico e Gas PSV ufficiali GME · aggiornati ogni giorno</span>
  </div>
  <span class="hspacer"></span>
  <span class="updated" id="updated">aggiornato __GEN__</span>
</header>

<div class="wrap">
  <div class="domains">
    <div class="dom elec active" data-dom="elec"><span class="dot" style="background:var(--elec)"></span>⚡ Elettricità · PUN</div>
    <div class="dom gas" data-dom="gas"><span class="dot" style="background:var(--gas)"></span>🔥 Gas · PSV</div>
  </div>
  <div class="tabs">
    <div class="tab active" data-view="day">📅 Giorno</div>
    <div class="tab" data-view="month">📊 Mese</div>
    <div class="tab" data-view="year">📈 Anno</div>
  </div>
  <div class="nav"><button id="prev">‹</button><div class="label" id="navlabel"></div><button id="next">›</button></div>
  <div id="content"></div>

  <div class="certs" id="certs" style="display:none">
    <div class="lbl">Certificazioni</div>
    <div id="certbody"></div>
  </div>
</div>

<footer class="brand">
  <div class="foot-in">
    <div>
      <div class="co">LOGICA MEDIA SERVICE</div>
      <div class="row">P.IVA 01567580764</div>
      <div class="row"><a href="https://www.logicamediaservice.it" target="_blank" rel="noopener">www.logicamediaservice.it</a></div>
    </div>
    <div>
      <div class="lab">Sede legale e operativa</div>
      <div class="row">Via della Tecnica 18 — 85100 Potenza (PZ)</div>
      <div class="row">Tel: <a href="tel:+390971746521">0971 1746521</a></div>
      <div class="row"><a href="mailto:amministrazione@logicamediaservice.it">amministrazione@logicamediaservice.it</a></div>
    </div>
    <div>
      <div class="lab">Sede di rappresentanza</div>
      <div class="row">Via Trabaci 22/8 — 75100 Matera (MT)</div>
      <div class="row">Tel: <a href="tel:+390835170051">0835 1700051</a></div>
      <div class="row"><a href="mailto:clienti@logicamediaservice.it">clienti@logicamediaservice.it</a></div>
      <div class="row"><a href="mailto:info@logicamediaservice.it">info@logicamediaservice.it</a></div>
    </div>
  </div>
  <div class="legal">
    Fonte dati: Gestore dei Mercati Energetici (GME) — mercatoelettrico.org. PUN: prezzo MGP orario.
    Gas PSV: prezzo di riferimento MGP-GAS. Dati a fini informativi, soggetti alle Condizioni di utilizzo
    e al Disclaimer di GME.
  </div>
</footer>

<script>
const ELEC = /*__ELEC__*/;
const GAS  = /*__GAS__*/;
// Per aggiungere i loghi delle certificazioni: CERTS=[{src:"iso9001.png",alt:"ISO 9001"}, ...]
const CERTS = [];

const MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"];
const DOW=["lun","mar","mer","gio","ven","sab","dom"];
const SMC=0.01069; // €/MWh -> ≈ €/Smc (PCS standard, indicativo)

let domain="elec", view="day", selDate=null;
let cur={y:new Date().getFullYear(),m:new Date().getMonth(),d:1};

const content=document.getElementById("content"), navlabel=document.getElementById("navlabel");

function D(){ // accessor del dominio corrente
  if(domain==="elec") return {
    data:ELEC, accent:getComputedStyle(document.documentElement).getPropertyValue('--elec'),
    name:"PUN", unit:"€/MWh", dayVal:k=>avg(ELEC[k]),
    monthAvg:ks=>{let a=[];ks.forEach(k=>a=a.concat(ELEC[k]));return avg(a);}, hourly:true };
  return {
    data:GAS, accent:getComputedStyle(document.documentElement).getPropertyValue('--gas'),
    name:"Gas PSV", unit:"€/MWh", dayVal:k=>GAS[k],
    monthAvg:ks=>avg(ks.map(k=>GAS[k])), hourly:false };
}
function keys(){return Object.keys(D().data).sort();}
function parse(s){const[y,m,d]=s.split("-").map(Number);return{y,m:m-1,d};}
function fmt(y,m,d){return `${y}-${String(m+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;}
function avg(a){return a.reduce((x,y)=>x+y,0)/a.length;}
function eur(v,dec=2){return v.toLocaleString("it-IT",{minimumFractionDigits:dec,maximumFractionDigits:dec});}
function daysInMonth(y,m){return new Date(y,m+1,0).getDate();}
function monthKeys(y,m){return keys().filter(k=>{const p=parse(k);return p.y===y&&p.m===m;});}
function yearKeys(y){return keys().filter(k=>parse(k).y===y);}

function applyAccent(){document.documentElement.style.setProperty('--accent', D().accent.trim());}
function heat(v,mn,mx){if(mx===mn)return "#1e3a2a";const t=(v-mn)/(mx-mn);return `hsl(${140-t*140},55%,30%)`;}

function setActive(){
  document.querySelectorAll(".dom").forEach(e=>e.classList.toggle("active",e.dataset.dom===domain));
  document.querySelectorAll(".tab").forEach(e=>e.classList.toggle("active",e.dataset.view===view));
}
function init(){
  const ks=keys();
  if(ks.length){const last=parse(ks[ks.length-1]);cur={y:last.y,m:last.m,d:last.d};selDate=ks[ks.length-1];}
  renderCerts();
}
function render(){
  applyAccent(); setActive();
  const ks=keys();
  if(!ks.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato ${D().name} disponibile.</div></div>`;navlabel.textContent="—";return;}
  if(view==="day")renderDay();else if(view==="month")renderMonth();else renderYear();
}
function barChart(values,labels,opts={}){
  const max=Math.max(...values,0),min=Math.min(...values,0),span=(max-min)||1;let bars="",xs="";
  values.forEach((v,i)=>{const h=Math.max(2,((v-min)/span)*100);
    bars+=`<div class="bar" style="height:${h}%"><span class="tip">${labels[i]}: ${eur(v)} ${D().unit}</span></div>`;
    xs+=`<div>${opts.xevery?(i%opts.xevery===0?labels[i]:""):labels[i]}</div>`;});
  return `<div class="bars">${bars}</div><div class="xlabels">${xs}</div>`;
}
function statBlock(label,mwh){return `<div class="stat"><div class="k">${label}</div>
  <div class="val">${eur(mwh)} <small>€/MWh</small></div>
  <div class="val" style="font-size:14px">${eur(mwh/1000,4)} <small>€/kWh</small></div></div>`;}
function statGas(label,mwh){return `<div class="stat"><div class="k">${label}</div>
  <div class="val">${eur(mwh)} <small>€/MWh</small></div>
  <div class="val" style="font-size:14px">≈ ${eur(mwh*SMC,4)} <small>€/Smc</small></div></div>`;}

function renderDay(){
  navlabel.textContent=`${MESI[cur.m]} ${cur.y}`;
  const dv=D().dayVal; const ks=keys();
  let mn=Infinity,mx=-Infinity; ks.forEach(k=>{const a=dv(k);mn=Math.min(mn,a);mx=Math.max(mx,a);});
  const nd=daysInMonth(cur.y,cur.m),fd=(new Date(cur.y,cur.m,1).getDay()+6)%7;let cells="";
  for(let i=0;i<fd;i++)cells+=`<div class="cell empty"></div>`;
  for(let d=1;d<=nd;d++){const key=fmt(cur.y,cur.m,d);
    if(D().data[key]!=null){const a=dv(key);
      cells+=`<div class="cell has" style="background:${heat(a,mn,mx)}" data-key="${key}"><div class="d">${d}</div><div><span class="v">${eur(a,1)}</span> <span class="u">€/MWh</span></div></div>`;
    }else cells+=`<div class="cell"><div class="d">${d}</div></div>`;}
  let detail=`<div class="hint">Clicca un giorno colorato per il dettaglio.</div>`;
  if(selDate&&D().data[selDate]!=null&&parse(selDate).y===cur.y&&parse(selDate).m===cur.m)detail=dayDetail(selDate);
  content.innerHTML=`<div class="card"><div class="dow">${DOW.map(x=>`<div>${x}</div>`).join("")}</div><div class="grid">${cells}</div></div><div style="height:16px"></div>${detail}`;
  document.querySelectorAll(".cell.has").forEach(c=>c.onclick=()=>{selDate=c.dataset.key;render();});
}
function dayDetail(key){
  const p=parse(key);
  if(D().hourly){
    const vals=ELEC[key],a=avg(vals),mn=Math.min(...vals),mx=Math.max(...vals);
    const labels=vals.map((_,i)=>String(i+1).padStart(2,"0"));let rows="";
    vals.forEach((v,i)=>rows+=`<tr><td>${String(i+1).padStart(2,"0")}:00</td><td>${eur(v)}</td><td>${eur(v/1000,4)}</td></tr>`);
    return `<div class="card"><h3 style="margin:0 0 4px">Profilo orario PUN — ${p.d} ${MESI[p.m]} ${p.y}</h3>
      <div class="stats">${statBlock("Media giorno",a)}${statBlock("Minimo",mn)}${statBlock("Massimo",mx)}</div>
      ${barChart(vals,labels,{})}
      <table><thead><tr><th>Ora</th><th>€/MWh</th><th>€/kWh</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  const v=GAS[key];
  return `<div class="card"><h3 style="margin:0 0 4px">Gas PSV — ${p.d} ${MESI[p.m]} ${p.y}</h3>
    <div class="bigprice">${eur(v)} <span style="font-size:18px;color:var(--muted)">€/MWh</span></div>
    <div class="stats">${statGas("Prezzo di riferimento",v)}</div>
    <div class="hint">Prezzo di riferimento MGP-GAS al PSV. €/Smc indicativo (PCS standard).</div></div>`;
}
function renderMonth(){
  navlabel.textContent=`${MESI[cur.m]} ${cur.y}`;
  const ks=monthKeys(cur.y,cur.m).sort();
  if(!ks.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato per ${MESI[cur.m]} ${cur.y}.</div></div>`;return;}
  const dv=D().dayVal; const dayVals=ks.map(dv);
  const mAvg=D().monthAvg(ks),mMin=Math.min(...dayVals),mMax=Math.max(...dayVals),labels=ks.map(k=>String(parse(k).d));
  const sb=domain==="gas"?statGas:statBlock;
  content.innerHTML=`<div class="card"><h3 style="margin:0 0 4px">${D().name} — medie giornaliere ${MESI[cur.m]} ${cur.y}</h3>
    <div class="stats">${sb("Media mese",mAvg)}${sb("Giorno più basso",mMin)}${sb("Giorno più alto",mMax)}
    <div class="stat"><div class="k">Giorni</div><div class="val">${ks.length}</div></div></div>
    ${barChart(dayVals,labels,{xevery:2})}</div>`;
}
function renderYear(){
  navlabel.textContent=`${cur.y}`;
  const out=[]; for(let m=0;m<12;m++){const ks=monthKeys(cur.y,m);out.push(ks.length?D().monthAvg(ks):null);}
  const present=out.map((v,i)=>({v,i})).filter(o=>o.v!=null);
  if(!present.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato per il ${cur.y}.</div></div>`;return;}
  const yks=yearKeys(cur.y); const yAvg=D().monthAvg(yks);
  const vals=present.map(o=>o.v),labels=present.map(o=>MESI[o.i].slice(0,3)),mn=Math.min(...vals),mx=Math.max(...vals);
  const sb=domain==="gas"?statGas:statBlock;
  content.innerHTML=`<div class="card"><h3 style="margin:0 0 4px">${D().name} — medie mensili ${cur.y}</h3>
    <div class="stats">${sb("Media anno",yAvg)}${sb("Mese più basso",mn)}${sb("Mese più alto",mx)}</div>
    ${barChart(vals,labels,{})}</div>`;
}
function step(dir){if(view==="year")cur.y+=dir;else{cur.m+=dir;if(cur.m<0){cur.m=11;cur.y--;}if(cur.m>11){cur.m=0;cur.y++;}}render();}
function renderCerts(){
  if(!CERTS.length)return;
  document.getElementById("certs").style.display="flex";
  document.getElementById("certbody").innerHTML=CERTS.map(c=>`<img src="${c.src}" alt="${c.alt}" title="${c.alt}"/>`).join("");
}
document.getElementById("prev").onclick=()=>step(-1);
document.getElementById("next").onclick=()=>step(1);
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{view=t.dataset.view;render();});
document.querySelectorAll(".dom").forEach(b=>b.onclick=()=>{
  domain=b.dataset.dom; const ks=keys();
  if(ks.length){const last=parse(ks[ks.length-1]);cur={y:last.y,m:last.m,d:last.d};selDate=ks[ks.length-1];}
  render();
});
init(); render();
</script>
</body>
</html>
"""
