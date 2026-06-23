#!/usr/bin/env python3
"""
LMS Energy — PUN UFFICIALE dal portale pubblico GME (mercatoelettrico.org)
==========================================================================

Niente ENTSO-E, niente API key, niente user/password.
Prende i prezzi PUN del MGP dalla pagina pubblica "Esiti MGP/PUN" del sito GME,
accumula uno STORICO in CSV e genera un'app CALENDARIO (HTML offline) per
navigare indietro nel tempo: PUN orario di un singolo giorno + media mese/anno.

Meccanismo (app Angular su DotNetNuke):
  1. Apre la pagina pubblica con una sessione HTTP (cookie di sessione).
  2. Estrae al volo il token antiforgery __RequestVerificationToken e i
     parametri del modulo ModuleId/TabId.
  3. Chiama in GET l'endpoint JSON che usa il sito stesso:
        GET /DesktopModules/GmeEsitiPrezziME/API/item/GetMEPrezzi
            ?DataInizio=YYYYMMDD&DataFine=YYYYMMDD
            &Granularita=h&Mercato=MGP&Zona=PUN&Tipologia=PUN
        -> [{"df":20260621,"h":1,"p":134.45,"qh":4}, ...]
           df=data | h=ora(1..24) | p=PUN €/MWh | qh=quarto d'ora
Token e parametri sono dati di SESSIONE temporanei: NON sono credenziali.

USO TIPICO
----------
    # PUN di oggi -> aggiorna JSON, CSV storico e ricostruisce il calendario
    python pun_gme.py

    # popolamento iniziale dello storico (resumable: salta i giorni già presenti)
    python pun_gme.py --backfill 2026-04-01 2026-06-21

    # solo ricostruire l'app calendario dallo storico esistente
    python pun_gme.py --rebuild-viewer

File prodotti:
    pun_gme.json         ultimo giorno (€/MWh + €/kWh)
    pun_storico.csv      storico (data,ora,pun_eur_mwh)  <-- accumula nel tempo
    pun_calendario.html  app calendario offline (doppio clic per aprirla)

NOTE
----
* Dati del giorno disponibili di norma dopo le ~14:00 (esiti MGP). Per "domani"
  di norma NON ci sono ancora: usa today/yesterday.
* Uso dei dati soggetto alle "Condizioni di utilizzo" e al "Disclaimer" di GME
  (artt. 7, 8, 10, 13). Verificarne il rispetto per il proprio caso d'uso.

Requisiti:  pip install requests   (matplotlib solo per --chart)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("Manca la dipendenza 'requests'. Installa con: pip install requests")


# --------------------------------------------------------------------------- #
# Costanti (verificate sul sito GME, giugno 2026)
# --------------------------------------------------------------------------- #
BASE = "https://www.mercatoelettrico.org"
PAGE_URL = BASE + "/it-it/Home/Esiti/Elettricita/MGP/Esiti/PUN"
SERVICE_URL = BASE + "/DesktopModules/GmeEsitiPrezziME/API/item/GetMEPrezzi"

DATE_FMT = "%Y%m%d"
GRANULARITA, MERCATO, ZONA, TIPOLOGIA = "h", "MGP", "PUN", "PUN"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 30

DEFAULT_CSV = "pun_storico.csv"
DEFAULT_VIEWER = "pun_calendario.html"

log = logging.getLogger("pun_gme")


# --------------------------------------------------------------------------- #
# Sessione GME + estrazione token
# --------------------------------------------------------------------------- #
def _first(*patterns, text):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    return None


def open_session():
    """Apre la pagina pubblica e restituisce (session, headers_pronti)."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, */*"})
    r = session.get(PAGE_URL, timeout=TIMEOUT)
    r.raise_for_status()
    html = r.text
    token = _first(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"',
                   r'value="([^"]+)"[^>]*name="__RequestVerificationToken"', text=html)
    if not token:
        raise RuntimeError("Token antiforgery non trovato (markup GME cambiato? usa --debug).")
    module_id = _first(r'"ModuleId"\s*:\s*"?(\d+)', r'DnnModule-(\d+)"', text=html)
    tab_id = _first(r'"TabId"\s*:\s*"?(\d+)', text=html)
    headers = {"RequestVerificationToken": token, "X-Requested-With": "XMLHttpRequest",
               "Referer": PAGE_URL}
    if module_id:
        headers["ModuleId"] = module_id
    if tab_id:
        headers["TabId"] = tab_id
    log.debug("Sessione aperta — ModuleId=%s TabId=%s", module_id, tab_id)
    return session, headers


