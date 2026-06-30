import time
import requests
from bs4 import BeautifulSoup
from .analysis import extract_topic

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIContentIntelligenceDemo/1.0)"}
def extract_page_data(url, timeout=12):
    base = {"url":url, "crawl_status":"Errore", "crawl_error":""}
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        meta = lambda **kw: (soup.find("meta", attrs=kw) or {}).get("content", "")
        canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
        paragraphs = [p.get_text(" ", strip=True) for p in soup.select("article p, main p, p") if len(p.get_text(strip=True)) > 50][:3]
        return {**base, "crawl_status":f"OK ({r.status_code})", "title_crawled":soup.title.get_text(strip=True) if soup.title else "", "h1":soup.h1.get_text(" ",strip=True) if soup.h1 else "", "meta_description":meta(name="description"), "og_title":meta(property="og:title"), "article_section":meta(property="article:section"), "published_date":meta(property="article:published_time") or meta(name="date"), "canonical_url":canonical.get("href","") if canonical else "", "paragraph_context":" ".join(paragraphs)[:1800]}
    except Exception as e: return {**base, "crawl_error":str(e)[:300]}

def enrich_analyzed_dataframe(analyzed, max_urls=5, delay_seconds=.2):
    out = analyzed.copy(); logs=[]
    for _, row in out.head(max_urls).iterrows():
        data=extract_page_data(row.url); logs.append(data)
        for k,v in data.items():
            if k != "url": out.loc[out.url.eq(row.url), k]=v
        context = data.get("h1") or data.get("title_crawled")
        if context: out.loc[out.url.eq(row.url), "topic"] = extract_topic(row.url, context)
        if delay_seconds: time.sleep(delay_seconds)
    return out, logs

