#!/usr/bin/env python3
"""
LMS — Mercati Energetici: PUN (elettricità) + Gas PSV dal portale pubblico GME
==============================================================================

Scarica dal sito pubblico mercatoelettrico.org, senza credenziali:
  * PUN orario ufficiale (MGP elettrico)         -> endpoint item/GetMEPrezzi
  * Prezzo gas PSV ufficiale (MGP-GAS, riferim.) -> endpoint item/GetGasEsitiMGAS

Accumula due storici in CSV e genera un'app/pagina HTML brandizzata "Mercati
Energetici" (calendario navigabile, viste Giorno/Mese/Anno per elettricità e
gas) da pubblicare su GitHub Pages e aggiornare ogni giorno via GitHub Actions.

Token e parametri di modulo sono dati di sessione temporanei estratti al volo
dalla pagina pubblica: NON sono credenziali personali.

USO
    python pun_gme.py                       # oggi: PUN + gas, aggiorna CSV e pagina
    python pun_gme.py --backfill 2026-04-01 2026-06-23
    python pun_gme.py --rebuild-viewer

File: pun_gme.json, pun_storico.csv, gas_storico.csv, index.html (o --viewer)

Dati soggetti alle Condizioni di utilizzo / Disclaimer di GME (artt. 7,8,10,13).
Requisiti: pip install requests   (matplotlib solo per --chart)
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
    sys.exit("Manca 'requests'. Installa con: pip install requests")

BASE = "https://www.mercatoelettrico.org"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 30

# --- Elettricità (PUN, MGP) ---
EL_PAGE = BASE + "/it-it/Home/Esiti/Elettricita/MGP/Esiti/PUN"
EL_SERVICE = BASE + "/DesktopModules/GmeEsitiPrezziME/API/item/GetMEPrezzi"

# --- Gas (PSV, MGP-GAS) ---
GAS_PAGE = BASE + "/it-it/Home/Esiti/Gas/MGP-GAS/Esiti/NegoziazioneContinua"
GAS_SERVICE = BASE + "/DesktopModules/GmeEsitiMGAS/API/item/GetGasEsitiMGAS"

# --- Forward / Futures (prezzi di controllo = settlement) ---
# Power: MTE (Mercato a Termine Energia). Gas: MT-GAS (Mercato a Termine Gas).
MTE_PAGE = BASE + "/it-it/Home/Esiti/Elettricita/MTE/Esiti/Prezzi"
MTE_SERVICE = BASE + "/DesktopModules/GmeEsitiMTE/API/GmeEsitiMTE/GetMEESitiMTE"
MTGAS_PAGE = BASE + "/it-it/Home/Esiti/Gas/MT-GAS/Esiti/MT-GAS"
MTGAS_SERVICE = BASE + "/DesktopModules/GmeEsitiMGAS/API/item/GetGasEsitiMGAS"

DATE_FMT = "%Y%m%d"
DEFAULT_CSV = "pun_storico.csv"
GAS_CSV = "gas_storico.csv"
FORWARD_JSON = "forward.json"
DEFAULT_VIEWER = "index.html"

log = logging.getLogger("pun_gme")


# --------------------------------------------------------------------------- #
# Estrazione token/parametri
# --------------------------------------------------------------------------- #
def _first(*patterns, text):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    return None


def _open(page_url):
    """Apre una pagina pubblica e prepara (session, headers con token+modulo)."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, */*"})
    html = s.get(page_url, timeout=TIMEOUT).text
    token = _first(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"',
                   r'value="([^"]+)"[^>]*name="__RequestVerificationToken"', text=html)
    if not token:
        raise RuntimeError("Token antiforgery non trovato (markup GME cambiato?).")
    module_id = _first(r'"ModuleId"\s*:\s*"?(\d+)', r'DnnModule-(\d+)"', text=html)
    tab_id = _first(r'"TabId"\s*:\s*"?(\d+)', text=html)
    h = {"RequestVerificationToken": token, "X-Requested-With": "XMLHttpRequest",
         "Referer": page_url}
    if module_id:
        h["ModuleId"] = module_id
    if tab_id:
        h["TabId"] = tab_id
    return s, h


# --------------------------------------------------------------------------- #
# Elettricità
# --------------------------------------------------------------------------- #
def open_el():
    return _open(EL_PAGE)


