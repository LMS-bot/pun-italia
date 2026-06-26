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
    --bg:#f4f6f9; --panel:#ffffff; --panel2:#f1f4f8; --line:#dde3ea; --txt:#16202c;
    --muted:#5d6b7a; --brand:#1f6feb; --elec:#15a34a; --gas:#d97706; --chip:#eef2f6;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.45}
  a{color:var(--brand);text-decoration:none} a:hover{text-decoration:underline}
  /* ---------- header brand ---------- */
  header.brand{display:flex;align-items:center;gap:18px;padding:14px 22px;
    border-bottom:1px solid var(--line);background:linear-gradient(180deg,#ffffff,#f4f6f9);flex-wrap:wrap}
  .logoplate{flex:0 0 auto;background:#fff;border:1px solid var(--line);border-radius:12px;padding:9px 14px;display:flex;align-items:center}
  .logoplate img{height:46px;width:auto;display:block}
  .brandtxt{display:flex;flex-direction:column;line-height:1.15}
  .brandtxt h1{margin:0;font-size:21px;font-weight:700}
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
  .dow,.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
  .dow div{color:var(--muted);font-size:12px;text-align:center;padding:4px 0;text-transform:uppercase}
  .cell{min-height:58px;border:1px solid var(--line);border-radius:9px;padding:6px 7px;display:flex;
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
  .bar:hover{outline:2px solid var(--txt)}
  .bar .tip{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);
    background:#16202c;color:#fff;border:1px solid var(--line);padding:4px 7px;border-radius:6px;font-size:11px;white-space:nowrap;z-index:5;margin-bottom:4px}
  .bar:hover .tip{display:block}
  .xlabels{display:flex;gap:3px;margin-top:4px}
  .xlabels div{flex:1;text-align:center;font-size:9px;color:var(--muted)}
  .hint{color:var(--muted);font-size:13px;margin-top:10px}
  .trendpill{padding:6px 12px;border-radius:999px;font-size:13px;font-weight:700}
  .trendpill.down{background:#e7f6ec;color:#15803d}
  .trendpill.up{background:#fdeccd;color:#b45309}
  .fwdtoggle{display:flex;gap:6px}
  .fwdtoggle button{padding:5px 12px;border:1px solid var(--line);background:var(--panel2);color:var(--txt);border-radius:8px;cursor:pointer;font-size:13px}
  .fwdtoggle button.on{background:var(--accent);border-color:var(--accent);color:#08121d;font-weight:700}
  .legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;color:var(--muted);font-size:12px}
  .legend i{display:inline-block;width:13px;height:13px;border-radius:3px;margin-right:6px;vertical-align:middle;border:1px solid rgba(0,0,0,.08)}
  .consbanner{background:#e7f6ec;color:#15803d;border:1px solid #cdeed6;border-radius:10px;padding:11px 14px;font-size:15px;margin-bottom:12px}
  .consbanner.red{background:#fdecec;color:#b91c1c;border-color:#f5c2c2}
  .moderow{display:flex;gap:8px;margin-bottom:12px}
  .modebtn{flex:1;padding:11px;border:1px solid var(--line);background:var(--panel2);border-radius:10px;cursor:pointer;font-size:15px;font-weight:600;color:var(--txt)}
  .modebtn.on{background:#b45309;border-color:#b45309;color:#fff}
  .bizgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px;margin-bottom:12px}
  .bizbtn{padding:11px 12px;border:1px solid var(--line);background:var(--panel);border-radius:10px;cursor:pointer;font-size:14px;color:var(--txt);text-align:center}
  .bizbtn.on{background:#b45309;border-color:#b45309;color:#fff;font-weight:700}
  .acards{display:flex;flex-direction:column;gap:12px;margin-top:6px}
  .acard{border:1px solid var(--line);border-radius:12px;padding:14px;background:#fff}
  .ahead{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
  .aic{font-size:18px;margin-right:6px}
  .asub{font-size:12px;color:var(--muted);margin-top:2px}
  .asave{color:#15803d;font-weight:800;font-size:19px;text-align:right;white-space:nowrap}
  .asublab{font-size:11px;color:var(--muted);font-weight:500}
  .abest{margin-top:10px;font-size:13px;color:#15803d}
  .chip{display:inline-block;background:#e7f6ec;color:#15803d;border-radius:8px;padding:4px 9px;margin:4px 5px 0 0;font-weight:600}
  .aavoid{margin-top:9px;font-size:13px;color:#b91c1c}
  .aavoid b{background:#fdecec;color:#b91c1c;border-radius:7px;padding:2px 8px}
  .acont{margin-top:10px;font-size:12px;color:var(--muted);background:var(--chip);border-radius:10px;padding:8px 10px}
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
  footer.brand{margin-top:22px;border-top:1px solid var(--line);background:#eef2f6;color:var(--muted);font-size:13px}
  .foot-in{max-width:1080px;margin:0 auto;padding:22px;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:22px}
  footer .co{color:var(--txt);font-weight:700;letter-spacing:.04em;margin-bottom:6px}
  footer .lab{color:var(--txt);font-weight:600;margin-bottom:3px}
  footer .row{margin:2px 0}
  .legal{max-width:1080px;margin:0 auto;padding:16px 22px;color:#5f6f7e;font-size:11px}
  .herowrap{background:linear-gradient(180deg,#ffffff,#eef3f9);border-bottom:1px solid var(--line)}
  .hero{max-width:1080px;margin:0 auto;padding:18px 22px}
  .hero-main{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
  .hero-num{font-size:46px;font-weight:800;line-height:1;color:var(--accent);display:flex;align-items:baseline;gap:8px}
  .hero-unit{font-size:18px;font-weight:700;color:var(--muted)}
  .hero-meta{display:flex;flex-direction:column;gap:2px}
  .hero-lab{font-size:15px;font-weight:600}
  .hero-sub{font-size:13px;color:var(--muted)}
  .hero-ctx{margin-top:8px;font-size:13px;color:var(--muted);max-width:680px}
  @media (max-width:640px){
    .wrap{padding:12px 12px 26px}
    header.brand{padding:12px 14px;gap:10px}
    .brandtxt h1{font-size:18px}
    .updated{width:100%;text-align:left}
    .domains,.tabs{flex-wrap:wrap}
    .dom{padding:9px 12px;font-size:14px}
    .tab{padding:8px 12px;font-size:13px}
    .nav .label{min-width:0;flex:1;font-size:15px}
    .dow,.grid{gap:3px}
    .dow div{font-size:10px}
    .cell{min-height:46px;padding:4px 5px;border-radius:7px}
    .cell .d{font-size:11px}
    .cell .v{font-size:11px}
    .cell .u{display:none}
    .bars{height:160px}
    .xlabels div{font-size:8px}
    .stat{min-width:0;flex:1 1 calc(50% - 7px)}
    .card{padding:14px;overflow-x:auto}
    .bigprice{font-size:32px}
    table{font-size:12px}
    .hero{padding:14px}
    .hero-num{font-size:36px}
    .hero-unit{font-size:16px}
    .trendpill{font-size:12px}
  }
</style>
</head>
<body>
<header class="brand">
  <span class="logoplate"><img src="lms_logo.png" alt="Logica Media Service — Soluzioni per l'Energia"/></span>
  <div class="brandtxt">
    <h1>Mercati Energetici</h1>
    <span class="sub">PUN elettrico e Gas PSV ufficiali GME · aggiornati ogni giorno</span>
  </div>
  <span class="hspacer"></span>
  <span class="updated" id="updated">aggiornato __GEN__</span>
</header>

<section class="herowrap"><div class="hero" id="hero"></div></section>

<div class="wrap">
  <div class="domains">
    <div class="dom elec active" data-dom="elec"><span class="dot" style="background:var(--elec)"></span>⚡ Elettricità · PUN</div>
    <div class="dom gas" data-dom="gas"><span class="dot" style="background:var(--gas)"></span>🔥 Gas · PSV</div>
  </div>
  <div class="tabs">
    <div class="tab active" data-view="day">📅 Giorno</div>
    <div class="tab" data-view="month">📊 Mese</div>
    <div class="tab" data-view="year">📈 Anno</div>
    <div class="tab" data-view="forward">🔮 Forward</div>
    <div class="tab" data-view="consigli">💡 Consigli</div>
  </div>
  <div class="nav"><button id="prev">‹</button><div class="label" id="navlabel"></div><button id="next">›</button></div>
  <div id="content"></div>

  <div class="certs" id="certs" style="display:none">
    <div class="lbl">Certificazioni</div>
    <div id="certbody"></div>
  </div>
</div>

<footer class="brand">
  <div class="legal">
    Fonte dati: Gestore dei Mercati Energetici (GME) — mercatoelettrico.org. PUN: prezzo MGP orario.
    Gas PSV: prezzo di riferimento MGP-GAS. Dati a fini informativi, soggetti alle Condizioni di utilizzo
    e al Disclaimer di GME.
  </div>
</footer>

<script>
const ELEC = /*__ELEC__*/;
const GAS  = /*__GAS__*/;
const FORWARD = /*__FWD__*/;
// Per aggiungere i loghi delle certificazioni: CERTS=[{src:"iso9001.png",alt:"ISO 9001"}, ...]
const CERTS = [];

const MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"];
const DOW=["lun","mar","mer","gio","ven","sab","dom"];
const SMC=0.01069; // €/MWh -> ≈ €/Smc (PCS standard, indicativo)
// Consigli di consumo — potenze (kW), durata ciclo (h) o energia (kWh) indicative
const APP_CASA=[
 {n:"Lavatrice",ic:"💦",kw:2,h:1.5,label:"2 kW · ciclo ~1.5h"},
 {n:"Lavastoviglie",ic:"🍽️",kw:1.8,h:1.5,label:"1.8 kW · ciclo ~1.5h"},
 {n:"Asciugatrice",ic:"🌬️",kw:2.5,h:1.5,label:"2.5 kW · ciclo ~1.5h"},
 {n:"Forno",ic:"🔥",kw:2.2,h:1,label:"2.2 kW · ciclo ~1h"},
 {n:"Ferro da stiro",ic:"👔",kw:2.4,h:0.5,label:"2.4 kW · ciclo ~0.5h"},
 {n:"Carica auto EV",ic:"🚗",energy:10,label:"10 kWh ricarica"}
];
const BIZ=[
 {id:"ristorante",label:"Ristorante / Bar",icon:"🍽️",equip:[
   {n:"Forno professionale",ic:"🔥",kw:8,h:2,label:"8 kW · uso ~2h/giorno"},
   {n:"Abbattitore di temperatura",ic:"❄️",kw:3,h:1,label:"3 kW · ciclo ~1h"},
   {n:"Lavastoviglie industriale",ic:"🍽️",kw:6,h:1.5,label:"6 kW · ciclo ~1.5h"},
   {n:"Friggitrice",ic:"🍟",kw:4,h:1,label:"4 kW · uso ~1h/giorno"},
   {n:"Climatizzazione sala",ic:"❄️",kw:3.5,h:4,label:"3.5 kW · uso ~4h/giorno"}]},
 {id:"panificio",label:"Panificio / Pasticceria",icon:"🥖",equip:[
   {n:"Forno industriale",ic:"🔥",kw:15,h:3,label:"15 kW · cottura ~3h/giorno"},
   {n:"Impastatrice",ic:"🥣",kw:2.5,h:1,label:"2.5 kW · ciclo ~1h"},
   {n:"Cella di lievitazione",ic:"🌡️",kw:2,h:6,label:"2 kW · uso ~6h/giorno"},
   {n:"Abbattitore",ic:"❄️",kw:3,h:1,label:"3 kW · ciclo ~1h"}]},
 {id:"officina",label:"Officina meccanica",icon:"🔧",equip:[
   {n:"Compressore aria",ic:"💨",kw:5.5,h:3,label:"5.5 kW · uso ~3h/giorno"},
   {n:"Saldatrice",ic:"⚡",kw:6,h:1.5,label:"6 kW · uso ~1.5h/giorno"},
   {n:"Ponte elevatore elettrico",ic:"🚗",kw:2.2,h:2,label:"2.2 kW · uso ~2h/giorno"},
   {n:"Cabina di verniciatura",ic:"🎨",kw:9,h:1,label:"9 kW · ciclo ~1h"}]},
 {id:"negozio",label:"Negozio / Retail",icon:"🛍️",equip:[
   {n:"Climatizzazione punto vendita",ic:"❄️",kw:4,h:8,label:"4 kW · uso ~8h/giorno"},
   {n:"Vetrina refrigerata",ic:"🧊",kw:1.5,h:10,label:"1.5 kW · uso ~10h/giorno"},
   {n:"Illuminazione LED",ic:"💡",kw:2,h:10,label:"2 kW · uso ~10h/giorno"}]},
 {id:"ufficio",label:"Ufficio",icon:"🏢",equip:[
   {n:"Climatizzazione uffici",ic:"❄️",kw:5,h:8,label:"5 kW · uso ~8h/giorno"},
   {n:"Sala server",ic:"🖥️",kw:3,continuous:true,label:"3 kW · funzionamento continuo"},
   {n:"Ricarica veicoli aziendali",ic:"🚗",energy:30,label:"30 kWh ricarica flotta"}]},
 {id:"lavanderia",label:"Lavanderia industriale",icon:"🧺",equip:[
   {n:"Lavatrice industriale",ic:"💦",kw:9,h:1,label:"9 kW · ciclo ~1h"},
   {n:"Asciugatrice industriale",ic:"🌬️",kw:12,h:1,label:"12 kW · ciclo ~1h"},
   {n:"Stiratrice a vapore",ic:"♨️",kw:7,h:2,label:"7 kW · uso ~2h/giorno"}]},
 {id:"hotel",label:"Hotel / Agriturismo",icon:"🏨",equip:[
   {n:"Cucina industriale",ic:"🍳",kw:10,h:3,label:"10 kW · uso ~3h/giorno"},
   {n:"Lavatrici biancheria",ic:"💦",kw:6,h:1.5,label:"6 kW · ciclo ~1.5h"},
   {n:"Pompa filtraggio piscina",ic:"🏊",kw:2,h:6,label:"2 kW · uso ~6h/giorno"},
   {n:"Climatizzazione camere",ic:"❄️",kw:6,h:8,label:"6 kW · uso ~8h/giorno"}]},
 {id:"palestra",label:"Palestra / Centro estetico",icon:"💪",equip:[
   {n:"Sauna / bagno turco",ic:"🔥",kw:6,h:3,label:"6 kW · uso ~3h/giorno"},
   {n:"Climatizzazione sala corsi",ic:"❄️",kw:4,h:10,label:"4 kW · uso ~10h/giorno"},
   {n:"Lavatrici asciugamani",ic:"💦",kw:3,h:1.5,label:"3 kW · ciclo ~1.5h"}]},
 {id:"supermercato",label:"Supermercato",icon:"🛒",equip:[
   {n:"Banchi frigo refrigerati",ic:"🧊",kw:8,continuous:true,label:"8 kW · funzionamento continuo"},
   {n:"Cella surgelati",ic:"❄️",kw:10,continuous:true,label:"10 kW · funzionamento continuo"},
   {n:"Climatizzazione punto vendita",ic:"❄️",kw:7,h:10,label:"7 kW · uso ~10h/giorno"},
   {n:"Illuminazione LED",ic:"💡",kw:5,h:12,label:"5 kW · uso ~12h/giorno"},
   {n:"Ricarica carrelli elevatori",ic:"🚚",energy:20,label:"20 kWh ricarica"}]},
 {id:"manifattura",label:"Azienda manifatturiera",icon:"🏭",equip:[
   {n:"Linea di produzione / CNC",ic:"⚙️",kw:25,h:8,label:"25 kW · uso ~8h/giorno"},
   {n:"Compressore industriale",ic:"💨",kw:15,h:6,label:"15 kW · uso ~6h/giorno"},
   {n:"Forno trattamento termico",ic:"🔥",kw:30,h:4,label:"30 kW · ciclo ~4h"},
   {n:"Saldatura robotizzata",ic:"⚡",kw:12,h:5,label:"12 kW · uso ~5h/giorno"},
   {n:"Aspirazione/ventilazione",ic:"🌬️",kw:8,h:8,label:"8 kW · uso ~8h/giorno"},
   {n:"Ricarica mezzi aziendali",ic:"🚚",energy:25,label:"25 kWh ricarica"}]}
];

let domain="elec", view="day", selDate=null, fwdType="base";
let consMode="casa", consBiz="ristorante";
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
function heat(v,mn,mx){if(mx===mn)return "#dff0e4";const t=(v-mn)/(mx-mn);return `hsl(${140-t*140},72%,72%)`;}
// Semaforo PUN a soglie fisse: verde <=110 €/MWh (<=11 c€/kWh), giallo 110-140, rosso >=140 (>=14 c€/kWh)
function bandColor(mwh){if(mwh<=110)return "#bbf7d0";if(mwh<140)return "#fef08a";return "#fecaca";}

function setActive(){
  document.querySelectorAll(".dom").forEach(e=>e.classList.toggle("active",e.dataset.dom===domain));
  document.querySelectorAll(".tab").forEach(e=>e.classList.toggle("active",e.dataset.view===view));
}
function init(){
  const ks=keys();
  if(ks.length){const last=parse(ks[ks.length-1]);cur={y:last.y,m:last.m,d:last.d};selDate=ks[ks.length-1];}
  renderCerts();
}
function heroTrend(ks, dvFn){
  if(ks.length < 2) return null;
  const last = dvFn(ks[ks.length-1]);
  const prev = ks.slice(-8, -1).map(dvFn);
  if(!prev.length) return null;
  const base = prev.reduce((a,b)=>a+b,0)/prev.length;
  if(!base) return null;
  return (last - base) / base * 100;
}
function renderHero(){
  const host = document.getElementById('hero');
  if(!host) return;
  const ks = keys();
  if(!ks.length){ host.innerHTML=''; return; }
  const dv = D().dayVal;
  const lk = ks[ks.length-1];
  const mwh = dv(lk);
  const ckwh = mwh/10;
  const p = parse(lk);
  const tr = heroTrend(ks, dv);
  const isUp = tr!=null && tr>0;
  const pill = tr==null ? '' :
    `<span class="trendpill ${isUp?'up':'down'}">${isUp?'↗ +':'↘ '}${tr.toFixed(1)}% <small style="font-weight:500">sulla settimana</small></span>`;
  let bigVal, bigUnit, sub, lab;
  if(domain==='gas'){
    const smc = mwh*SMC;
    bigVal = eur(smc,4);  bigUnit = '€/Smc';
    sub = `${eur(mwh)} €/MWh · ≈ ${eur(ckwh,1)} c€/kWh`;
    lab = `${D().name} · ${p.d} ${MESI[p.m]} ${p.y}`;
  } else {
    bigVal = eur(ckwh,1); bigUnit = 'c€/kWh';
    sub = `${eur(mwh)} €/MWh`;
    lab = `${D().name} medio · ${p.d} ${MESI[p.m]} ${p.y}`;
  }
  const ctx = domain==='gas'
    ? 'Il PSV è il prezzo all’ingrosso del gas in Italia: più è basso, meno incide la materia prima gas in bolletta.'
    : 'Il PUN è il prezzo all’ingrosso dell’energia elettrica in Italia: più è basso, meno costa la materia prima in bolletta.';
  host.innerHTML = `
    <div class="hero-main">
      <div class="hero-num">${bigVal}<span class="hero-unit">${bigUnit}</span></div>
      <div class="hero-meta">
        <div class="hero-lab">${lab}</div>
        <div class="hero-sub">${sub}</div>
      </div>
      ${pill}
    </div>
    <div class="hero-ctx">${ctx}</div>`;
}
function render(){
  applyAccent(); setActive();
  renderHero();
  if(view==="forward"){renderForward();return;}
  if(view==="consigli"){renderConsigli();return;}
  const ks=keys();
  if(!ks.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato ${D().name} disponibile.</div></div>`;navlabel.textContent="—";return;}
  if(view==="day")renderDay();else if(view==="month")renderMonth();else renderYear();
}
// ---- Forward / Futures ----
function fwdDom(){return domain==="elec"?"power":"gas";}
function monthAdd(ym,n){let[y,m]=ym.split("-").map(Number);let idx=y*12+(m-1)+n;return `${Math.floor(idx/12)}-${String(idx%12+1).padStart(2,"0")}`;}
function qOf(ym){let[y,m]=ym.split("-").map(Number);return `${y}-Q${Math.floor((m-1)/3)+1}`;}
function ymLabel(ym){const[y,m]=ym.split("-");return MESI[+m-1].slice(0,3)+" "+y.slice(2);}
function fwdCurve(F){
  const M=F.months||{},Q=F.quarters||{},Y=F.years||{};
  const mk=Object.keys(M).sort();let start=mk[0];
  if(!start){const qk=Object.keys(Q).sort();if(!qk.length)return [];const[y,q]=qk[0].split("-Q");start=`${y}-${String((+q-1)*3+1).padStart(2,"0")}`;}
  const out=[];
  for(let i=0;i<24;i++){const ym=monthAdd(start,i);const y=ym.split("-")[0];
    let p=(M[ym]!=null)?M[ym]:(Q[qOf(ym)]!=null)?Q[qOf(ym)]:(Y[y]!=null)?Y[y]:null;
    if(p==null){if(i>0)break;else continue;}
    out.push({ym,price:p});}
  return out;
}
function renderForward(){
  navlabel.textContent="Curva forward";
  const isPower=domain==="elec";
  const F=(FORWARD||{})[fwdDom()]||{};
  const src=(isPower&&fwdType==="peak")?(F.peak||{}):F;
  const toggle=isPower?`<div class="fwdtoggle"><button class="${fwdType==="base"?"on":""}" data-ft="base">Baseload</button><button class="${fwdType==="peak"?"on":""}" data-ft="peak">Peak</button></div>`:"";
  const wire=()=>document.querySelectorAll("[data-ft]").forEach(b=>b.onclick=()=>{fwdType=b.dataset.ft;render();});
  const tit=isPower?("Energia ("+(fwdType==="peak"?"peak load":"baseload")+")"):"Gas PSV";
  const hasData=(src.months&&Object.keys(src.months).length)||(src.quarters&&Object.keys(src.quarters).length);
  if(!hasData){
    content.innerHTML=`<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px"><h3 style="margin:0">Curva forward — ${tit}</h3>${toggle}</div><div class="empty-note">Curva forward non ancora disponibile per questa selezione.</div></div>`;
    wire();return;
  }
  const curve=fwdCurve(src);const prices=curve.map(c=>c.price),labels=curve.map(c=>ymLabel(c.ym));
  const front=prices[0],peak=Math.max(...prices),pI=prices.indexOf(peak);
  const i12=Math.min(12,curve.length-1),m12=prices[i12];
  const trend=front?((m12-front)/front*100):0;
  const trendTxt=trend<=0?`Backwardation ↘ ${trend.toFixed(1)}%`:`Contango ↗ +${trend.toFixed(1)}%`;
  const smc=domain==="gas"?`<div class="val" style="font-size:13px">≈ ${eur(front*SMC,4)} <small>€/Smc</small></div>`:"";
  const qLabel=k=>{const[y,q]=k.split("-Q");return `Q${q} ${y}`;};
  const sLabel=k=>k.replace("SS-","Estate ").replace("WS-","Inverno ");
  const rows=(arr,fk)=>arr.map(([k,v])=>`<tr><td>${fk(k)}</td><td>${eur(v)} €/MWh</td></tr>`).join("");
  const qs=Object.entries(src.quarters||{}).sort(),ys=Object.entries(src.years||{}).sort(),ss=Object.entries(F.seasons||{}).sort();
  let tbl="";
  if(qs.length)tbl+=`<tr><th colspan="2">Trimestri</th></tr>`+rows(qs,qLabel);
  if(ss.length&&!isPower)tbl+=`<tr><th colspan="2">Stagioni</th></tr>`+rows(ss,sLabel);
  if(ys.length)tbl+=`<tr><th colspan="2">Anni (Cal)</th></tr>`+rows(ys,k=>"Cal "+k);
  content.innerHTML=`<div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
      <h3 style="margin:0">Curva forward — ${tit}</h3>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">${toggle}<span class="trendpill ${trend<=0?"down":"up"}">${trendTxt}</span></div></div>
    <div class="stats">
      <div class="stat"><div class="k">Front · ${labels[0]}</div><div class="val">${eur(front)} <small>€/MWh</small></div>${smc}</div>
      <div class="stat"><div class="k">Picco · ${labels[pI]}</div><div class="val" style="color:#c0392b">${eur(peak)} <small>€/MWh</small></div></div>
      <div class="stat"><div class="k">A 12 mesi · ${labels[i12]}</div><div class="val" style="color:var(--elec)">${eur(m12)} <small>€/MWh</small></div></div>
    </div>
    ${barChart(prices,labels,{xevery:2})}
    <div class="hint">Il mercato si aspetta prezzi ${trend<=0?"in discesa":"in salita"}. Fonte: settlement (prezzo di controllo) GME ${isPower?"MTE":"MT-GAS"}, sessione ${F.as_of}.${isPower?(" Profilo: "+(fwdType==="peak"?"peak load":"baseload")+"."):""} I mesi non quotati direttamente sono stimati dal trimestre/anno di riferimento.</div>
    <table style="margin-top:14px"><tbody>${tbl}</tbody></table>
  </div>`;
  wire();
}
function barChart(values,labels,opts={}){
  const max=Math.max(...values,0),min=Math.min(...values,0),span=(max-min)||1;let bars="",xs="";
  values.forEach((v,i)=>{const h=Math.max(2,((v-min)/span)*100);
    const bg=opts.band?`;background:${bandColor(v)}`:"";
    bars+=`<div class="bar" style="height:${h}%${bg}"><span class="tip">${labels[i]}: ${eur(v)} ${D().unit}</span></div>`;
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
  const dv=D().dayVal;
  // heatmap relativa al mese visualizzato (così le differenze del mese sono visibili)
  const mk=monthKeys(cur.y,cur.m);
  let mn=Infinity,mx=-Infinity; mk.forEach(k=>{const a=dv(k);mn=Math.min(mn,a);mx=Math.max(mx,a);});
  const nd=daysInMonth(cur.y,cur.m),fd=(new Date(cur.y,cur.m,1).getDay()+6)%7;let cells="";
  for(let i=0;i<fd;i++)cells+=`<div class="cell empty"></div>`;
  for(let d=1;d<=nd;d++){const key=fmt(cur.y,cur.m,d);
    if(D().data[key]!=null){const a=dv(key);
      const col=(domain==="elec")?bandColor(a):heat(a,mn,mx);
      cells+=`<div class="cell has" style="background:${col}" data-key="${key}"><div class="d">${d}</div><div><span class="v">${eur(a,1)}</span> <span class="u">€/MWh</span></div></div>`;
    }else cells+=`<div class="cell"><div class="d">${d}</div></div>`;}
  let detail=`<div class="hint">Clicca un giorno colorato per il dettaglio.</div>`;
  if(selDate&&D().data[selDate]!=null&&parse(selDate).y===cur.y&&parse(selDate).m===cur.m)detail=dayDetail(selDate);
  const legend=(domain==="elec")?`<div class="legend"><span><i style="background:#bbf7d0"></i>≤ 11 c€/kWh (≤110 €/MWh)</span><span><i style="background:#fef08a"></i>11,1–13,9 c€/kWh</span><span><i style="background:#fecaca"></i>≥ 14 c€/kWh (≥140 €/MWh)</span></div>`:"";
  content.innerHTML=`<div class="card"><div class="dow">${DOW.map(x=>`<div>${x}</div>`).join("")}</div><div class="grid">${cells}</div>${legend}</div><div style="height:16px"></div>${detail}`;
  document.querySelectorAll(".cell.has").forEach(c=>c.onclick=()=>{selDate=c.dataset.key;render();});
}
function dayDetail(key){
  const p=parse(key);
  if(D().hourly){
    const vals=ELEC[key],a=avg(vals),mn=Math.min(...vals),mx=Math.max(...vals);
    const labels=vals.map((_,i)=>String(i+1).padStart(2,"0"));let rows="";
    vals.forEach((v,i)=>{const bg=bandColor(v);rows+=`<tr><td>${String(i+1).padStart(2,"0")}:00</td><td style="background:${bg}">${eur(v)}</td><td style="background:${bg}">${eur(v/1000,4)}</td></tr>`;});
    return `<div class="card"><h3 style="margin:0 0 4px">Profilo orario PUN — ${p.d} ${MESI[p.m]} ${p.y}</h3>
      <div class="stats">${statBlock("Media giorno",a)}${statBlock("Minimo",mn)}${statBlock("Massimo",mx)}</div>
      ${barChart(vals,labels,{band:true})}
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
  let miI=0,maI=0; dayVals.forEach((v,i)=>{if(v<dayVals[miI])miI=i;if(v>dayVals[maI])maI=i;});
  const mese3=MESI[cur.m].slice(0,3);
  const mAvg=D().monthAvg(ks),labels=ks.map(k=>String(parse(k).d));
  const sb=domain==="gas"?statGas:statBlock;
  content.innerHTML=`<div class="card"><h3 style="margin:0 0 4px">${D().name} — medie giornaliere ${MESI[cur.m]} ${cur.y}</h3>
    <div class="stats">${sb("Media mese",mAvg)}${sb("Giorno più basso · "+parse(ks[miI]).d+" "+mese3,dayVals[miI])}${sb("Giorno più alto · "+parse(ks[maI]).d+" "+mese3,dayVals[maI])}
    <div class="stat"><div class="k">Giorni</div><div class="val">${ks.length}</div></div></div>
    ${barChart(dayVals,labels,{xevery:2})}</div>`;
}
function renderYear(){
  navlabel.textContent=`${cur.y}`;
  const out=[]; for(let m=0;m<12;m++){const ks=monthKeys(cur.y,m);out.push(ks.length?D().monthAvg(ks):null);}
  const present=out.map((v,i)=>({v,i})).filter(o=>o.v!=null);
  if(!present.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato per il ${cur.y}.</div></div>`;return;}
  const yks=yearKeys(cur.y); const yAvg=D().monthAvg(yks);
  const vals=present.map(o=>o.v),labels=present.map(o=>MESI[o.i].slice(0,3));
  let lo=present[0],hi=present[0];present.forEach(o=>{if(o.v<lo.v)lo=o;if(o.v>hi.v)hi=o;});
  const sb=domain==="gas"?statGas:statBlock;
  content.innerHTML=`<div class="card"><h3 style="margin:0 0 4px">${D().name} — medie mensili ${cur.y}</h3>
    <div class="stats">${sb("Media anno",yAvg)}${sb("Mese più basso · "+MESI[lo.i].slice(0,3),lo.v)}${sb("Mese più alto · "+MESI[hi.i].slice(0,3),hi.v)}</div>
    ${barChart(vals,labels,{})}</div>`;
}
function consDay(){if(selDate&&ELEC[selDate])return selDate;const ks=Object.keys(ELEC).sort();return ks.length?ks[ks.length-1]:null;}
function calcApp(prices,energy){
  const costs=prices.map(p=>energy*p/1000);
  const idx=[...costs.keys()];
  const byCost=[...idx].sort((a,b)=>costs[a]-costs[b]);
  const best=byCost.slice(0,3).sort((a,b)=>a-b);
  const worst=byCost[byCost.length-1];
  const minCost=Math.min(...best.map(i=>costs[i]));
  return {costs,best,worst,risparmio:costs[worst]-minCost};
}
function appCard(a,prices){
  if(a.continuous){
    const daily=a.kw*prices.reduce((s,p)=>s+p,0)/1000;
    return `<div class="acard"><div class="ahead"><div><span class="aic">${a.ic}</span><b>${a.n}</b><div class="asub">${a.label}</div></div></div><div class="acont">⚠️ Funzionamento continuo H24 — non programmabile</div><div style="margin-top:9px;display:flex;justify-content:space-between;align-items:center"><span style="font-size:12px;color:var(--muted)">Costo stimato giornaliero</span><b style="font-size:17px">${eur(daily,2)}€</b></div></div>`;
  }
  const energy=(a.energy!=null)?a.energy:a.kw*a.h;
  const r=calcApp(prices,energy);
  const chips=r.best.map(i=>`<span class="chip">${String(i).padStart(2,"0")}:00 ~${eur(r.costs[i],2)}€</span>`).join("");
  return `<div class="acard"><div class="ahead"><div><span class="aic">${a.ic}</span><b>${a.n}</b><div class="asub">${a.label}</div></div><div class="asave">−${eur(r.risparmio,2)}€<div class="asublab">risparmio/giorno</div></div></div><div class="abest">✅ Migliori ore di accensione:</div><div>${chips}</div><div class="aavoid">🔴 Evita: <b>${String(r.worst).padStart(2,"0")}:00</b> · costa ${eur(r.risparmio,2)}€ in più</div></div>`;
}
function renderConsigli(){
  navlabel.textContent=`${MESI[cur.m]} ${cur.y}`;
  const key=consDay();
  if(!key){content.innerHTML=`<div class="card"><div class="empty-note">Dati PUN non disponibili.</div></div>`;return;}
  // Calendario sempre visibile (colori semaforo PUN), clic = scegli il giorno
  const nd=daysInMonth(cur.y,cur.m),fd=(new Date(cur.y,cur.m,1).getDay()+6)%7;let cells="";
  for(let i=0;i<fd;i++)cells+=`<div class="cell empty"></div>`;
  for(let d=1;d<=nd;d++){const k=fmt(cur.y,cur.m,d);
    if(ELEC[k]){const a=avg(ELEC[k]);const sel=(k===key);
      cells+=`<div class="cell has" style="background:${bandColor(a)}${sel?';outline:3px solid #111;outline-offset:-2px':''}" data-cday="${k}"><div class="d">${d}</div><div><span class="v">${eur(a,1)}</span> <span class="u">€/MWh</span></div></div>`;
    }else cells+=`<div class="cell"><div class="d">${d}</div></div>`;}
  const cal=`<div class="card"><div class="dow">${DOW.map(x=>`<div>${x}</div>`).join("")}</div><div class="grid">${cells}</div><div class="hint">Clicca un giorno per i consigli di consumo di quella data.</div></div>`;
  // Consigli per il giorno scelto
  const prices=ELEC[key],p=parse(key);
  let mh=0,xh=0;prices.forEach((v,i)=>{if(v<prices[mh])mh=i;if(v>prices[xh])xh=i;});
  const ckwh=prices[mh]/10,ckwhX=prices[xh]/10;
  let body="";
  if(consMode==="casa"){ body=`<div class="acards">${APP_CASA.map(a=>appCard(a,prices)).join("")}</div>`; }
  else{
    const biz=BIZ.find(b=>b.id===consBiz)||BIZ[0];
    const grid=BIZ.map(b=>`<button class="bizbtn ${b.id===biz.id?'on':''}" data-biz="${b.id}">${b.icon} ${b.label}</button>`).join("");
    body=`<div style="font-size:13px;color:var(--muted);font-weight:600;margin-bottom:8px">Seleziona il tipo di attività:</div><div class="bizgrid">${grid}</div><div style="font-size:13px;color:#15803d;font-weight:700;margin-bottom:8px">⚙️ Attrezzature consigliate per: ${biz.label}</div><div class="acards">${biz.equip.map(a=>appCard(a,prices)).join("")}</div>`;
  }
  const advice=`<div class="card"><div class="consbanner">💚 Ora più conveniente: <b>ore ${String(mh).padStart(2,"0")}:00</b> → ${eur(ckwh,1)} c€/kWh</div><div class="consbanner red">🔴 Ora più cara: <b>ore ${String(xh).padStart(2,"0")}:00</b> → ${eur(ckwhX,1)} c€/kWh · riduci i consumi in questa fascia</div><div class="moderow"><button class="modebtn ${consMode==="casa"?"on":""}" data-mode="casa">🏠 Casa</button><button class="modebtn ${consMode==="azienda"?"on":""}" data-mode="azienda">🏢 Azienda</button></div><div class="hint" style="margin-top:0;margin-bottom:10px">Consigli per <b>${p.d} ${MESI[p.m]} ${p.y}</b>, in base al PUN orario. Stime su potenze tipiche, solo prezzo energia (escluse imposte/oneri).</div>${body}</div>`;
  content.innerHTML=cal+`<div style="height:16px"></div>`+advice;
  document.querySelectorAll("[data-cday]").forEach(c=>c.onclick=()=>{selDate=c.dataset.cday;render();});
  document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{consMode=b.dataset.mode;render();});
  document.querySelectorAll("[data-biz]").forEach(b=>b.onclick=()=>{consBiz=b.dataset.biz;render();});
}
function step(dir){if(view==="forward")return;if(view==="year")cur.y+=dir;else{cur.m+=dir;if(cur.m<0){cur.m=11;cur.y--;}if(cur.m>11){cur.m=0;cur.y++;}}render();}
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
