#!/usr/bin/env python3
"""Download a reproducible, source-labelled dataset bundle for the India CPI project.

Only public source data are fetched. Failed/protected sources are logged, never filled
with synthetic values. Run from any directory; output is the adjacent package folder.
"""
from __future__ import annotations
import csv, gzip, json, os, re, ssl, sys, threading, time, traceback, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
META = ROOT / "metadata"
NOTES = ROOT / "source_notes"
for p in [RAW / "mospi", RAW / "world_bank", RAW / "imf", RAW / "fred", RAW / "eia", RAW / "oecd", RAW / "imd", RAW / "wpi", META, NOTES]:
    p.mkdir(parents=True, exist_ok=True)
LOG = ROOT / "acquisition.log"
_lock = threading.Lock()


def log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    with _lock:
        print(line, flush=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def session(legacy=False):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; IndiaInflationResearch/1.0; public-data-download)"})
    if legacy:
        class LegacyAdapter(HTTPAdapter):
            def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
                ctx = ssl.create_default_context()
                ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
                kwargs["ssl_context"] = ctx
                self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, **kwargs)
        s.mount("https://api.mospi.gov.in", LegacyAdapter())
    return s


def get_bytes(url, timeout=180, params=None, legacy=False):
    last = None
    for n in range(5):
        try:
            r = session(legacy=legacy).get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.content, r.url, r.headers.get("content-type", "")
        except Exception as e:
            last = e
            time.sleep(min(2 ** n, 16))
    raise last


def save_download(url, dest, timeout=180, params=None, legacy=False):
    try:
        data, final_url, ctype = get_bytes(url, timeout=timeout, params=params, legacy=legacy)
        if len(data) < 50:
            raise RuntimeError(f"too-short response ({len(data)} bytes), content-type={ctype}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        log(f"DOWNLOADED {dest.relative_to(ROOT)} bytes={len(data)} type={ctype} url={final_url}")
        return {"status": "downloaded", "path": str(dest.relative_to(ROOT)), "bytes": len(data), "url": final_url, "content_type": ctype}
    except Exception as e:
        log(f"FAILED {url}: {type(e).__name__}: {e}")
        return {"status": "failed", "url": url, "error": str(e)}


# ---------------------------- MoSPI CPI API ----------------------------
_tls = threading.local()
def mospi_session():
    if not hasattr(_tls, "session"):
        _tls.session = session(legacy=True)
    return _tls.session


def mospi_page(spec, page, limit=100):
    base = "https://api.mospi.gov.in/api/cpi/getCPIData"
    params = dict(spec)
    params.update({"page": page, "limit": limit})
    last = None
    for attempt in range(5):
        try:
            r = mospi_session().get(base, params=params, timeout=90)
            r.raise_for_status()
            j = r.json()
            if "error" in j:
                raise RuntimeError(j["error"])
            return j
        except Exception as e:
            last = e
            time.sleep(min(2 ** attempt, 16))
    raise last


def write_rows(path, rows):
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return 0
    # API schemas vary by base year; preserve every source field in each file.
    keys = sorted({k for row in rows for k in row})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    return len(rows)


def fetch_mospi_batch(name, specs, out_path, workers=5):
    """Fetch page 1 for many filters, then all remaining pages concurrently."""
    out_path = RAW / "mospi" / out_path
    log(f"MoSPI {name}: probing {len(specs)} filters")
    jobs = []
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(mospi_page, spec, 1): spec for spec in specs}
        for fut in as_completed(futures):
            spec = futures[fut]
            try:
                j = fut.result()
                data = j.get("data", []) or []
                meta = j.get("meta_data", {}) or {}
                rows.extend(data)
                total_pages = int(meta.get("totalPages", 1))
                for page in range(2, total_pages + 1):
                    jobs.append((spec, page))
            except Exception as e:
                log(f"MoSPI first-page failure {name} {spec}: {e}")
    log(f"MoSPI {name}: queued {len(jobs)} additional pages")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(mospi_page, spec, page): (spec, page) for spec, page in jobs}
        for fut in as_completed(futures):
            spec, page = futures[fut]
            try:
                j = fut.result()
                rows.extend(j.get("data", []) or [])
            except Exception as e:
                log(f"MoSPI page failure {name} page={page} filters={spec}: {e}")
            done += 1
            if done % 100 == 0 or done == len(futures):
                log(f"MoSPI {name}: pages {done}/{len(futures)}; observations accumulated={len(rows)}")
    count = write_rows(out_path, rows)
    log(f"MoSPI {name}: wrote {count} rows to {out_path.relative_to(ROOT)}")
    return {"name": name, "path": str(out_path.relative_to(ROOT)), "rows": count, "filter_count": len(specs), "page_count": len(jobs)+len(specs)}