def get_day(session, headers, date, debug=False):
    """Restituisce lista (ora:int, pun:float) per un giorno, o [] se assente."""
    ds = date.strftime(DATE_FMT)
    query = {"DataInizio": ds, "DataFine": ds, "Granularita": GRANULARITA,
             "Mercato": MERCATO, "Zona": ZONA, "Tipologia": TIPOLOGIA}
    resp = session.get(SERVICE_URL, headers=headers, params=query, timeout=TIMEOUT)
    if debug:
        log.info("HTTP %s — %s", resp.status_code, resp.text[:200])
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError("Risposta non-JSON: controlla SERVICE_URL/parametri (--debug).")
    return _normalize_records(data)


def _normalize_records(data):
    if isinstance(data, dict):
        for k in ("d", "data", "Data", "result", "items"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        if not isinstance(row, dict):
            continue
        ora = row.get("h", row.get("Ora", row.get("ora")))
        pun = row.get("p", row.get("PUN", row.get("prezzo")))
        if pun is None:
            continue
        try:
            out.append((int(float(ora)), float(str(pun).replace(",", "."))))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda t: t[0])
    return out


def fetch_pun(date, debug=False):
    session, headers = open_session()
    records = get_day(session, headers, date, debug=debug)
    if not records:
        raise RuntimeError(
            f"Nessun prezzo per {date:%Y-%m-%d}: dati non ancora pubblicati "
            "(riprova dopo le ~14:00) o giorno senza esiti."
        )
    return date.strftime("%Y-%m-%d"), records


# --------------------------------------------------------------------------- #
# Storico CSV  (formato long: data,ora,pun_eur_mwh)
# --------------------------------------------------------------------------- #
def load_history(csv_path):
    """Restituisce dict {('YYYY-MM-DD'): [p1..p24]} ordinato per ora."""
    hist = {}
    if not os.path.exists(csv_path):
        return hist
    tmp = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d = row["data"]
                ora = int(row["ora"])
                p = float(row["pun_eur_mwh"])
            except (KeyError, ValueError):
                continue
            tmp.setdefault(d, {})[ora] = p
    for d, ore in tmp.items():
        hist[d] = [ore[h] for h in sorted(ore)]
    return dict(sorted(hist.items()))


def save_history(csv_path, hist):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "ora", "pun_eur_mwh"])
        for d in sorted(hist):
            for i, p in enumerate(hist[d], start=1):
                w.writerow([d, i, f"{p:.2f}"])


def upsert_day(csv_path, date_label, records):
    hist = load_history(csv_path)
    hist[date_label] = [p for _, p in records]
    save_history(csv_path, hist)
    return hist


# --------------------------------------------------------------------------- #
# Output JSON singolo giorno + grafico
# --------------------------------------------------------------------------- #
def build_output(date_label, records):
    mwh = [round(p, 2) for _, p in records]
    kwh = [round(p / 1000.0, 5) for _, p in records]
    avg = sum(p for _, p in records) / len(records) if records else None
    return {
        "data": date_label,
        "fonte": "GME — mercatoelettrico.org, Esiti MGP (PUN UFFICIALE)",
        "mercato": MERCATO, "granularita": GRANULARITA,
        "aggiornato_il": datetime.now().astimezone().isoformat(),
        "ore": len(mwh),
        "prezzi_orari_eur_mwh": mwh, "prezzi_orari_eur_kwh": kwh,
        "media_giornaliera_eur_mwh": round(avg, 2) if avg is not None else None,
        "media_giornaliera_eur_kwh": round(avg / 1000.0, 5) if avg is not None else None,
        "min_eur_mwh": min(mwh) if mwh else None,
        "max_eur_mwh": max(mwh) if mwh else None,
    }


def make_chart(records, date_label, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        log.warning("matplotlib non installato: salto il grafico.")
        return
    hours = [o for o, _ in records]
    vals = [v for _, v in records]
    avg = sum(vals) / len(vals) if vals else 0
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(hours, vals, color="#16a34a", alpha=0.85, width=0.8)
    ax.axhline(avg, color="#dc2626", linestyle="--", linewidth=1,
               label=f"media {avg:.2f} €/MWh ({avg/1000:.4f} €/kWh)")
    ax.set_title(f"PUN ufficiale GME — {date_label}")
    ax.set_xlabel("Ora"); ax.set_ylabel("€/MWh")
    ax.set_xticks(hours); ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=8)
    ax.grid(axis="y", alpha=0.3); ax.legend(loc="upper left", fontsize=9)
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim()[0] / 1000.0, ax.get_ylim()[1] / 1000.0)
    ax2.set_ylabel("€/kWh"); ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    log.info("Grafico salvato in %s", path)


