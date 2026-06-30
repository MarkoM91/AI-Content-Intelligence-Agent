import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from urllib.parse import quote, urlparse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIContentIntelligence/1.0)"}
RESULT_COLUMNS = ["source_url","topic","query_used","publisher","title","url","snippet",
                  "published_date","competitor_domain","competitor_match_score",
                  "competitor_match_reason","angle","suggested_gap","scraped_title",
                  "scraped_excerpt","scrape_status","article_suggestion","audience_reason",
                  "recommended_format","research_provider"]

def _parse_feed(url):
    try:
        import feedparser
        return feedparser.parse(url)
    except ImportError:
        response = requests.get(url, timeout=15, headers=HEADERS)
        response.raise_for_status(); root = ET.fromstring(response.content); entries=[]
        for item in root.findall(".//item"):
            value=lambda name: (item.findtext(name) or "").strip()
            entries.append({"title":value("title"),"link":value("link"),
                "summary":value("description"),"description":value("description"),
                "published":value("pubDate"),"source":{"title":value("source")}})
        return SimpleNamespace(entries=entries)

def build_queries(row):
    title = str(row.get("h1") or row.get("title_crawled") or row.get("title") or "").strip()
    topic = str(row.get("topic", "")).strip()
    seed = title or topic
    seed = re.sub(r"\s+", " ", seed)[:140]
    queries = [seed, f'"{topic}" novità', f'{topic} analisi guida']
    return [q for q in dict.fromkeys(queries) if q.strip()][:3]

def infer_angle(title, snippet=""):
    text=f"{title} {snippet}".lower()
    if any(x in text for x in ("come ","guida","consigli","passaggi")): return "guida/how-to"
    if any(x in text for x in ("studio","dati","report","ricerca","classifica")): return "dati/report"
    if any(x in text for x in ("opinione","commento","editoriale")): return "opinione"
    if any(x in text for x in ("analisi","perché","scenario","cosa cambia")): return "analisi"
    return "news update"

def _terms(value):
    stop={"della","delle","degli","nella","nelle","sono","come","alla","allo","con","per","che","del","dei","una","the"}
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+",str(value).lower()) if len(w)>2 and w not in stop}

def competitor_match_score(row, title, snippet=""):
    source=_terms(f'{row.get("topic","")} {row.get("keywords","")} {row.get("title","")}')
    target=_terms(f"{title} {snippet}")
    overlap=len(source & target)/max(len(source),1)
    return round(min(100, overlap*120),1)

def suggested_gap_from_angle(angle, row):
    return {"news update":"Timeline + conseguenze pratiche + FAQ",
        "guida/how-to":"Checklist, esempi italiani e dati proprietari",
        "dati/report":"Interpretazione dei numeri per il pubblico del sito",
        "opinione":"Fact-check e analisi con fonti verificabili",
        "analisi":"Aggiornamento operativo con scenari e cosa cambia"}.get(angle,"Approfondimento originale e verificabile")

def google_news_rss_search(query):
    return _parse_feed(f"https://news.google.com/rss/search?q={quote(query)}&hl=it&gl=IT&ceid=IT:it")

def custom_rss_search(feed_urls, query):
    entries=[]
    for url in feed_urls: entries.extend(_parse_feed(url.strip()).entries)
    terms=_terms(query)
    return [e for e in entries if terms & _terms(f'{e.get("title","")} {e.get("summary","")}')]

def scrape_article(url):
    try:
        response=requests.get(url,headers=HEADERS,timeout=12,allow_redirects=True)
        response.raise_for_status(); soup=BeautifulSoup(response.text,"html.parser")
        for node in soup.select("script,style,nav,footer,aside"): node.decompose()
        title=(soup.find("meta",property="og:title") or {}).get("content","")
        if not title and soup.title: title=soup.title.get_text(" ",strip=True)
        paragraphs=[p.get_text(" ",strip=True) for p in soup.select("article p, main p, p") if len(p.get_text(" ",strip=True))>70]
        return {"scraped_title":title[:300],"scraped_excerpt":" ".join(paragraphs[:4])[:1800],
                "scrape_status":f"OK ({response.status_code})","resolved_url":response.url}
    except Exception as exc:
        return {"scraped_title":"","scraped_excerpt":"","scrape_status":f"Errore: {str(exc)[:180]}","resolved_url":url}

def _recommendation(source, external_title, angle, gap):
    topic=str(source.get("topic","tema")).strip().title()
    formats={"news update":"Aggiornamento / timeline","guida/how-to":"Guida pratica","dati/report":"Analisi dati","opinione":"Analisi editoriale","analisi":"Approfondimento"}
    suggestion=f"{topic}: cosa sta cambiando e perché conta davvero"
    reason=(f"Il tema ha già prodotto segnali Discover ({source.get('status','')}, "
            f"score {source.get('opportunity_score',0)}). La fonte esterna usa l’angolo “{angle}”; "
            f"la proposta conserva il tema validato ma aggiunge {gap.lower()}.")
    return suggestion,reason,formats.get(angle,"Approfondimento")

def hermes_available(command="hermes"):
    return bool(shutil.which(command))

def _parse_json(text):
    match=re.search(r"\{.*\}",text,re.S)
    return json.loads(match.group(0) if match else text)