def collect_mospi():
    results = []
    # 2012-base all-India group/subgroup observations. State code 99 = All India;
    # API returns all available years/sectors in this filtered slice.
    results.append(fetch_mospi_batch("2012-base all-India group history", [
        {"base_year": 2012, "level": "Group", "state_code": 99}
    ], "cpi_2012_all_india_group_history.csv"))
    # 2012-base item series: source's item endpoint is already the all-India item panel.
    results.append(fetch_mospi_batch("2012-base item history", [
        {"base_year": 2012, "level": "Item"}
    ], "cpi_2012_item_history.csv"))
    # MoSPI 2024-base current detailed releases. Numeric codes: All India=1;
    # Rural=1, Urban=2, Combined=3. Query all months; months with no published data return no rows.
    current_specs = []
    for year in (2025, 2026):
        for month in range(1, 13):
            for sector in (1, 2, 3):
                current_specs.append({"base_year": 2024, "series": "Current", "level": "Group",
                                      "state_code": 1, "sector_code": sector, "year": year, "month_code": month})
    results.append(fetch_mospi_batch("2024-base current detailed all-India (all sectors)", current_specs,
                                     "cpi_2024_current_all_india_detailed.csv"))
    # MoSPI-provided back series, kept in a separate file from the 2012-base CPI.
    results.append(fetch_mospi_batch("2024-base back series", [
        {"base_year": 2024, "series": "Back", "level": "Group"}
    ], "cpi_2024_back_series.csv"))
    return results


# -------------------------- World Bank WDI ---------------------------
WDI = {
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "FP.CPI.TOTL": "Consumer price index (2010=100)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.PCAP.KD.ZG": "GDP per capita growth (annual %)",
    "NY.GDP.DEFL.KD.ZG": "Inflation, GDP deflator (annual %)",
    "PA.NUS.FCRF": "Official exchange rate (LCU per US$, period average)",
    "PA.NUS.PPPC.RF": "PPP conversion factor (GDP, LCU per international $)",
    "FR.INR.RINR": "Real interest rate (%)",
    "FR.INR.LEND": "Lending interest rate (%)",
    "FR.INR.DPST": "Deposit interest rate (%)",
    "FS.AST.PRVT.GD.ZS": "Domestic credit to private sector (% of GDP)",
    "FM.LBL.BMNY.GD.ZS": "Broad money (% of GDP)",
    "NE.CON.PRVT.ZS": "Household consumption (% of GDP)",
    "NE.CON.GOVT.ZS": "Government consumption (% of GDP)",
    "NE.GDI.TOTL.ZS": "Gross capital formation (% of GDP)",
    "NE.EXP.GNFS.ZS": "Exports of goods and services (% of GDP)",
    "NE.IMP.GNFS.ZS": "Imports of goods and services (% of GDP)",
    "BN.CAB.XOKA.GD.ZS": "Current account balance (% of GDP)",
    "FI.RES.TOTL.CD": "Total reserves incl. gold (current US$)",
    "SP.POP.TOTL": "Population, total",
    "SP.POP.GROW": "Population growth (annual %)",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "NV.AGR.TOTL.ZS": "Agriculture, forestry, fishing value added (% GDP)",
    "NV.IND.TOTL.ZS": "Industry value added (% GDP)",
    "NV.SRV.TOTL.ZS": "Services value added (% GDP)",
    "NV.IND.MANF.KD.ZG": "Manufacturing value added growth (annual %)",
    "NV.AGR.TOTL.KD.ZG": "Agriculture value added growth (annual %)",
    "AG.PRD.FOOD.XD": "Food production index (2014-2016=100)",
    "AG.PRD.CROP.XD": "Crop production index (2014-2016=100)",
    "AG.LND.AGRI.ZS": "Agricultural land (% of land area)",
    "AG.LND.CROP.ZS": "Arable land (% of land area)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, modeled ILO estimate)",
    "SL.TLF.CACT.ZS": "Labor force participation rate (% ages 15+)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt (% of GDP)",
    "GC.TAX.TOTL.GD.ZS": "Tax revenue (% of GDP)",
}


