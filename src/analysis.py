import re
from urllib.parse import urlparse, unquote
import pandas as pd
from .csv_loader import normalize_gsc_export

STOP = {"www", "html", "htm", "news", "articolo", "pagina", "index", "del", "della", "delle", "con", "per", "gli", "una"}

def extract_topic(url, title=""):
    text = title or unquote(urlparse(str(url)).path).replace("-", " ").replace("_", " ")
    words = [w for w in re.findall(r"[a-zà-ÿ0-9]+", text.lower()) if len(w) > 2 and w not in STOP]
    return " ".join(words[:6]) or "tema da definire"

def infer_intent(title, path=""):
    text = f"{title} {path}".lower()
    if any(x in text for x in ("come ", "guida", "tutorial")): return "Informativo / how-to"
    if any(x in text for x in ("prezzo", "offerta", "miglior", "confront")): return "Commerciale"
    if any(x in text for x in ("oggi", "ultim", "news", "diretta")): return "News / aggiornamento"
    return "Informativo"

def _decorate(df):
    d = df.copy()
    d["topic"] = [extract_topic(u, t) for u, t in zip(d.url, d.title)]
    d["keywords"] = d["topic"].map(lambda x: ", ".join(str(x).split()[:5]))
    d["category"] = d.url.map(lambda u: next(iter([p for p in urlparse(u).path.split("/") if p]), "generale"))
    d["intent"] = [infer_intent(t, urlparse(u).path) for u, t in zip(d.url, d.title)]
    return d

def _score(impressions, ctr, growth):
    volume = min(float(impressions) / 1000, 1) * 40
    ctr_gap = max(0, .08 - float(ctr)) / .08 * 35
    momentum = max(-20, min(25, float(growth) / 4))
    return round(max(0, min(100, volume + ctr_gap + momentum)), 1)

def _status(row):
    if row.impressions_current >= 300 and row.ctr_current < .025: return "molte impression / CTR basso"
    if row.growth_pct >= 25: return "in crescita"
    if row.growth_pct <= -25: return "in calo"
    if row.clicks_current >= 30 and row.ctr_current >= .05: return "contenuto forte"
    return "stabile"

def analyze_single_window(df):
    n = normalize_gsc_export(df).rename(columns={"clicks":"clicks_current", "impressions":"impressions_current", "ctr":"ctr_current"})
    n["growth_pct"] = 0.0; n["status"] = n.apply(_status, axis=1)
    n["opportunity_score"] = n.apply(lambda r: _score(r.impressions_current, r.ctr_current, 0), axis=1)
    return _decorate(n).sort_values("opportunity_score", ascending=False).reset_index(drop=True)

def analyze_comparison(short_df, long_df, short_days=3, long_days=7):
    s, l = normalize_gsc_export(short_df), normalize_gsc_export(long_df)
    s = s.rename(columns={"clicks":"clicks_short", "impressions":"impressions_short", "ctr":"ctr_short", "position":"position_short"})
    l = l.rename(columns={"clicks":"clicks_long", "impressions":"impressions_long", "ctr":"ctr_long", "position":"position_long", "title":"title_long"})
    d = s.merge(l, on="url", how="outer", suffixes=("", "_x"))
    d["title"] = d.get("title", "").fillna("").mask(lambda x: x.eq(""), d.get("title_long", "").fillna(""))
    for c in ("clicks_short","impressions_short","ctr_short","position_short","clicks_long","impressions_long","ctr_long","position_long"): d[c] = pd.to_numeric(d.get(c, 0), errors="coerce").fillna(0)
    factor = short_days / max(long_days, 1)
    d["clicks_current"], d["impressions_current"], d["ctr_current"] = d.clicks_short, d.impressions_short, d.ctr_short
    base = d.clicks_long * factor
    d["growth_pct"] = ((d.clicks_short - base) / base.replace(0, pd.NA) * 100).fillna(d.clicks_short.gt(0).map({True:100, False:0})).clip(-999,999)
    d["position"] = d.position_short.mask(d.position_short.eq(0), d.position_long)
    d["status"] = d.apply(_status, axis=1)
    d["opportunity_score"] = d.apply(lambda r: _score(r.impressions_current, r.ctr_current, r.growth_pct), axis=1)
    return _decorate(d).sort_values("opportunity_score", ascending=False).reset_index(drop=True)

