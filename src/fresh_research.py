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

def canonical_url(url):
    """Normalizza per deduplica: rimuove schema/www, query di tracking, slash finale."""
    from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
    try:
        parts=urlsplit(str(url))
        netloc=parts.netloc.lower().removeprefix("www.")
        query=urlencode([(k,v) for k,v in parse_qsl(parts.query) if not k.lower().startswith(("utm_","fbclid","gclid","ref"))])
        path=parts.path.rstrip("/")
        return urlunsplit(("",netloc,path,query,"")).strip("/").lower()
    except Exception:
        return str(url).lower()

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

def _embed(texts, model="text-embedding-3-small"):
    import os
    key=os.getenv("OPENAI_API_KEY")
    if not key: return None
    from openai import OpenAI
    clean=[(t or "").strip()[:1500] or " " for t in texts]
    data=OpenAI(api_key=key).embeddings.create(model=model,input=clean).data
    return [d.embedding for d in data]

def semantic_match_scores(source_text, candidate_texts):
    """Cosine similarity Discover-topic vs candidati in una sola chiamata embeddings.
    Ritorna None se non c'è API key, così il chiamante usa il fallback euristico."""
    if not candidate_texts: return []
    try:
        vectors=_embed([source_text]+list(candidate_texts))
    except Exception:
        vectors=None
    if not vectors: return None
    src=vectors[0]; norm_s=sum(v*v for v in src)**0.5 or 1.0
    scores=[]
    for vec in vectors[1:]:
        dot=sum(a*b for a,b in zip(src,vec)); norm_v=sum(v*v for v in vec)**0.5 or 1.0
        scores.append(round(max(0,min(100,dot/(norm_s*norm_v)*100)),1))
    return scores

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

def seed_label(source):
    """Etichetta umana del contenuto Discover vincente: preferisce il titolo
    reale (H1/crawl), altrimenti il topic senza il prefisso di categoria."""
    for key in ("h1","title_crawled","title"):
        value=str(source.get(key,"") or "").strip()
        if value: return value[:90]
    topic=str(source.get("topic","") or "").strip()
    category=str(source.get("category","") or "").strip().lower()
    words=[w for w in topic.split() if w.lower()!=category]
    return (" ".join(words) or topic or "tema da definire").title()[:90]

def _recommendation(source, external_title, angle, gap):
    label=seed_label(source)
    formats={"news update":"Aggiornamento / timeline","guida/how-to":"Guida pratica","dati/report":"Analisi dati","opinione":"Analisi editoriale","analisi":"Approfondimento"}
    hooks={"news update":"l’aggiornamento che mancava","guida/how-to":"la guida che cercavano","dati/report":"i numeri spiegati per il tuo pubblico","opinione":"l’analisi con fonti verificabili","analisi":"scenari e cosa cambia davvero"}
    suggestion=f"{label}: {hooks.get(angle,'l’approfondimento originale')}"
    reason=(f"Questo contenuto ha già funzionato su Discover ({source.get('status','')}, "
            f"{int(source.get('clicks_current',0) or 0)} click, score {source.get('opportunity_score',0)}). "
            f"La fonte esterna usa l’angolo “{angle}”; la proposta conserva il tema validato ma aggiunge {gap.lower()}.")
    return suggestion,reason,formats.get(angle,"Approfondimento")

