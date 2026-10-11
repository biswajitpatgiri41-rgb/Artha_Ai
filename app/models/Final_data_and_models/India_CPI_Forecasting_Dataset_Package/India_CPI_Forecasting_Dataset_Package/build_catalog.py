#!/usr/bin/env python3
"""Build dataset catalog, file inventory/checksums, and package README.

Run after source downloads finish. This script reports only real retrieved files and
explicitly labels proxies, partial snapshots, and datasets that were not retrieved.
"""
from __future__ import annotations
import csv, gzip, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'raw'
META=ROOT/'metadata'
META.mkdir(parents=True,exist_ok=True)

def existing(patterns):
    found=[]
    for pat in patterns:
        found.extend(sorted(RAW.glob(pat)))
    return sorted({p for p in found if p.is_file()})

def rel(files): return '; '.join(str(p.relative_to(ROOT)) for p in files) or '—'

def csv_row_count(path):
    name=path.name.lower()
    if not any(name.endswith(suffix) for suffix in ('.csv','.tsv','.csv.gz','.tsv.gz')):
        return None
    try:
        op=gzip.open if name.endswith('.gz') else open
        with op(path,'rt',newline='',encoding='utf-8-sig',errors='replace') as f:
            return max(0,sum(1 for _ in csv.reader(f))-1)
    except Exception: return None

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