# --------------------------------------------------------------------------- #
# App calendario (HTML offline, dati embedded, zero dipendenze)
# --------------------------------------------------------------------------- #
def write_viewer(html_path, hist):
    payload = json.dumps(hist, separators=(",", ":"))
    gen = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    html = VIEWER_TEMPLATE.replace("/*__DATA__*/", payload).replace("__GEN__", gen)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Calendario aggiornato: %s (%d giorni)", html_path, len(hist))


# --------------------------------------------------------------------------- #
# Backfill
# --------------------------------------------------------------------------- #
def backfill(csv_path, start, end, delay=0.15, debug=False):
    hist = load_history(csv_path)
    session, headers = open_session()
    d = start
    added = skipped = failed = 0
    while d <= end:
        label = d.strftime("%Y-%m-%d")
        if label in hist and len(hist[label]) >= 23:
            skipped += 1
            d += timedelta(days=1)
            continue
        try:
            recs = get_day(session, headers, d, debug=debug)
            if recs:
                hist[label] = [p for _, p in recs]
                added += 1
            else:
                failed += 1
                log.debug("Nessun dato per %s", label)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            log.warning("Errore su %s: %s", label, exc)
            # token scaduto? riapri la sessione
            try:
                session, headers = open_session()
            except Exception:
                pass
        time.sleep(delay)
        d += timedelta(days=1)
    save_history(csv_path, hist)
    log.info("Backfill: +%d giorni, %d già presenti, %d senza dati.", added, skipped, failed)
    return hist


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def resolve_date(date_arg):
    today = datetime.now()
    mapping = {"today": today, "tomorrow": today + timedelta(days=1),
               "yesterday": today - timedelta(days=1)}
    if date_arg in mapping:
        return mapping[date_arg]
    try:
        return datetime.strptime(date_arg, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Data non valida: {date_arg!r}. Usa today/tomorrow/yesterday/YYYY-MM-DD.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="PUN ufficiale GME + storico + calendario.")
    ap.add_argument("--date", default="today",
                    help="today|tomorrow|yesterday|YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default="pun_gme.json", help="JSON del giorno")
    ap.add_argument("--csv", default=DEFAULT_CSV, help="storico CSV")
    ap.add_argument("--viewer", default=DEFAULT_VIEWER, help="app calendario HTML")
    ap.add_argument("--chart", nargs="?", const="pun_gme_profilo.png", default=None,
                    help="salva PNG del profilo orario")
    ap.add_argument("--backfill", nargs=2, metavar=("START", "END"),
                    help="popola lo storico tra due date (YYYY-MM-DD)")
    ap.add_argument("--rebuild-viewer", action="store_true",
                    help="ricostruisce solo il calendario dallo storico CSV")
    ap.add_argument("--no-viewer", action="store_true", help="non rigenerare il calendario")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.rebuild_viewer:
        write_viewer(args.viewer, load_history(args.csv))
        return 0

    if args.backfill:
        start = datetime.strptime(args.backfill[0], "%Y-%m-%d")
        end = datetime.strptime(args.backfill[1], "%Y-%m-%d")
        hist = backfill(args.csv, start, end, debug=args.debug)
        if not args.no_viewer:
            write_viewer(args.viewer, hist)
        return 0

    # Esecuzione normale: un giorno.
    date = resolve_date(args.date)
    date_label, records = fetch_pun(date, debug=args.debug)
    output = build_output(date_label, records)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    if args.chart:
        make_chart(records, date_label, args.chart)
    hist = upsert_day(args.csv, date_label, records)
    if not args.no_viewer:
        write_viewer(args.viewer, hist)

    log.info("OK %s — media %s €/MWh (%s €/kWh) — storico: %d giorni.",
             date_label, output["media_giornaliera_eur_mwh"],
             output["media_giornaliera_eur_kwh"], len(hist))
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# Template dell'app calendario (vanilla JS, nessuna dipendenza, offline)
# --------------------------------------------------------------------------- #
VIEWER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PUN — Calendario storico</title>
<style>
  :root{
    --bg:#0f1419; --panel:#171f29; --panel2:#1e2733; --line:#2b3947;
    --txt:#e8edf2; --muted:#93a1b0; --accent:#16a34a; --accent2:#2563eb;
    --warn:#dc2626; --chip:#243140;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
       font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
  header{padding:18px 22px;border-bottom:1px solid var(--line);display:flex;
         align-items:baseline;gap:14px;flex-wrap:wrap}
  header h1{font-size:18px;margin:0;font-weight:650}
  header .sub{color:var(--muted);font-size:13px}
  .wrap{max-width:1080px;margin:0 auto;padding:18px 22px 60px}
  .tabs{display:flex;gap:8px;margin:8px 0 18px}
  .tab{padding:8px 16px;border:1px solid var(--line);background:var(--panel);
       color:var(--txt);border-radius:9px;cursor:pointer;font-size:14px}
  .tab.active{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
  .nav{display:flex;align-items:center;gap:12px;margin-bottom:14px}
  .nav button{background:var(--panel);border:1px solid var(--line);color:var(--txt);
       width:38px;height:38px;border-radius:9px;cursor:pointer;font-size:18px}
  .nav button:hover{background:var(--panel2)}
  .nav .label{font-size:17px;font-weight:600;min-width:190px;text-align:center;text-transform:capitalize}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
  /* calendario */
  .dow,.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
  .dow div{color:var(--muted);font-size:12px;text-align:center;padding:4px 0;text-transform:uppercase}
  .cell{aspect-ratio:1/1;border:1px solid var(--line);border-radius:10px;padding:7px;
        display:flex;flex-direction:column;justify-content:space-between;background:var(--panel2)}
  .cell.empty{background:transparent;border:none}
  .cell.has{cursor:pointer;transition:transform .06s}
  .cell.has:hover{transform:translateY(-2px);outline:2px solid var(--accent)}
  .cell .d{font-size:13px;color:var(--muted)}
  .cell .v{font-size:15px;font-weight:700}
  .cell .u{font-size:10px;color:var(--muted)}
  /* stats */
  .stats{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 16px}
  .stat{background:var(--chip);border:1px solid var(--line);border-radius:11px;padding:10px 14px;min-width:120px}
  .stat .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
  .stat .val{font-size:20px;font-weight:700;margin-top:3px}
  .stat .val small{font-size:12px;color:var(--muted);font-weight:500}
  /* bar charts (puro CSS) */
  .bars{display:flex;align-items:flex-end;gap:3px;height:220px;margin-top:8px;
        border-bottom:1px solid var(--line);padding-bottom:2px}
  .bar{flex:1;background:linear-gradient(180deg,var(--accent),#0e7a37);border-radius:3px 3px 0 0;
       position:relative;min-height:2px}
  .bar.neg{background:linear-gradient(180deg,#f59e0b,#b45309)}
  .bar:hover{outline:2px solid #fff}
  .bar .tip{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);
       background:#000;border:1px solid var(--line);padding:4px 7px;border-radius:6px;
       font-size:11px;white-space:nowrap;z-index:5;margin-bottom:4px}
  .bar:hover .tip{display:block}
  .xlabels{display:flex;gap:3px;margin-top:4px}
  .xlabels div{flex:1;text-align:center;font-size:9px;color:var(--muted)}
  .hint{color:var(--muted);font-size:13px;margin-top:10px}
  table{border-collapse:collapse;width:100%;margin-top:14px;font-size:13px}
  th,td{border:1px solid var(--line);padding:5px 8px;text-align:right}
  th:first-child,td:first-child{text-align:left}
  th{color:var(--muted);font-weight:600;background:var(--panel2)}
  .empty-note{color:var(--muted);padding:30px;text-align:center}
  a{color:var(--accent2)}
</style>
</head>
<body>
<header>
  <h1>⚡ PUN — Calendario storico</h1>
  <span class="sub">Fonte: GME (mercatoelettrico.org) · PUN ufficiale MGP · aggiornato __GEN__</span>
</header>
<div class="wrap">
  <div class="tabs">
    <div class="tab active" data-view="day">📅 Giorno</div>
    <div class="tab" data-view="month">📊 Mese</div>
    <div class="tab" data-view="year">📈 Anno</div>
  </div>
  <div class="nav">
    <button id="prev">‹</button>
    <div class="label" id="navlabel"></div>
    <button id="next">›</button>
  </div>
  <div id="content"></div>
</div>

<script>
const HISTORY = /*__DATA__*/;
const MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
              "luglio","agosto","settembre","ottobre","novembre","dicembre"];
const DOW = ["lun","mar","mer","gio","ven","sab","dom"];

// stato
let view = "day";
const keys = Object.keys(HISTORY).sort();
let cur = keys.length ? parse(keys[keys.length-1]) : {y:new Date().getFullYear(), m:new Date().getMonth(), d:1};
let selDate = keys.length ? keys[keys.length-1] : null;

function parse(s){const [y,m,d]=s.split("-").map(Number);return {y, m:m-1, d};}
function fmt(y,m,d){return `${y}-${String(m+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;}
function avg(a){return a.reduce((x,y)=>x+y,0)/a.length;}
function eur(v,dec=2){return v.toLocaleString("it-IT",{minimumFractionDigits:dec,maximumFractionDigits:dec});}

function daysInMonth(y,m){return new Date(y,m+1,0).getDate();}
function monthDays(y,m){ // giorni con dati in quel mese
  return keys.filter(k=>{const p=parse(k);return p.y===y&&p.m===m;});
}
function yearMonths(y){ // medie mensili dell'anno
  const out=[];
  for(let m=0;m<12;m++){
    const ds=monthDays(y,m);
    if(!ds.length){out.push(null);continue;}
    let all=[];ds.forEach(k=>all=all.concat(HISTORY[k]));
    out.push(avg(all));
  }
  return out;
}

// scala colore per heat (verde scuro->chiaro su min..max delle medie giornaliere)
let GMIN=Infinity,GMAX=-Infinity;
keys.forEach(k=>{const a=avg(HISTORY[k]);GMIN=Math.min(GMIN,a);GMAX=Math.max(GMAX,a);});
function heat(v){
  if(GMAX===GMIN)return "#1e3a2a";
  const t=(v-GMIN)/(GMAX-GMIN);            // 0..1
  const h=140-t*140;                       // verde(140)->rosso(0)
  return `hsl(${h},55%,30%)`;
}

const content=document.getElementById("content");
const navlabel=document.getElementById("navlabel");

function render(){
  document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.view===view));
  if(!keys.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato nello storico.<br>Esegui <code>python pun_gme.py --backfill 2026-04-01 2026-06-21</code> per popolarlo.</div></div>`;navlabel.textContent="—";return;}
  if(view==="day")renderDay();
  else if(view==="month")renderMonth();
  else renderYear();
}

function barChart(values, labels, opts={}){
  const max=Math.max(...values,0), min=Math.min(...values,0), span=(max-min)||1;
  let bars="", xs="";
  values.forEach((v,i)=>{
    const h=Math.max(2,((v-min)/span)*100);
    const cls=v<0?"bar neg":"bar";
    bars+=`<div class="${cls}" style="height:${h}%"><span class="tip">${labels[i]}: ${eur(v)} €/MWh</span></div>`;
    xs+=`<div>${(opts.xevery? (i%opts.xevery===0?labels[i]:"") : labels[i])}</div>`;
  });
  return `<div class="bars">${bars}</div><div class="xlabels">${xs}</div>`;
}

function statBlock(label, mwh){
  return `<div class="stat"><div class="k">${label}</div>
    <div class="val">${eur(mwh)} <small>€/MWh</small></div>
    <div class="val" style="font-size:14px">${eur(mwh/1000,4)} <small>€/kWh</small></div></div>`;
}

function renderDay(){
  navlabel.textContent=`${MESI[cur.m]} ${cur.y}`;
  const ndays=daysInMonth(cur.y,cur.m);
  const firstDow=(new Date(cur.y,cur.m,1).getDay()+6)%7; // lun=0
  let cells="";
  for(let i=0;i<firstDow;i++)cells+=`<div class="cell empty"></div>`;
  for(let d=1;d<=ndays;d++){
    const key=fmt(cur.y,cur.m,d);
    if(HISTORY[key]){
      const a=avg(HISTORY[key]);
      cells+=`<div class="cell has" style="background:${heat(a)}" data-key="${key}">
        <div class="d">${d}</div><div><span class="v">${eur(a,1)}</span> <span class="u">€/MWh</span></div></div>`;
    }else{
      cells+=`<div class="cell"><div class="d">${d}</div></div>`;
    }
  }
  let detail=`<div class="hint">Clicca un giorno colorato per vedere il profilo orario.</div>`;
  if(selDate&&HISTORY[selDate]&&parse(selDate).y===cur.y&&parse(selDate).m===cur.m){
    detail=dayDetail(selDate);
  }
  content.innerHTML=`<div class="card">
    <div class="dow">${DOW.map(x=>`<div>${x}</div>`).join("")}</div>
    <div class="grid">${cells}</div></div>
    <div style="height:16px"></div>${detail}`;
  document.querySelectorAll(".cell.has").forEach(c=>c.onclick=()=>{selDate=c.dataset.key;render();});
}

function dayDetail(key){
  const vals=HISTORY[key], a=avg(vals), mn=Math.min(...vals), mx=Math.max(...vals);
  const p=parse(key);
  const labels=vals.map((_,i)=>String(i+1).padStart(2,"0"));
  let rows="";
  vals.forEach((v,i)=>rows+=`<tr><td>${String(i+1).padStart(2,"0")}:00</td><td>${eur(v)}</td><td>${eur(v/1000,4)}</td></tr>`);
  return `<div class="card">
    <h3 style="margin:0 0 4px">Profilo orario — ${p.d} ${MESI[p.m]} ${p.y}</h3>
    <div class="stats">${statBlock("Media giorno",a)}${statBlock("Minimo",mn)}${statBlock("Massimo",mx)}</div>
    ${barChart(vals,labels,{})}
    <table><thead><tr><th>Ora</th><th>€/MWh</th><th>€/kWh</th></tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

function renderMonth(){
  navlabel.textContent=`${MESI[cur.m]} ${cur.y}`;
  const ds=monthDays(cur.y,cur.m).sort();
  if(!ds.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato per ${MESI[cur.m]} ${cur.y}.</div></div>`;return;}
  const dayAvgs=ds.map(k=>avg(HISTORY[k]));
  let all=[];ds.forEach(k=>all=all.concat(HISTORY[k]));
  const mAvg=avg(all), mMin=Math.min(...dayAvgs), mMax=Math.max(...dayAvgs);
  const labels=ds.map(k=>String(parse(k).d));
  content.innerHTML=`<div class="card">
    <h3 style="margin:0 0 4px">Medie giornaliere — ${MESI[cur.m]} ${cur.y}</h3>
    <div class="stats">
      ${statBlock("Media mese",mAvg)}
      ${statBlock("Giorno più basso",mMin)}
      ${statBlock("Giorno più alto",mMax)}
      <div class="stat"><div class="k">Giorni con dati</div><div class="val">${ds.length}</div></div>
    </div>
    ${barChart(dayAvgs,labels,{xevery:2})}
    <div class="hint">Ogni barra = media del giorno. La media mese è sulla media di tutte le ore del mese.</div>
  </div>`;
}

function renderYear(){
  navlabel.textContent=`${cur.y}`;
  const months=yearMonths(cur.y);
  const present=months.map((v,i)=>({v,i})).filter(o=>o.v!=null);
  if(!present.length){content.innerHTML=`<div class="card"><div class="empty-note">Nessun dato per il ${cur.y}.</div></div>`;return;}
  let allv=[];
  monthDays_all(cur.y).forEach(k=>allv=allv.concat(HISTORY[k]));
  const yAvg=avg(allv);
  const vals=present.map(o=>o.v), labels=present.map(o=>MESI[o.i].slice(0,3));
  const mn=Math.min(...vals), mx=Math.max(...vals);
  content.innerHTML=`<div class="card">
    <h3 style="margin:0 0 4px">Medie mensili — ${cur.y}</h3>
    <div class="stats">
      ${statBlock("Media anno",yAvg)}
      ${statBlock("Mese più basso",mn)}
      ${statBlock("Mese più alto",mx)}
    </div>
    ${barChart(vals,labels,{})}
    <div class="hint">Media anno calcolata su tutte le ore disponibili del ${cur.y}.</div>
  </div>`;
}
function monthDays_all(y){return keys.filter(k=>parse(k).y===y);}

// navigazione
function step(dir){
  if(view==="year"){cur.y+=dir;}
  else{cur.m+=dir;if(cur.m<0){cur.m=11;cur.y--;}if(cur.m>11){cur.m=0;cur.y++;}}
  render();
}
document.getElementById("prev").onclick=()=>step(-1);
document.getElementById("next").onclick=()=>step(1);
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{view=t.dataset.view;render();});
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