def refine_with_llm(source, candidates, audience_context="", provider="OpenAI", model=""):
    """Raffina le evidenze in 3 contenuti originali via OpenAI/Anthropic.
    Default consigliato: funziona ovunque con una API key, niente binari esterni.
    Ritorna dict {"suggestions":[...]} oppure una stringa di fallback."""
    import os
    cols=[c for c in ("title","url","snippet","scraped_excerpt","angle","suggested_gap") if c in candidates.columns]
    evidence=candidates[cols].head(8).to_dict("records")
    prompt=(f'Agisci come research editor italiano. Parti ESCLUSIVAMENTE dai dati Discover e dalle fonti web fornite. '
            f'Proponi 3 contenuti originali che risuonino col pubblico, senza copiare i competitor. '
            f'Restituisci solo JSON: {{"suggestions":[{{"title":"","angle":"","format":"","audience_reason":"","source_urls":[]}}]}}. '
            f'Contesto audience: {audience_context}. Contenuto Discover: {json.dumps(source,ensure_ascii=False,default=str)}. '
            f'Evidenze: {json.dumps(evidence,ensure_ascii=False,default=str)}')
    try:
        if provider=="Anthropic":
            from anthropic import Anthropic
            key=os.getenv("ANTHROPIC_API_KEY"); assert key,"ANTHROPIC_API_KEY mancante"
            text=Anthropic(api_key=key).messages.create(model=model or "claude-3-5-sonnet-latest",max_tokens=1500,messages=[{"role":"user","content":prompt}]).content[0].text
        else:
            from openai import OpenAI
            key=os.getenv("OPENAI_API_KEY"); assert key,"OPENAI_API_KEY mancante"
            text=OpenAI(api_key=key).chat.completions.create(model=model or "gpt-4o-mini",messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"}).choices[0].message.content
        return _parse_json(text)
    except Exception as exc:
        return f"Raffinamento LLM non disponibile, uso i suggerimenti deterministici: {str(exc)[:200]}"

def hermes_available(command="hermes"):
    return bool(shutil.which(command))

def _parse_json(text):
    match=re.search(r"\{.*\}",text,re.S)
    return json.loads(match.group(0) if match else text)

def refine_with_hermes(source, candidates, audience_context="", command="hermes", timeout=180):
    if not hermes_available(command): return candidates,"Hermes Agent non installato: usate raccomandazioni deterministiche."
    cols=[c for c in ("title","url","snippet","scraped_excerpt","angle","suggested_gap") if c in candidates.columns]
    evidence=candidates[cols].head(8).to_dict("records")
    prompt=f'''Agisci come research editor italiano. Parti ESCLUSIVAMENTE dai dati Discover e dalle fonti web fornite. Proponi 3 contenuti originali che possano risuonare con il pubblico, senza copiare i competitor. Restituisci solo JSON: {{"suggestions":[{{"title":"", "angle":"", "format":"", "audience_reason":"", "source_urls":[]}}]}}. Contesto audience: {audience_context}. Contenuto Discover: {json.dumps(source,ensure_ascii=False,default=str)}. Evidenze: {json.dumps(evidence,ensure_ascii=False,default=str)}'''
    try:
        proc=subprocess.run([command,"-z",prompt,"--source","tool","--max-turns","20"],capture_output=True,text=True,timeout=timeout,check=True)
        return candidates,_parse_json(proc.stdout)
    except Exception as exc: return candidates,f"Hermes non disponibile, fallback locale: {str(exc)[:220]}"

# Domini competitor italiani per la ricerca mirata site: su Google News.
CURATED_COMPETITORS=["corriere.it","repubblica.it","ansa.it","ilsole24ore.com","tg24.sky.it",
    "tgcom24.mediaset.it","today.it","fanpage.it","ilmessaggero.it","lastampa.it",
    "ilfattoquotidiano.it","adnkronos.com","rainews.it","ilpost.it"]

# Feed RSS italiani predefiniti, organizzati per verticale.
DEFAULT_RSS_FEEDS=[
    "https://www.ansa.it/sito/ansait_rss.xml","https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml",
    "https://www.ansa.it/sito/notizie/economia/economia_rss.xml","https://www.ansa.it/canale_tecnologia/notizie/tecnologia_rss.xml",
    "https://www.adnkronos.com/rss","https://www.agi.it/rss.xml",
    "https://www.repubblica.it/rss/homepage/rss2.0.xml","https://www.repubblica.it/rss/economia/rss2.0.xml",
    "https://www.repubblica.it/rss/cronaca/rss2.0.xml","https://www.repubblica.it/rss/tecnologia/rss2.0.xml",
    "https://xml2.corriereobjects.it/rss/homepage.xml","https://xml2.corriereobjects.it/rss/cronache.xml",
    "https://xml2.corriereobjects.it/rss/economia.xml","https://xml2.corriereobjects.it/rss/scienze.xml",
    "https://www.lastampa.it/rss.xml","https://www.ilfattoquotidiano.it/feed/","https://www.ilpost.it/feed/",
    "https://www.open.online/feed/","https://www.rainews.it/rss",
    "https://www.tgcom24.mediaset.it/rss/homepage.xml","https://www.tgcom24.mediaset.it/rss/cronaca.xml",
    "https://www.tgcom24.mediaset.it/rss/economia.xml","https://www.tgcom24.mediaset.it/rss/tgtech.xml",
    "https://www.today.it/feed/","https://www.milanotoday.it/feed/","https://www.romatoday.it/feed/",
    "https://www.ilsole24ore.com/rss/italia.xml","https://www.ilsole24ore.com/rss/economia.xml",
    "https://www.ilsole24ore.com/rss/finanza.xml","https://www.ilsole24ore.com/rss/tecnologia.xml",
    "https://quifinanza.it/feed/","https://www.economyup.it/feed/",
    "https://www.punto-informatico.it/feed/","https://www.agendadigitale.eu/feed/",
    "https://www.dday.it/rss","https://www.hdblog.it/rss/","https://www.macitynet.it/feed/","https://www.tomshw.it/feed/",
    "https://www.focus.it/rss","https://www.fanpage.it/feed/","https://www.geopop.it/feed/","https://www.cookist.it/feed/"]

def llm_plan_research(source, provider="OpenAI", model=""):
    """Chiede all'LLM il TIPO/FORMATO del contenuto e le query per trovare
    coperture competitor dello stesso formato. Ritorna (content_type, [queries])
    oppure None se non disponibile (il chiamante usa build_queries euristico)."""
    import os
    key=os.getenv("ANTHROPIC_API_KEY" if provider=="Anthropic" else "OPENAI_API_KEY")
    if not key: return None
    label=seed_label(source)
    prompt=(f'Sei un content strategist SEO italiano. Dato un contenuto che funziona su Google Discover, '
            f'1) classifica il TIPO/FORMATO (es: news, guida how-to, analisi, dati/report, opinione, '
            f'gossip/intrattenimento, lista/classifica, intervista). '
            f'2) genera 4 query brevi per cercare su Google News coperture competitor dello STESSO formato sullo stesso tema. '
            f'Rispondi solo JSON: {{"content_type":"","queries":[]}}. '
            f'Titolo: {label}. URL: {source.get("url","")}. Topic: {source.get("topic","")}. Keyword: {source.get("keywords","")}.')
    try:
        if provider=="Anthropic":
            from anthropic import Anthropic
            text=Anthropic(api_key=key).messages.create(model=model or "claude-3-5-sonnet-latest",max_tokens=600,messages=[{"role":"user","content":prompt}]).content[0].text
        else:
            from openai import OpenAI
            text=OpenAI(api_key=key).chat.completions.create(model=model or "gpt-4o-mini",messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"}).choices[0].message.content
        data=_parse_json(text); queries=[str(q).strip() for q in data.get("queries",[]) if str(q).strip()][:4]
        return (str(data.get("content_type","")).strip(),queries) if queries else None
    except Exception:
        return None

def select_seeds(analyzed, strategy="Top per click (cosa funziona)", limit=5):
    """Sceglie i contenuti Discover da usare come base per la ricerca competitor.
    'cosa funziona' = top per click; altrimenti per opportunità o crescita."""
    d=analyzed.copy()
    if strategy=="Top per click (cosa funziona)" and "clicks_current" in d:
        return d.sort_values("clicks_current",ascending=False).head(limit)
    if strategy=="In crescita" and "growth_pct" in d:
        return d.sort_values("growth_pct",ascending=False).head(limit)
    key="opportunity_score" if "opportunity_score" in d else d.columns[0]
    return d.sort_values(key,ascending=False).head(limit)

def add_research_to_dataframe(analyzed,provider="Web scraper + Google News",own_domain="",feed_urls=None,max_topics=5,audience_context="",use_hermes=False,hermes_command="hermes",use_llm=False,llm_provider="OpenAI",llm_model="",seed_strategy="Top per click (cosa funziona)"):
    rows=[]; out=analyzed.copy(); feed_urls=feed_urls or []; hermes_notes=[]
    for _,source_series in select_seeds(out,seed_strategy,max_topics).iterrows():
        source=source_series.to_dict(); seen=set(); source_rows=[]
        plan=llm_plan_research(source,llm_provider,llm_model) if use_llm else None
        seed_format,queries=(plan if plan else ("",build_queries(source)))
        topic=str(source.get("topic","") or "").strip()
        is_google=provider not in ("RSS personalizzati","Piano locale")
        # broad queries (sullo stesso formato) + ricerca mirata site: sui competitor curati
        search_specs=[("broad",q) for q in queries]
        if is_google and topic:
            search_specs+=[("site",f"site:{d} {topic} when:30d",d) for d in CURATED_COMPETITORS]
        if provider=="Piano locale":
            for kind,query,*_ in search_specs:
                source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"publisher":"Task locale","title":f"Ricercare: {query}","url":"","snippet":"Query pronta per ricerca controllata.","published_date":"","competitor_domain":"","competitor_match_score":0,"competitor_match_reason":"Piano offline","angle":"da verificare","suggested_gap":"Raccogliere fonti reali","scraped_title":"","scraped_excerpt":"","scrape_status":"Non eseguito","article_suggestion":"","audience_reason":"","recommended_format":"","research_provider":provider})
        else:
            def _fetch(spec):
                kind,query=spec[0],spec[1]
                try:
                    if provider=="RSS personalizzati": return spec,custom_rss_search(feed_urls,query),None
                    return spec,google_news_rss_search(query if kind=="site" or "when:" in query else f"{query} when:30d").entries,None
                except Exception as exc: return spec,[],str(exc)
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched=list(pool.map(_fetch,search_specs))
            # processa sequenzialmente per preservare la deduplica
            for (kind,query,*_),entries,err in fetched:
                if err:
                    source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"title":"Errore ricerca","snippet":err[:300],"competitor_match_score":0,"competitor_match_reason":"Provider non disponibile","angle":"errore","suggested_gap":"Riprovare","scrape_status":"Errore","research_provider":provider}); continue
                for entry in entries[:(3 if kind=="site" else 8)]:
                    link=entry.get("link",""); title=entry.get("title",""); unique=re.sub(r"\W+","",title.lower()); cu=canonical_url(link)
                    if not link or unique in seen or cu in seen: continue
                    seen.add(unique); seen.add(cu); domain=urlparse(link).netloc.lower().removeprefix("www.")
                    if own_domain and own_domain.lower() in domain: continue
                    snippet=re.sub("<[^>]+>"," ",entry.get("summary",entry.get("description","")))[:700]
                    angle=infer_angle(title,snippet); score=competitor_match_score(source,title,snippet); gap=suggested_gap_from_angle(angle,source)
                    suggestion,reason,fmt=_recommendation(source,title,angle,gap)
                    publisher=entry.get("source",{}).get("title",domain) if hasattr(entry.get("source",{}),"get") else domain
                    source_rows.append({"source_url":source["url"],"topic":source.get("topic",""),"query_used":query,"publisher":publisher,"title":title,"url":link,"snippet":snippet,"published_date":entry.get("published",entry.get("updated","")),"competitor_domain":domain,"competitor_match_score":score,"competitor_match_reason":f"Coerenza con tema/keyword Discover: {score}%","angle":angle,"suggested_gap":gap,"scraped_title":"","scraped_excerpt":"","scrape_status":"In attesa","article_suggestion":suggestion,"audience_reason":reason,"recommended_format":fmt,"research_provider":provider})
        real=[row for row in source_rows if row.get("url")]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures={pool.submit(scrape_article,row["url"]):row for row in real[:16]}
            for future in as_completed(futures): futures[future].update(future.result())
        for row in real:
            resolved=urlparse(row.get("resolved_url","") or "").netloc.lower().removeprefix("www.")
            if resolved and "google." not in resolved:
                row["competitor_domain"]=resolved
                if not row.get("publisher") or "google" in str(row.get("publisher","")).lower(): row["publisher"]=resolved
        if real:
            src_text=f'{source.get("topic","")} {source.get("keywords","")} {source.get("title","")} {source.get("h1","")}'
            sem=semantic_match_scores(src_text,[f'{r.get("title","")} {r.get("scraped_excerpt") or r.get("snippet","")}' for r in real])
            if sem:
                for row,sc in zip(real,sem):
                    row["competitor_match_score"]=sc; row["competitor_match_reason"]=f"Similarità semantica con tema Discover: {sc}%"
        frame=pd.DataFrame(source_rows)
        if use_hermes and not frame.empty:
            _,note=refine_with_hermes(source,frame,audience_context,hermes_command); hermes_notes.append({"source_url":source["url"],"result":note})
        elif use_llm and "url" in frame.columns:
            real_frame=frame[frame["url"].fillna("").ne("")]
            if not real_frame.empty:
                note=refine_with_llm(source,real_frame,audience_context,llm_provider,llm_model); hermes_notes.append({"source_url":source["url"],"result":note})
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