# Logical requirements and their source files. A proxy is never labelled as the preferred series.
items=[
 ('CPI Combined General Group / inflation target','Core target','MoSPI / NSO',
  ['mospi/cpi_2012_all_india_group_history.csv','mospi/cpi_2012_item_history.csv','mospi/cpi_2024_back_series.csv','mospi/cpi_2024_current_all_india_detailed.csv'],
  'Downloaded — official files; base-year vintages are kept separate.',
  'Monthly index/group observations; derive YoY from the index and preserve base year, source release date, and vintage. Do not splice 2012 and 2024 bases casually.'),
 ('Food, fuel, and core CPI groups','Priority / feature group','MoSPI / NSO',
  ['mospi/cpi_2012_all_india_group_history.csv','mospi/cpi_2012_item_history.csv','mospi/cpi_2024_current_all_india_detailed.csv'],
  'Downloaded — group/item source observations; analytical group mapping still required.',
  'These are categories within CPI files, not separate fabricated series. Verify classification and definition before deriving food/core/fuel inflation.'),
 ('IIP general index','Core activity feature','MoSPI / NSO preferred; OECD via FRED alternative',
  ['fred/INDPROINDMISMEI.csv'],
  'Proxy downloaded — OECD/FRED India industrial production series only; official MoSPI release vintages not retrieved.',
  'Validate base, seasonal adjustment, and observation end date. Not a substitute for current official first-release IIP.'),
 ('RBI policy repo rate','Core policy feature','RBI / DBIE preferred; OECD via FRED alternative',
  ['fred/IRSTCB01INM156N_india_central_bank_rate.csv','rbi/dbie_landing_snapshot.csv'],
  'Partial — long historical central-bank-rate proxy plus a separate RBI current-indicator snapshot.',
  'OECD/FRED series through Dec-2023 is not guaranteed to equal the RBI repo rate. Snapshot effective date is not specified. Exact event-dated RBI repo history remains a gap.'),
 ('Brent crude oil','Core external feature','EIA; FRED / World Bank cross-checks',
  ['eia/brent_daily_official.xls','fred/DCOILBRENTEU.csv','world_bank/pink_sheet_monthly_commodity_prices.xlsx'],
  'Downloaded — EIA daily workbook, FRED daily mirror, and World Bank monthly commodity panel.',
  'Keep daily and monthly frequencies distinct; use a documented monthly aggregation. WTI is a separate comparator, not Brent.'),
 ('INR/USD exchange rate','Core external feature','RBI preferred; FRED and World Bank alternatives',
  ['fred/DEXINUS.csv','world_bank/wdi_selected_all_countries_long.csv.gz'],
  'Proxy downloaded — daily FRED exchange-rate series and annual WDI official-rate observations.',
  'RBI reference-rate history was not retrieved. Verify the INR-per-USD quotation, source definition, and aggregation; daily and annual series are not interchangeable.'),
 ('Wholesale Price Index (WPI)','Optional price feature','Office of the Economic Adviser (OEA)',
  ['wpi/wpi_2011_12_monthly_from_2012.xls','wpi/wpi_2011_12_calendar_year_averages.xls','wpi/wpi_2011_12_financial_year_averages.xls'],
  'Downloaded — official OEA 2011–12-base workbooks.',
  'Keep WPI separate from CPI. Different base series require an official bridge; latest observations can be provisional.'),
 ('GDP / GVA / activity aggregates','Extended macro context','World Bank WDI; IMF WEO',
  ['world_bank/wdi_selected_all_countries_long.csv.gz','imf/WEOApr2026all.xlsx'],
  'Downloaded — annual global panels and WEO vintage.',
  'Annual/quarterly aggregates are low-frequency and released with lags; WEO projected values must remain distinguishable from realized data.'),
 ('Purchasing Managers’ Index (PMI)','Optional if licensed','S&P Global / HSBC licensed; open activity proxies',
  [],
  'Not retrieved — no redistribution-cleared bulk series found.',
  'Use official IIP as an open monthly activity alternative; WDI consumption and payment statistics are imperfect, low-frequency/high-frequency proxies, not PMI.'),
 ('Policy rates / SDF / MSF / CRR / SLR / liquidity','Extended monetary-policy features','RBI / DBIE',
  ['rbi/dbie_landing_snapshot.csv','fred/IRSTCB01INM156N_india_central_bank_rate.csv'],
  'Partial — RBI current snapshot includes repo, reverse repo, SDF, CRR, and SLR; historical event series and MSF are absent.',
  'The FRED/OECD central-bank-rate proxy is not the event-dated RBI policy history. Do not infer dates not printed in the source snapshot.'),
 ('Credit growth and broad money (M3)','Extended financial features','RBI / DBIE preferred; WDI/FRED alternatives',
  ['world_bank/wdi_selected_all_countries_long.csv.gz','fred/M2SL.csv'],
  'Proxy downloaded — WDI annual India credit/broad-money ratios and US M2; RBI monthly India aggregates not retrieved.',
  'Do not substitute US M2 for Indian M3. Frequency and denominator differ; RBI Handbook/DBIE is the preferred monthly/fortnightly source.'),
 ('Bond yields / financial conditions','Extended global feature family','RBI / Indian market sources preferred; FRED alternatives',
  ['fred/DGS10.csv','fred/DGS2.csv','fred/DTWEXBGS.csv','fred/DFF.csv'],
  'Partial proxy — US Treasury yields, dollar index, and effective Federal Funds rate downloaded; Indian bond-yield series not retrieved.',
  'Identify country and tenor explicitly. US rates are external/global context, not Indian sovereign yields or a complete India financial-conditions index.'),
 ('US CPI and Federal Funds rate','Global context','FRED',
  ['fred/CPIAUCSL.csv','fred/CPILFESL.csv','fred/FEDFUNDS.csv','fred/DFF.csv'],
  'Downloaded — US CPI, core CPI, monthly effective and daily Federal Funds series.',
  'External controls only; preserve source frequency and FRED series citation/rights.'),
 ('Global commodity price indices','External supply/cost context','World Bank Pink Sheet; EIA',
  ['world_bank/pink_sheet_monthly_commodity_prices.xlsx','eia/brent_daily_official.xls','eia/wti_daily_official.xls'],
  'Downloaded — monthly multi-commodity workbook plus official daily oil workbooks.',
  'Global USD benchmark prices do not equal Indian retail or landed prices; document transformations and units.'),
 ('Rainfall / weather','Extended supply feature','India Meteorological Department (IMD)',
  ['imd/imd_regional_monthly_seasonal_rainfall_1901_2024.csv','imd/gridded_daily_025deg/RF25_daily_0.25deg_*.nc.gz'],
  'Downloaded — five-region annual/monthly/seasonal summary; daily 0.25-degree files cover only successful CPI-aligned years recorded in the IMD manifest.',
  'Aggregate grid cells to India/crop-region masks before modeling. Long weather history does not extend the CPI target history.'),
 ('IMF monthly CPI dataset','Optional CPI cross-check','IMF Statistics CPI; OECD SDMX alternative',
  [],
  'Not retrieved in this run — the official IMF CPI dataset/API is documented, but no raw IMF monthly CPI extract is in the ZIP; OECD monthly India CPI files are included as the related alternative.',
  'Use the OECD/FRED monthly series only as a cross-check, not as a replacement for MoSPI release vintages. Obtain a dated IMF extract through the current API route if it is required.'),
 ('India monthly CPI alternative / cross-check','Validation alternative','OECD SDMX via public API; FRED mirror',
  ['oecd/india_monthly_cpi_yoy.csv','oecd/india_monthly_cpi_index.csv','fred/INDCPALTT01IXNBM.csv'],
  'Downloaded — OECD monthly India CPI index and YoY, plus an OECD/FRED mirror.',
  'Definitions, vintages, and end dates can differ from MoSPI; retain metadata and use as cross-check/proxy only.'),
 ('Consumption / high-frequency activity proxies','Optional extended features','WDI; NPCI/Dataful route',
  ['world_bank/wdi_selected_all_countries_long.csv.gz'],
  'Partial proxy — annual household/private-consumption ratio in WDI; UPI monthly file not retrieved.',
  'UPI activity is not household consumption. Dataful describes an NPCI mirror (124 rows, FY2016–17 to FY2026–27), but its export was client/account-gated in this run.'),
 ('Global macro panel / country controls','Optional data expansion','World Bank WDI; IMF WEO',
  ['world_bank/wdi_selected_all_countries_long.csv.gz','imf/WEOApr2026all.xlsx'],
  'Downloaded — all-country annual WDI selected-indicator panel plus April-2026 WEO workbook.',
  'WDI is annual; WEO includes estimates/projections. The acquisition manifest gives the exact recovered indicator count and failed/deleted code note.'),
]