def collect_wdi():
    out = RAW / "world_bank" / "wdi_selected_all_countries_long.csv.gz"
    fields = ["country_iso3", "country_id", "country_name", "year", "indicator_code", "indicator_name", "value", "unit", "source_note", "source_organization"]
    tmp_rows = []
    ok = 0
    def one(code, name):
        url = f"https://api.worldbank.org/v2/country/all/indicator/{code}"
        params = {"date": "1960:2025", "format": "json", "per_page": 20000}
        r = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=120)
        r.raise_for_status(); js = r.json()
        if not isinstance(js, list) or len(js) < 2 or not isinstance(js[1], list):
            raise RuntimeError(str(js)[:300])
        meta, data = js[0], js[1]
        return code, name, meta, data
    log(f"World Bank WDI: fetching {len(WDI)} all-country indicators, 1960-2025")
    with ThreadPoolExecutor(max_workers=6) as pool:
        fs = {pool.submit(one, c, n): (c,n) for c,n in WDI.items()}
        for fut in as_completed(fs):
            code, name = fs[fut]
            try:
                c,n,meta,data = fut.result(); ok += 1
                for x in data:
                    country = x.get("country") or {}
                    ind = x.get("indicator") or {}
                    tmp_rows.append([x.get("countryiso3code"), (x.get("country") or {}).get("id"), country.get("value"), x.get("date"), code, ind.get("value") or name, x.get("value"), x.get("unit"), x.get("obs_status"), x.get("decimal")])
                log(f"WDI {code}: {len(data)} observations; valid indicators={ok}")
            except Exception as e:
                log(f"WDI FAILED {code}: {e}")
    # correct headers include the metadata fields returned above
    fields = ["country_iso3", "country_id", "country_name", "year", "indicator_code", "indicator_name", "value", "unit", "observation_status", "decimal"]
    with gzip.open(out, "wt", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(fields); w.writerows(tmp_rows)
    log(f"WDI wrote {len(tmp_rows)} observation rows to {out.relative_to(ROOT)}")
    return {"path": str(out.relative_to(ROOT)), "rows": len(tmp_rows), "indicators_requested": len(WDI), "indicators_ok": ok}


# --------------------------- External files --------------------------
def collect_external():
    results=[]
    # World Bank Pink Sheet monthly global benchmark commodity prices.
    results.append(save_download("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx", RAW/"world_bank"/"pink_sheet_monthly_commodity_prices.xlsx", timeout=300))
    # IMF WEO full all-country data workbook, April 2026 vintage.
    results.append(save_download("https://data.imf.org/-/media/iData/External-Storage/Documents/2F78EE59F79143A7921E5E203D3AAA80/en/WEOApr2026all.xlsx", RAW/"imf"/"WEOApr2026all.xlsx", timeout=300))
    # OEA official WPI monthly series, 2011-12 base. Also save annual summaries.
    for url, name in [
        ("https://eaindustry.nic.in/indx_download_1112/monthly_index_202606.xls", "wpi_2011_12_monthly_from_2012.xls"),
        ("https://eaindustry.nic.in/indx_download_1112/cal_year_index.xls", "wpi_2011_12_calendar_year_averages.xls"),
        ("https://eaindustry.nic.in/indx_download_1112/fin_year_index.xls", "wpi_2011_12_financial_year_averages.xls"),
    ]:
        results.append(save_download(url, RAW/"wpi"/name, timeout=180))
    # EIA official key-free daily crude oil workbook downloads.
    for sid, label in [("RBRTEd", "brent"), ("RWTCd", "wti")]:
        url = f"https://www.eia.gov/dnav/pet/hist_xls/{sid}.xls"
        results.append(save_download(url, RAW/"eia"/f"{label}_daily_official.xls", timeout=180))
    # IMF/World Bank raw source notes and HBs are in source_notes; do not scrape RBI CAPTCHA.
    # FRED monthly and daily control variables plus India/OECD alternatives.
    fred_ids = ["CPIAUCSL","CPILFESL","FEDFUNDS","DFF","UNRATE","DGS10","DGS2","DEXINUS",
                "DCOILWTICO","DCOILBRENTEU","DTWEXBGS","M2SL","INDPROINDMISMEI","INDCPALTT01IXNBM",
                "IR3TIB01INM156N","IRLTLT01INM156N"]
    def fred_one(sid):
        u=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        dest=RAW/"fred"/f"{sid}.csv"
        res=save_download(u,dest,timeout=180)
        if res["status"]=="downloaded":
            txt=dest.read_text(errors="ignore")[:1000]
            if "<!DOCTYPE" in txt or "series_id" in txt.lower() and len(txt)<400:
                dest.unlink(missing_ok=True); raise RuntimeError("FRED returned an HTML/error page")
        return sid,res
    with ThreadPoolExecutor(max_workers=6) as pool:
        fs={pool.submit(fred_one,sid):sid for sid in fred_ids}
        for fut in as_completed(fs):
            sid=fs[fut]
            try:
                s,r=fut.result(); results.append({"source":"FRED","series":s,**r})
            except Exception as e:
                log(f"FRED FAILED {sid}: {e}"); results.append({"source":"FRED","series":sid,"status":"failed","error":str(e)})
    # OECD India CPI monthly (YoY and index). FRED mirrors are also collected above.
    oecd_urls = {
        "india_monthly_cpi_yoy.csv": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/IND.M.N.CPI.PA._T.N.GY?startPeriod=1990-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels",
        "india_monthly_cpi_index.csv": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/IND.M.N.CPI.IX._T.N._Z?startPeriod=1990-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels",
    }
    for name,url in oecd_urls.items():
        results.append(save_download(url,RAW/"oecd"/name,timeout=240))
    # WDI alternatives are fetched separately by collect_wdi().
    return results


# ----------------------- IMD regional rainfall -----------------------
def collect_imd_rainfall():
    from bs4 import BeautifulSoup
    from io import StringIO
    import pandas as pd
    regions = [("WHI","Whole India"),("NEI","North-East India"),("NWI","North-West India"),("PNI","Peninsular India"),("CNI","Central India")]
    frames=[]
    s=requests.Session(); s.headers["User-Agent"]="Mozilla/5.0"
    for code,name in regions:
        url="https://dsp.imdpune.gov.in/home_ogd_rainfall.php"
        try:
            r=s.post(url,data={"region1":code},timeout=90); r.raise_for_status()
            tables=pd.read_html(StringIO(r.text))
            # Table 2 is the annual all-month and seasonal-rainfall table (1901-2024).
            df=tables[2].copy()
            df.columns=[str(x).strip() for x in df.iloc[0].tolist()]
            df=df.iloc[1:].reset_index(drop=True)
            df["region_code"]=code; df["region_name"]=name
            frames.append(df)
            (RAW/"imd"/f"imd_ogd_rainfall_{code}.html").write_text(r.text,encoding="utf-8")
            log(f"IMD rainfall {code}: rows={len(df)} columns={len(df.columns)}")
        except Exception as e:
            log(f"IMD rainfall FAILED {code}: {e}")
    if frames:
        out=pd.concat(frames,ignore_index=True)
        out.to_csv(RAW/"imd"/"imd_regional_monthly_seasonal_rainfall_1901_2024.csv",index=False,encoding="utf-8-sig")
        log(f"IMD rainfall wrote {len(out)} rows")
        return {"path":"raw/imd/imd_regional_monthly_seasonal_rainfall_1901_2024.csv","rows":len(out)}
    return {"status":"failed","rows":0}


def main():
    LOG.write_text("",encoding="utf-8")
    log("Starting official/public data acquisition; request window 1960-2026 where available")
    manifest={"created_utc":datetime.now(timezone.utc).isoformat(),"script":"download_bundle.py","datasets":[]}
    # MoSPI requests are individually paginated; use numeric MoSPI filter codes.
    try:
        manifest["datasets"].extend(collect_mospi())
    except Exception as e:
        log(f"MoSPI collection fatal: {traceback.format_exc()}")
    try:
        manifest["datasets"].append({"source":"World Bank WDI",**collect_wdi()})
    except Exception:
        log(f"WDI fatal: {traceback.format_exc()}")
    try:
        manifest["datasets"].extend(collect_external())
    except Exception:
        log(f"External downloads fatal: {traceback.format_exc()}")
    try:
        manifest["datasets"].append({"source":"IMD OGD regional rainfall",**collect_imd_rainfall()})
    except Exception:
        log(f"IMD rainfall fatal: {traceback.format_exc()}")
    manifest["completed_utc"]=datetime.now(timezone.utc).isoformat()
    manifest["log_path"]="acquisition.log"
    (META/"download_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    log("Finished data acquisition run")

if __name__=="__main__":
    main()
