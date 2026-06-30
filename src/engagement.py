"""Engagement-export analysis for editorial research."""
import re
from urllib.parse import unquote, urlparse

import pandas as pd

from .analysis import extract_topic, infer_intent
from .csv_loader import _key, _number

ALIASES = {
    "url": ("url", "page", "pagina", "path", "page_path", "landing_page"),
    "pageviews": ("pageviews", "views", "visualizzazioni", "screen_page_views"),
    "total_time_seconds": ("total_time_on_page", "total_time", "engagement_time", "tempo_totale", "total_seconds"),
    "avg_time_seconds": ("avg_time_per_view", "average_time", "avg_time", "tempo_medio", "average_engagement_time"),
    "flag": ("flag", "bounce", "conversion", "conversions"),
    "title": ("title", "titolo", "page_title"),
}

THEMES = {
    "Stipendi, patrimoni e denaro": ("stipend", "salari", "compens", "patrimon", "finanz", "milion", "miliard", "soldi", "delfin", "del vecchio"),
    "Cronaca e true crime": ("garlasco", "stasi", "delitto", "omicid", "interrogatorio", "inchiesta", "cronaca"),
    "TV, media e ascolti": ("mediaset", "rai", "la7", "ascolti", "televis", "manager"),
    "Sport, celebrità e business": ("maldini", "milan", "calcio", "sport", "vacchi", "celebr"),
    "Aziende, startup e protagonisti": ("startup", "kuiri", "azienda", "imprend", "manager", "investitor", "moncler", "unipol"),
    "Servizio e utilità": ("supermerc", "apert", "primo maggio", "lotto", "superenalotto", "orari", "bonus"),
}


def _column(df, aliases, fallback_index=None):
    lookup = {_key(c): c for c in df.columns}
    found = next((lookup.get(_key(alias)) for alias in aliases if lookup.get(_key(alias))), None)
    if found is not None:
        return df[found]
    if fallback_index is not None and len(df.columns) > fallback_index:
        return df.iloc[:, fallback_index]
    return pd.Series(["" for _ in range(len(df))], index=df.index)


def normalize_engagement_export(df):
    """Normalise GA/editorial exports, including generic five-column files."""
    if df is None or df.empty:
        return pd.DataFrame(columns=ALIASES)
    out = pd.DataFrame(index=df.index)
    out["url"] = _column(df, ALIASES["url"], 0).fillna("").astype(str).str.strip()
    out["pageviews"] = _column(df, ALIASES["pageviews"], 1).map(_number).fillna(0).astype(float)
    out["total_time_seconds"] = _column(df, ALIASES["total_time_seconds"], 2).map(_number).fillna(0).astype(float)
    out["avg_time_seconds"] = _column(df, ALIASES["avg_time_seconds"], 3).map(_number).fillna(0).astype(float)
    out["flag"] = _column(df, ALIASES["flag"], 4).map(_number).fillna(0).astype(float)
    out["title"] = _column(df, ALIASES["title"]).fillna("").astype(str).str.strip()
    missing_total = out.total_time_seconds.le(0) & out.pageviews.gt(0) & out.avg_time_seconds.gt(0)
    out.loc[missing_total, "total_time_seconds"] = out.loc[missing_total, "pageviews"] * out.loc[missing_total, "avg_time_seconds"]
    return out[out.url.ne("")].reset_index(drop=True)


def _percentile(series):
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    return numeric.rank(pct=True, method="average") * 100 if len(numeric) else numeric


def _label(url, title=""):
    if str(title).strip():
        return str(title).strip()
    slug = unquote(urlparse(str(url)).path).strip("/").split("/")[-1]
    return re.sub(r"[-_]+", " ", re.sub(r"\.(?:html?|php)$", "", slug)).strip().title()


def classify_editorial_theme(url, title=""):
    text = f"{unquote(str(url))} {title}".lower().replace("-", " ").replace("_", " ")
    scored = [(sum(term in text for term in terms), theme) for theme, terms in THEMES.items()]
    score, theme = max(scored)
    return theme if score else "Altri temi"


def analyze_engagement_export(df):
    d = normalize_engagement_export(df)
    if d.empty:
        return d
    d["title"] = [_label(url, title) for url, title in zip(d.url, d.title)]
    d["topic"] = [extract_topic(url, title) for url, title in zip(d.url, d.title)]
    d["category"] = d.url.map(lambda u: next(iter([p for p in urlparse(u).path.split("/") if p]), "generale"))
    d["intent"] = [infer_intent(title, urlparse(url).path) for url, title in zip(d.url, d.title)]
    d["editorial_theme"] = [classify_editorial_theme(url, title) for url, title in zip(d.url, d.title)]
    d["traffic_percentile"] = _percentile(d.pageviews)
    d["dwell_percentile"] = _percentile(d.avg_time_seconds)
    d["engagement_percentile"] = _percentile(d.total_time_seconds)
    d["engagement_score"] = (d.engagement_percentile * .45 + d.traffic_percentile * .30 + d.dwell_percentile * .25).round(1)
    d["engagement_quality"] = pd.cut(d.avg_time_seconds, [-1, 8, 13, 18, float("inf")], labels=["Bassa", "Media", "Alta", "Molto alta"]).astype(str)
    d["editorial_signal"] = "Cadence filler"
    d.loc[(d.traffic_percentile >= 75) & (d.dwell_percentile >= 60), "editorial_signal"] = "Headliner"
    d.loc[(d.traffic_percentile < 75) & (d.dwell_percentile >= 75), "editorial_signal"] = "Niche ad alta fedeltà"
    d.loc[(d.traffic_percentile >= 75) & (d.dwell_percentile < 40), "editorial_signal"] = "Traffico alto, retention debole"
    d["clicks_current"] = d.pageviews
    d["impressions_current"] = d.pageviews
    d["ctr_current"] = 1.0
    d["growth_pct"] = 0.0
    d["status"] = d.editorial_signal
    d["opportunity_score"] = d.engagement_score
    d["position"] = 0.0
    return d.sort_values("engagement_score", ascending=False).reset_index(drop=True)


def summarize_editorial_themes(analyzed):
    if analyzed is None or analyzed.empty or "editorial_theme" not in analyzed:
        return pd.DataFrame()
    summary = analyzed.groupby("editorial_theme", as_index=False).agg(
        articles=("url", "count"), pageviews=("pageviews", "sum"),
        total_engagement_seconds=("total_time_seconds", "sum"),
        avg_time_seconds=("avg_time_seconds", "mean"), avg_engagement_score=("engagement_score", "mean"),
    )
    summary["theme_score"] = (_percentile(summary.pageviews) * .35 + _percentile(summary.total_engagement_seconds) * .40 + _percentile(summary.avg_time_seconds) * .25).round(1)
    return summary.sort_values("theme_score", ascending=False).reset_index(drop=True)