# Resolve files by patterns relative to raw.
catalog=[]
for name,priority,source,patterns,status,caveat in items:
    files=existing(patterns)
    if not files and status.startswith('Downloaded'):
        status='Not retrieved — no matching local source file.'
    catalog.append({'dataset_or_family':name,'pdf_priority':priority,'preferred_or_actual_sources':source,
                    'local_files':rel(files),'local_file_count':len(files),'status':status,'use_and_limitations':caveat})

with (META/'DATASET_CATALOG.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(catalog[0]));w.writeheader();w.writerows(catalog)
(META/'dataset_catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False),encoding='utf-8')

# File-level inventory and SHA256 checksums for every retained raw source asset.
files=[]
for p in sorted(RAW.rglob('*')):
    if not p.is_file() or p.name.endswith('.tmp'): continue
    row_count=csv_row_count(p)
    files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha256(p),'tabular_rows_excluding_header':row_count})
with (META/'FILE_INVENTORY.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['path','bytes','sha256','tabular_rows_excluding_header']);w.writeheader();w.writerows(files)

source_manifest={}
mp=META/'download_manifest.json'
if mp.exists(): source_manifest=json.loads(mp.read_text(encoding='utf-8'))
wdi=next((d for d in source_manifest.get('datasets',[]) if d.get('source')=='World Bank WDI'),{})
num_bytes=sum(x['bytes'] for x in files)
num_grid=sum(1 for x in files if x['path'].startswith('raw/imd/gridded_daily_025deg/RF25_daily_'))
summary={'generated_utc':datetime.now(timezone.utc).isoformat(),'raw_file_count':len(files),'raw_total_bytes':num_bytes,
         'raw_total_mib':round(num_bytes/1024**2,2),'daily_grid_year_file_count':num_grid,
         'wdi_rows':wdi.get('rows'),'wdi_indicators_ok':wdi.get('indicators_ok'),'wdi_indicators_requested':wdi.get('indicators_requested'),
         'catalog_entries':len(catalog)}
(META/'PACKAGE_MANIFEST.json').write_text(json.dumps({'summary':summary,'files':files,'datasets':catalog},indent=2,ensure_ascii=False),encoding='utf-8')

readme=f'''# India CPI Forecasting — Dataset Package\n\nGenerated: {summary['generated_utc']}\n\nThis package is a source-labelled research dataset bundle for the attached India CPI forecasting workflow. It contains real public-source observations and provider files only—no synthetic data. The companion PDF explains the project requirements, source decisions, modeling use, and gaps.\n\n## Bundle snapshot\n\n- Raw source files: **{summary['raw_file_count']}**\n- Total raw-data size: **{summary['raw_total_mib']} MiB**\n- MoSPI CPI rows: 15,150 (2012-base group history), 42,159 (2012-base item panel), 432 (2024-base back series), and 40,080 (2024-base current detailed all-India panel).\n- World Bank WDI panel: **{summary.get('wdi_rows') or 'see manifest'} rows**, {summary.get('wdi_indicators_ok') or 'see manifest'} of {summary.get('wdi_indicators_requested') or 'see manifest'} requested indicators retrieved after retry.\n- IMD regional rainfall: 620 rows (124 annual rows × 5 regions); daily 0.25-degree grid files: **{num_grid} annual files**, limited to CPI-era years and listed individually in the IMD manifest.\n\nExact paths, byte sizes, checksums, and tabular row counts are in `metadata/FILE_INVENTORY.csv` and `metadata/PACKAGE_MANIFEST.json`.\n\n## Folders\n\n- `raw/` — original CSV, CSV.GZ, XLS/XLSX, HTML source captures, and annual NetCDF rainfall files (gzip-compressed).\n- `metadata/DATASET_CATALOG.csv` — every major dataset family named in the workflow, with local paths, source, status, and caveats.\n- `metadata/download_manifest.json` — collector results, source URLs, and observation counts.\n- `metadata/wdi_retry_manifest.json` — retries and recovered WDI indicators.\n- `metadata/FILE_INVENTORY.csv` — SHA-256 inventory for raw files.\n- `source_notes/VERIFIED_SOURCES.md` — official links, alternatives, coverage, and access/licensing caveats.\n- `report/main.pdf` — the accompanying project/dataset analysis report.\n- `download_bundle.py`, `download_imd_grid.py`, `repair_wdi.py`, `build_catalog.py` — reproducible acquisition and inventory scripts.\n\n## Most important files\n\n- `raw/mospi/cpi_2012_all_india_group_history.csv` — official 2012-base CPI group history.\n- `raw/mospi/cpi_2012_item_history.csv` — official 2012-base CPI item observations.\n- `raw/mospi/cpi_2024_current_all_india_detailed.csv` and `raw/mospi/cpi_2024_back_series.csv` — separate 2024-base current/back-series files.\n- `raw/world_bank/wdi_selected_all_countries_long.csv.gz` — all-country annual WDI panel.\n- `raw/imf/WEOApr2026all.xlsx` — IMF April 2026 WEO workbook.\n- `raw/world_bank/pink_sheet_monthly_commodity_prices.xlsx` — monthly global commodity panel.\n- `raw/eia/brent_daily_official.xls` — official EIA daily Brent; WTI is stored separately.\n- `raw/wpi/wpi_2011_12_monthly_from_2012.xls` — official monthly OEA WPI.\n- `raw/imd/imd_regional_monthly_seasonal_rainfall_1901_2024.csv` — official long-history five-region rainfall summary.\n\n## Critical limitations and safe use\n\n1. **CPI bases stay separate.** Preserve 2012-base and 2024-base files as different vintages; do not splice levels without an official method. Compute YoY consistently within each base.\n2. **The repo-rate gap is explicit.** `raw/fred/IRSTCB01INM156N_india_central_bank_rate.csv` is the OECD/FRED *central-bank-rate proxy* (monthly through Dec-2023), not a guaranteed event-dated RBI repo history. `raw/rbi/dbie_landing_snapshot.csv` is a retrieval-date-only snapshot. Replace both with official RBI event history for final modeling.\n3. **IIP is a proxy in this package.** `INDPROINDMISMEI` is an OECD/FRED India industrial-production alternative, not current MoSPI release-vintage IIP.\n4. **PMI was not retrieved.** It is licensed; use official IIP as an open activity feature. UPI is not household consumption; the mirror export was not downloaded.\n5. **Frequency and release timing matter.** WDI and WEO are annual; EIA/FRED market data are daily; CPI and OECD indices are monthly; policy changes are event-dated. Aligning series to a month does not remove release lags.\n6. **Rainfall grids need spatial aggregation.** The annual NetCDF files contain grid data, not a ready monthly India-average feature. Apply India/crop-region masks and aggregate explicitly. The regional table provides long history for quick baselines.\n7. **Data vintages prevent look-ahead leakage.** Store `ref_month` and source release/vintage date separately. Backtests must use only data available at the forecast origin.\n8. **Re-use terms are source-specific.** Public retrieval is not a blanket license to redistribute. Retain provider attribution and review terms, especially FRED/OECD and the IMF/World Bank workbooks.\n\n## Re-running / updating\n\nFrom this folder, with Python 3 and `requests`, `pandas`, and `beautifulsoup4` available:\n\n```bash\npython3 download_bundle.py\npython3 repair_wdi.py\nIMD_GRID_START=2012 IMD_GRID_END=2024 IMD_GRID_WORKERS=3 python3 download_imd_grid.py\npython3 build_catalog.py\n```\n\nThe download scripts may take time and network access; they skip synthetic values and log failures. Check each manifest before modeling.\n'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps(summary,indent=2))