def get_el_day(session, headers, date):
    ds = date.strftime(DATE_FMT)
    q = {"DataInizio": ds, "DataFine": ds, "Granularita": "h",
         "Mercato": "MGP", "Zona": "PUN", "Tipologia": "PUN"}
    r = session.get(EL_SERVICE, headers=headers, params=q, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for row in (data if isinstance(data, list) else []):
        if not isinstance(row, dict):
            continue
        ora, pun = row.get("h"), row.get("p")
        if pun is None:
            continue
        try:
            out.append((int(float(ora)), float(pun)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda t: t[0])
    return out


def fetch_el(date):
    s, h = open_el()
    recs = get_el_day(s, h, date)
    if not recs:
        raise RuntimeError(f"PUN non disponibile per {date:%Y-%m-%d} (riprova dopo le ~14:00).")
    return date.strftime("%Y-%m-%d"), recs


# --------------------------------------------------------------------------- #
# Gas PSV (MGP-GAS) — un prezzo di riferimento per gas-day (data di consegna)
# --------------------------------------------------------------------------- #
def open_gas():
    return _open(GAS_PAGE)


def get_gas_session(session, headers, session_date):
    """Per una data di sessione, ritorna {data_consegna 'YYYY-MM-DD': prezzo_rif €/MWh}."""
    ds = session_date.strftime(DATE_FMT)
    r = session.get(GAS_SERVICE, headers=headers,
                    params={"DataSessione": ds, "Mercato": "MGP"}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = {}
    for row in (data if isinstance(data, list) else []):
        if not isinstance(row, dict):
            continue
        pr = row.get("prezzoRiferimento")
        prod = row.get("prodotto", "")
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(prod))
        if pr is None or not m:
            continue
        try:
            out[f"{m.group(1)}-{m.group(2)}-{m.group(3)}"] = round(float(pr), 4)
        except (TypeError, ValueError):
            continue
    return out


# --------------------------------------------------------------------------- #
# Storici CSV
# --------------------------------------------------------------------------- #
def load_el(csv_path):
    hist = {}
    if not os.path.exists(csv_path):
        return hist
    tmp = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                tmp.setdefault(row["data"], {})[int(row["ora"])] = float(row["pun_eur_mwh"])
            except (KeyError, ValueError):
                continue
    for d, ore in tmp.items():
        hist[d] = [ore[h] for h in sorted(ore)]
    return dict(sorted(hist.items()))


def save_el(csv_path, hist):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "ora", "pun_eur_mwh"])
        for d in sorted(hist):
            for i, p in enumerate(hist[d], start=1):
                w.writerow([d, i, f"{p:.2f}"])


def load_gas(csv_path):
    hist = {}
    if not os.path.exists(csv_path):
        return hist
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                hist[row["data"]] = float(row["prezzo_eur_mwh"])
            except (KeyError, ValueError):
                continue
    return dict(sorted(hist.items()))


def save_gas(csv_path, hist):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "prezzo_eur_mwh"])
        for d in sorted(hist):
            w.writerow([d, f"{hist[d]:.4f}"])


# --------------------------------------------------------------------------- #
# Output JSON + grafico (elettricità)
# --------------------------------------------------------------------------- #
def build_output(date_label, recs, gas_today=None):
    mwh = [round(p, 2) for _, p in recs]
    avg = sum(p for _, p in recs) / len(recs) if recs else None
    o = {
        "data": date_label,
        "fonte": "GME mercatoelettrico.org — MGP (PUN ufficiale) + MGP-GAS (PSV)",
        "aggiornato_il": datetime.now().astimezone().isoformat(),
        "pun_ore": len(mwh),
        "pun_orari_eur_mwh": mwh,
        "pun_orari_eur_kwh": [round(p / 1000.0, 5) for _, p in recs],
        "pun_media_eur_mwh": round(avg, 2) if avg is not None else None,
        "pun_media_eur_kwh": round(avg / 1000.0, 5) if avg is not None else None,
    }
    if gas_today:
        d, p = gas_today
        o["gas_psv_data"] = d
        o["gas_psv_eur_mwh"] = round(p, 2)
    return o


