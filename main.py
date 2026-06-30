import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.analysis import analyze_comparison
from src.crawler import enrich_analyzed_dataframe
from src.fresh_research import DEFAULT_RSS_FEEDS, add_research_to_dataframe
from src.gsc_api import fetch_gsc, get_credentials
from src.sheets_writer import write_overview, write_site_results

def load_settings(path):
    with open(path,encoding="utf-8") as handle: return yaml.safe_load(handle) or {}

def run_site(site,common,args):
    name=site["name"]; print(f"[{name}] GSC Discover…")
    gsc={"property":site["property"],"appearance":"discover","dimension":"page","row_limit":site.get("row_limit",common.get("row_limit",250))}
    service_path=site.get("service_account_path") or common.get("service_account_path")
    if service_path: gsc["service_account_path"]=service_path
    if common.get("service_account_info"): gsc["service_account_info"]=common["service_account_info"]
    config={"gsc":gsc}; credentials=get_credentials(config)
    fresh_days=int(site.get("fresh_days",common.get("fresh_days",3)))
    trend_days=int(site.get("trend_days",common.get("trend_days",7)))
    fresh,fresh_info=fetch_gsc(config,fresh_days,credentials=credentials)
    trend,trend_info=fetch_gsc(config,trend_days,credentials=credentials)
    if fresh.empty: raise RuntimeError("Nessun dato Discover nella finestra fresca")
    analyzed=analyze_comparison(fresh,trend,fresh_days,trend_days)
    analyzed,crawl_log=enrich_analyzed_dataframe(analyzed,int(common.get("crawl_urls",10)),float(common.get("crawl_delay",0.1)))
    serper=site.get("serper_api_key") or common.get("serper_api_key") or os.getenv("SERPER_API_KEY","")
    research,analyzed,_=add_research_to_dataframe(analyzed,"Web scraper + Google News",site.get("own_domain",site["property"]),site.get("rss_feeds") or common.get("rss_feeds") or DEFAULT_RSS_FEEDS,max_topics=int(common.get("research_topics",5)),audience_context=site.get("audience",common.get("audience","")),seed_strategy=common.get("seed_strategy","Top per click (cosa funziona)"),freshness=common.get("freshness","1d"),include_reddit=bool(common.get("include_reddit",True)),serper_api_key=serper)
    output=Path(common.get("output_dir","outputs")); output.mkdir(parents=True,exist_ok=True)
    slug="".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    analyzed.to_csv(output/f"{slug}-performance.csv",index=False,encoding="utf-8-sig")
    research.to_csv(output/f"{slug}-ideas.csv",index=False,encoding="utf-8-sig")
    sheet_url=""
    sheets=common.get("google_sheets",{})
    if sheets.get("enabled") and not args.dry_run: sheet_url=write_site_results(sheets,name,analyzed,research)
    return {"site":name,"fresh_rows":len(fresh),"ideas":len(research),"top_clicks":int(analyzed.clicks_current.sum()),"sheet_url":sheet_url,"fresh_window":f"{fresh_info['start']} → {fresh_info['end']}"}

def main():
    load_dotenv()
    parser=argparse.ArgumentParser(description="Google Discover Content Machine multi-sito")
    parser.add_argument("--config",default="multi_site.yaml"); parser.add_argument("--site",help="Esegui un solo sito per nome"); parser.add_argument("--dry-run",action="store_true",help="Non scrive su Google Sheets")
    args=parser.parse_args(); settings=load_settings(args.config); common=settings.get("global",{}); sites=settings.get("sites",[])
    if args.site: sites=[s for s in sites if s.get("name")==args.site]
    if not sites: raise SystemExit("Nessun sito configurato")
    overview=[]
    for site in sites:
        try: overview.append(run_site(site,common,args))
        except Exception as exc:
            overview.append({"site":site.get("name","?"),"error":str(exc)[:300]}); print(f"ERRORE: {overview[-1]}")
    sheets=common.get("google_sheets",{})
    if sheets.get("enabled") and not args.dry_run: write_overview(sheets,overview)
    print(json.dumps(overview,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