def refine_with_hermes(source, candidates, audience_context="", command="hermes", timeout=180):
    if not hermes_available(command): return candidates,"Hermes Agent non installato: usate raccomandazioni deterministiche."
    evidence=candidates[["title","url","snippet","scraped_excerpt","angle","suggested_gap"]].head(8).to_dict("records")
    prompt=f'''Agisci come research editor italiano. Parti ESCLUSIVAMENTE dai dati Discover e dalle fonti web fornite. Proponi 3 contenuti originali che possano risuonare con il pubblico, senza copiare i competitor. Restituisci solo JSON: {{"suggestions":[{{"title":"", "angle":"", "format":"", "audience_reason":"", "source_urls":[]}}]}}. Contesto audience: {audience_context}. Contenuto Discover: {json.dumps(source,ensure_ascii=False,default=str)}. Evidenze: {json.dumps(evidence,ensure_ascii=False,default=str)}'''
    try:
        proc=subprocess.run([command,"-z",prompt,"--source","tool","--max-turns","20"],capture_output=True,text=True,timeout=timeout,check=True)
        return candidates,_parse_json(proc.stdout)
    except Exception as exc: return candidates,f"Hermes non disponibile, fallback locale: {str(exc)[:220]}"

def add_research_to_dataframe(analyzed,provider="Web scraper + Google News",own_domain="",feed_urls=None,max_topics=5,audience_context="",use_hermes=False,hermes_command="hermes"):
    rows=[]; out=analyzed.copy(); feed_urls=feed_urls or []; hermes_notes=[]
    for _,source_series in out.head(max_topics).iterrows():
        source=source_series.to_dict(); seen=set(); source_rows=[]
        for query in build_queries(source):
            if provider=="Piano locale":
                source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"publisher":"Task locale","title":f"Ricercare: {query}","url":"","snippet":"Query pronta per ricerca controllata.","published_date":"","competitor_domain":"","competitor_match_score":0,"competitor_match_reason":"Piano offline","angle":"da verificare","suggested_gap":"Raccogliere fonti reali","scraped_title":"","scraped_excerpt":"","scrape_status":"Non eseguito","article_suggestion":"","audience_reason":"","recommended_format":"","research_provider":provider}); continue
            try:
                entries=custom_rss_search(feed_urls,query) if provider=="RSS personalizzati" else google_news_rss_search(query).entries
                for entry in entries[:8]:
                    link=entry.get("link",""); title=entry.get("title",""); unique=re.sub(r"\W+","",title.lower())
                    if not link or unique in seen: continue
                    seen.add(unique); domain=urlparse(link).netloc.lower().removeprefix("www.")
                    if own_domain and own_domain.lower() in domain: continue
                    snippet=re.sub("<[^>]+>"," ",entry.get("summary",entry.get("description","")))[:700]
                    angle=infer_angle(title,snippet); score=competitor_match_score(source,title,snippet); gap=suggested_gap_from_angle(angle,source)
                    suggestion,reason,fmt=_recommendation(source,title,angle,gap)
                    publisher=entry.get("source",{}).get("title",domain) if hasattr(entry.get("source",{}),"get") else domain
                    source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"publisher":publisher,"title":title,"url":link,"snippet":snippet,"published_date":entry.get("published",entry.get("updated","")),"competitor_domain":domain,"competitor_match_score":score,"competitor_match_reason":f"Coerenza con tema/keyword Discover: {score}%","angle":angle,"suggested_gap":gap,"scraped_title":"","scraped_excerpt":"","scrape_status":"In attesa","article_suggestion":suggestion,"audience_reason":reason,"recommended_format":fmt,"research_provider":provider})
            except Exception as exc:
                source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"title":"Errore ricerca","snippet":str(exc)[:300],"competitor_match_score":0,"competitor_match_reason":"Provider non disponibile","angle":"errore","suggested_gap":"Riprovare","scrape_status":"Errore","research_provider":provider})
        real=[row for row in source_rows if row.get("url")]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures={pool.submit(scrape_article,row["url"]):row for row in real[:12]}
            for future in as_completed(futures): futures[future].update(future.result())
        frame=pd.DataFrame(source_rows)
        if use_hermes and not frame.empty:
            _,note=refine_with_hermes(source,frame,audience_context,hermes_command); hermes_notes.append({"source_url":source["url"],"result":note})
        rows.extend(source_rows)
    research=pd.DataFrame(rows).reindex(columns=RESULT_COLUMNS)
    if not research.empty:
        research=research.sort_values(["source_url","competitor_match_score"],ascending=[True,False]).drop_duplicates(["source_url","url","title"])
    for url in out.url:
        subset=research[research.source_url.eq(url)] if not research.empty else research
        out.loc[out.url.eq(url),"fresh_source_count"]=len(subset[subset.url.fillna("").ne("")]) if not subset.empty else 0
        out.loc[out.url.eq(url),"fresh_angles"]="; ".join(subset.angle.dropna().unique())
        out.loc[out.url.eq(url),"fresh_urls"]="\n".join(subset.url.dropna().astype(str).head(8))
        out.loc[out.url.eq(url),"competitor_domains_found"]="; ".join(x for x in subset.competitor_domain.dropna().unique() if x)
        out.loc[out.url.eq(url),"best_competitor_match_score"]=subset.competitor_match_score.max() if not subset.empty else 0
        out.loc[out.url.eq(url),"fresh_research_summary"]=" | ".join((subset.title.fillna("")+": "+subset.suggested_gap.fillna("")).head(5))
        out.loc[out.url.eq(url),"content_suggestions"]=" | ".join(subset.article_suggestion.dropna().unique()[:3])
    return research,out,hermes_notes