def make_chart(recs, date_label, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    hours = [o for o, _ in recs]
    vals = [v for _, v in recs]
    avg = sum(vals) / len(vals) if vals else 0
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(hours, vals, color="#16a34a", alpha=0.85, width=0.8)
    ax.axhline(avg, color="#dc2626", ls="--", lw=1, label=f"media {avg:.2f} €/MWh")
    ax.set_title(f"PUN — {date_label}")
    ax.set_xlabel("Ora"); ax.set_ylabel("€/MWh"); ax.set_xticks(hours)
    ax.grid(axis="y", alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(path, dpi=130); import matplotlib.pyplot as p2; p2.close(fig)


# --------------------------------------------------------------------------- #
# Forward / Futures (curva da prezzi di controllo GME = settlement)
# --------------------------------------------------------------------------- #
def _latest_session(page, service, params_fn, ref):
    """Trova l'ultima sessione (entro 8 giorni) che restituisce dati. -> (date, list)."""
    s, h = _open(page)
    for i in range(8):
        d = ref - timedelta(days=i)
        try:
            r = s.get(service, headers=h, params=params_fn(d), timeout=TIMEOUT)
            data = r.json()
        except Exception:  # noqa: BLE001
            data = []
        if isinstance(data, list) and data:
            return d, data
    return None, []


def _parse_power_fwd(data):
    base = {"months": {}, "quarters": {}, "years": {}}
    peak = {"months": {}, "quarters": {}, "years": {}}
    for r in data:
        p = r.get("Prodotto", "")
        pc = r.get("PrezzoControllo")
        if pc in (None, ""):
            continue
        pc = round(float(pc), 2)
        for pref, store in (("BL", base), ("PL", peak)):
            m = re.match(rf"{pref}-M-(\d{{4}})-(\d{{2}})$", p)
            if m:
                store["months"][f"{m.group(1)}-{m.group(2)}"] = pc; break
            m = re.match(rf"{pref}-Q-(\d{{4}})-(\d{{2}})$", p)
            if m:
                store["quarters"][f"{m.group(1)}-Q{int(m.group(2))}"] = pc; break
            m = re.match(rf"{pref}-Y-(\d{{4}})$", p)
            if m:
                store["years"][m.group(1)] = pc; break
    return {**base, "peak": peak}


def _parse_gas_fwd(data):
    months, quarters, years, seasons = {}, {}, {}, {}
    for r in data:
        p = r.get("prodotto", "")
        pc = r.get("prezzoControllo")
        if pc in (None, ""):
            continue
        pc = round(float(pc), 3)
        m = re.match(r"M-(\d{4})-(\d{2})$", p)
        if m:
            months[f"{m.group(1)}-{m.group(2)}"] = pc; continue
        m = re.match(r"Q-(\d{4})-(\d{2})$", p)
        if m:
            quarters[f"{m.group(1)}-Q{int(m.group(2))}"] = pc; continue
        m = re.match(r"CY-(\d{4})$", p)
        if m:
            years[m.group(1)] = pc; continue
        if p.startswith(("SS-", "WS-")):
            seasons[p] = pc
    return {"months": months, "quarters": quarters, "years": years, "seasons": seasons}


def fetch_forward(ref):
    """Curva forward power (MTE) e gas (MT-GAS) dall'ultima sessione disponibile."""
    out = {"aggiornato_il": datetime.now().astimezone().isoformat()}
    try:
        d, data = _latest_session(MTE_PAGE, MTE_SERVICE, lambda x: {"data": x.strftime(DATE_FMT)}, ref)
        if data:
            out["power"] = {"as_of": d.strftime("%Y-%m-%d"), **_parse_power_fwd(data)}
            log.info("Forward power: %d prodotti (sessione %s)", len(data), d.strftime("%Y-%m-%d"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Forward power non disponibile: %s", exc)
    try:
        d, data = _latest_session(MTGAS_PAGE, MTGAS_SERVICE,
                                  lambda x: {"DataSessione": x.strftime(DATE_FMT), "Mercato": "MT"}, ref)
        if data:
            out["gas"] = {"as_of": d.strftime("%Y-%m-%d"), **_parse_gas_fwd(data)}
            log.info("Forward gas: %d prodotti (sessione %s)", len(data), d.strftime("%Y-%m-%d"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Forward gas non disponibile: %s", exc)
    return out


def load_forward(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}
    return {}


# --------------------------------------------------------------------------- #
# Generazione pagina
# --------------------------------------------------------------------------- #
def write_viewer(html_path, el_hist, gas_hist, fwd=None):
    gen = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    html = (VIEWER_TEMPLATE
            .replace("/*__ELEC__*/", json.dumps(el_hist, separators=(",", ":")))
            .replace("/*__GAS__*/", json.dumps(gas_hist, separators=(",", ":")))
            .replace("/*__FWD__*/", json.dumps(fwd or {}, separators=(",", ":")))
            .replace("__GEN__", gen))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Pagina aggiornata: %s (PUN %d gg, Gas %d gg, forward %s)",
             html_path, len(el_hist), len(gas_hist), "sì" if fwd else "no")


# --------------------------------------------------------------------------- #
# Backfill
# --------------------------------------------------------------------------- #
def backfill(el_csv, gas_csv, start, end, delay=0.12):
    el = load_el(el_csv)
    gas = load_gas(gas_csv)
    se, he = open_el()
    sg, hg = open_gas()
    d = start
    add_e = add_g = 0
    while d <= end:
        label = d.strftime("%Y-%m-%d")
        if label not in el or len(el.get(label, [])) < 23:
            try:
                recs = get_el_day(se, he, d)
                if recs:
                    el[label] = [p for _, p in recs]; add_e += 1
            except Exception as exc:  # noqa: BLE001
                log.debug("PUN %s: %s", label, exc)
                try:
                    se, he = open_el()
                except Exception:
                    pass
        try:
            g = get_gas_session(sg, hg, d)
            for dd, pr in g.items():
                if dd not in gas:
                    add_g += 1
                gas[dd] = pr
        except Exception as exc:  # noqa: BLE001
            log.debug("Gas %s: %s", label, exc)
            try:
                sg, hg = open_gas()
            except Exception:
                pass
        time.sleep(delay)
        d += timedelta(days=1)
    save_el(el_csv, el)
    save_gas(gas_csv, gas)
    log.info("Backfill: PUN +%d gg, Gas +%d gg.", add_e, add_g)
    return el, gas


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def resolve_date(a):
    today = datetime.now()
    m = {"today": today, "tomorrow": today + timedelta(days=1),
         "yesterday": today - timedelta(days=1)}
    if a in m:
        return m[a]
    try:
        return datetime.strptime(a, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Data non valida: {a!r}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mercati Energetici GME: PUN + Gas PSV.")
    ap.add_argument("--date", default="today")
    ap.add_argument("--out", default="pun_gme.json")
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--gas-csv", default=GAS_CSV)
    ap.add_argument("--viewer", default=DEFAULT_VIEWER)
    ap.add_argument("--chart", nargs="?", const="pun_gme_profilo.png", default=None)
    ap.add_argument("--backfill", nargs=2, metavar=("START", "END"))
    ap.add_argument("--rebuild-viewer", action="store_true")
    ap.add_argument("--no-viewer", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.rebuild_viewer:
        write_viewer(args.viewer, load_el(args.csv), load_gas(args.gas_csv), load_forward(FORWARD_JSON))
        return 0

    if args.backfill:
        start = datetime.strptime(args.backfill[0], "%Y-%m-%d")
        end = datetime.strptime(args.backfill[1], "%Y-%m-%d")
        el, gas = backfill(args.csv, args.gas_csv, start, end)
        if not args.no_viewer:
            write_viewer(args.viewer, el, gas, load_forward(FORWARD_JSON))
        return 0

    date = resolve_date(args.date)

    # Elettricità (obbligatoria)
    date_label, recs = fetch_el(date)
    el = load_el(args.csv)
    el[date_label] = [p for _, p in recs]
    save_el(args.csv, el)

    # Gas (best-effort: non blocca se non disponibile)
    gas = load_gas(args.gas_csv)
    gas_today = None
    try:
        sg, hg = open_gas()
        g = get_gas_session(sg, hg, date)
        for dd, pr in g.items():
            gas[dd] = pr
        if g:
            last = sorted(g)[-1]
            gas_today = (last, g[last])
        save_gas(args.gas_csv, gas)
    except Exception as exc:  # noqa: BLE001
        log.warning("Gas non aggiornato: %s", exc)

    # Forward / Futures (best-effort: non blocca la pagina se non disponibile)
    fwd = load_forward(FORWARD_JSON)
    try:
        fnew = fetch_forward(date)
        if fnew.get("power") or fnew.get("gas"):
            fwd = fnew
            with open(FORWARD_JSON, "w", encoding="utf-8") as f:
                json.dump(fwd, f, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        log.warning("Forward non aggiornato: %s", exc)

    output = build_output(date_label, recs, gas_today)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    if args.chart:
        make_chart(recs, date_label, args.chart)
    if not args.no_viewer:
        write_viewer(args.viewer, el, gas, fwd)

    log.info("OK %s — PUN media %s €/MWh — Gas %s — storico PUN %d gg, Gas %d gg.",
             date_label, output.get("pun_media_eur_mwh"),
             output.get("gas_psv_eur_mwh"), len(el), len(gas))
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


# Il template della pagina è in un file separato per leggibilità.
from viewer_template import VIEWER_TEMPLATE  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
