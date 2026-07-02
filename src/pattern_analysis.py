"""Pattern mining sui contenuti Discover vincenti.

Discover funziona come un feed di interessi: se un articolo ha performato,
contenuti simili o adiacenti possono ripetere il risultato. Questo modulo
1) seleziona i vincitori reali della finestra, 2) profila ogni vincitore
(titolo, sottotitolo, tema, angolo, formato, tono), 3) aggrega i tratti
ricorrenti confrontandoli con il resto del sito (prevalenza e lift),
4) trasforma pattern + evidenze esterne in idee replicabili e verificabili.
"""
import hashlib
import re

import pandas as pd

from .audience_intelligence import extract_entities, infer_format, infer_hook
from .fresh_research import infer_angle

INTERROGATIVES = ("chi", "cosa", "come", "perché", "perche", "quanto", "quando", "dove")
CURIOSITY = ("ecco", "svelato", "spunta", "retroscena", "il motivo", "la verità", "cosa c'è dietro", "cosa succede")
URGENCY = ("ultim", "adesso", "subito", "oggi", "allarme", "scadenza", "entro", "diretta")
EMOTIVE = ("choc", "shock", "clamoroso", "incredibile", "gelo", "furia", "dramma", "paura", "bufera", "terremoto")
SCENARIO = ("può ", "puo ", "potrebbe", "rischia", "verso ", "ipotesi", "scenario")
SERVICE = ("come ", "guida", "quando ", "orari", "cosa fare", "bonus", "scadenz", "requisiti")


def best_title(row):
    for key in ("h1", "title_crawled", "title"):
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return str(row.get("topic", "") or "")


def title_features(title):
    """Tratti osservabili del titolo, espressi in linguaggio da riunione di redazione."""
    t = str(title or "").strip()
    if not t:
        return []
    lower = t.lower()
    words = t.split()
    feats = ["Titolo breve (≤8 parole)" if len(words) <= 8 else "Titolo medio (9-13 parole)" if len(words) <= 13 else "Titolo lungo (14+ parole)"]
    if ":" in t or " | " in t:
        feats.append("Struttura in due parti (tema: sviluppo)")
    first_comma = t.find(",")
    if 0 < first_comma <= 40:
        feats.append("Apertura «Soggetto, sviluppo»")
    if re.search(r"\d", t):
        feats.append("Numero o dato nel titolo")
    if "?" in t or words[0].lower() in INTERROGATIVES:
        feats.append("Domanda o interrogativo")
    if any(x in lower for x in CURIOSITY):
        feats.append("Curiosity gap (ecco/svelato/retroscena)")
    if t.count('"') >= 2 or "«" in t or "“" in t:
        feats.append("Citazione diretta nel titolo")
    entities = extract_entities(t)
    if entities and lower.startswith(entities[0].lower()):
        feats.append("Apertura con nome proprio")
    elif entities:
        feats.append("Nome proprio nel titolo")
    if any(x in lower for x in SCENARIO):
        feats.append("Scenario o ipotesi (può/rischia)")
    if any(x in lower for x in URGENCY):
        feats.append("Leva di attualità/urgenza")
    return feats


def infer_tone(title):
    lower = str(title or "").lower()
    if any(x in lower for x in EMOTIVE):
        return "Emotivo / enfatico"
    if any(x in lower for x in SERVICE):
        return "Servizio / utilità"
    if any(x in lower for x in CURIOSITY) or "?" in lower:
        return "Curiosità controllata"
    if any(x in lower for x in URGENCY):
        return "Urgenza / notizia"
    return "Fattuale / sobrio"


def _perf_metric(analyzed):
    for col in ("clicks_current", "engagement_score", "opportunity_score"):
        if col in analyzed and pd.to_numeric(analyzed[col], errors="coerce").fillna(0).sum() > 0:
            return col
    return "opportunity_score" if "opportunity_score" in analyzed else analyzed.columns[0]


def select_winners(analyzed, top_share=.25, min_n=5, max_n=15):
    """Vincitori = quota alta della finestra selezionata, ordinati per performance reale."""
    d = analyzed.copy()
    metric = _perf_metric(d)
    d["_perf"] = pd.to_numeric(d.get(metric), errors="coerce").fillna(0)
    d = d.sort_values("_perf", ascending=False).reset_index(drop=True)
    k = min(len(d), max(min(min_n, len(d)), min(int(round(len(d) * top_share)), max_n)))
    return d.head(k), d.iloc[k:], metric


def profile_articles(df, metric="clicks_current"):
    rows = []
    for _, row in df.iterrows():
        title = best_title(row)
        meta = str(row.get("meta_description", "") or "").strip()
        structure = []
        if meta:
            structure.append("Sottotitolo/meta descrittiva presente")
            if len(meta) <= 160:
                structure.append("Meta entro 160 caratteri")
        if str(row.get("paragraph_context", "") or "").strip():
            structure.append("Attacco diretto verificato dal crawl")
        rows.append({
            "url": row.get("url", ""), "title": title,
            "performance": float(row.get("_perf", row.get(metric, 0)) or 0),
            "theme": str(row.get("editorial_theme") or row.get("category") or "generale"),
            "angle": infer_angle(title, row.get("paragraph_context", "")),
            "hook": infer_hook(f"{title} {row.get('topic', '')} {row.get('paragraph_context', '')}"),
            "format": infer_format(title, row.get("intent", "")),
            "tone": infer_tone(title),
            "entities": ", ".join(extract_entities(title, row.get("topic", ""))),
            "title_patterns": title_features(title),
            "structure_patterns": structure,
            "editorial_signal": str(row.get("editorial_signal") or row.get("status", "")),
        })
    return pd.DataFrame(rows)


def _pattern_keys(profile_row):
    return ([("Titolo", p) for p in profile_row.title_patterns]
            + [("Struttura", p) for p in profile_row.structure_patterns]
            + [("Tema", profile_row.theme), ("Angolo", profile_row.angle),
               ("Hook", profile_row.hook), ("Formato", profile_row.format), ("Tono", profile_row.tone)])


def _aggregate_patterns(profile_w, profile_r):
    def counts(profile):
        c = {}
        for _, r in profile.iterrows():
            for key in set(_pattern_keys(r)):
                c.setdefault(key, []).append(r)
        return c
    cw, cr = counts(profile_w), counts(profile_r)
    nw, nr = max(len(profile_w), 1), max(len(profile_r), 1)
    rows = []
    for (dim, value), items in cw.items():
        if len(items) < 2:
            continue
        prevalence = len(items) / nw * 100
        baseline = len(cr.get((dim, value), [])) / nr * 100
        lift = prevalence / max(baseline, 5)
        examples = " · ".join(i.title[:70] for i in sorted(items, key=lambda x: -x.performance)[:2])
        rows.append({
            "pattern_type": dim, "pattern": value, "winners_with_pattern": len(items),
            "prevalence_pct": round(prevalence, 1), "baseline_pct": round(baseline, 1),
            "lift": round(lift, 2),
            "avg_performance": round(sum(i.performance for i in items) / len(items), 1),
            "pattern_score": round(min(100, prevalence * .6 + min(lift, 3) / 3 * 40), 1),
            "examples": examples,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["pattern_score", "prevalence_pct"], ascending=False).reset_index(drop=True)


def mine_patterns(analyzed):
    """Ritorna (profilo dei vincitori, pattern ricorrenti, metrica di performance usata)."""
    if analyzed is None or getattr(analyzed, "empty", True):
        return pd.DataFrame(), pd.DataFrame(), ""
    winners, rest, metric = select_winners(analyzed)
    profile_w = profile_articles(winners, metric)
    profile_r = profile_articles(rest, metric) if len(rest) else pd.DataFrame(columns=profile_w.columns)
    return profile_w, _aggregate_patterns(profile_w, profile_r), metric


def annotate_comparables(research_df, profile_w):
    """Marca ogni fonte esterna con i pattern di titolo che condivide col vincitore di origine."""
    if research_df is None or getattr(research_df, "empty", True) or profile_w is None or profile_w.empty:
        return research_df
    by_url = {r.url: set(r.title_patterns) for _, r in profile_w.iterrows()}
    out = research_df.copy()
    out["shared_patterns"] = [
        ", ".join(sorted(by_url.get(row.get("source_url", ""), set()) & set(title_features(row.get("title", ""))))) or ""
        for _, row in out.iterrows()
    ]
    return out


HOOK_DEVELOPMENTS = {
    "denaro e accesso esclusivo": "quanto vale davvero e chi guadagna di più",
    "nuova prova o rivelazione": "il dettaglio emerso che cambia la ricostruzione",
    "conflitto e conseguenze": "cosa cambia adesso e chi rischia di più",
    "impatto personale": "cosa cambia per famiglie e lavoratori",
    "autorità e spiegazione": "cosa dicono i dati e gli esperti",
    "utilità immediata": "date, regole e cosa fare adesso",
}


def _headline_draft(entities, theme, hook, patterns):
    subject = (str(entities).split(",")[0].strip() if entities else str(theme).title()) or "Il tema"
    development = HOOK_DEVELOPMENTS.get(hook, "cosa sta succedendo e perché conta adesso")
    if "Apertura «Soggetto, sviluppo»" in patterns or "Apertura con nome proprio" in patterns:
        return f"{subject}, {development}"
    return f"{subject}: {development}"


def build_replication_ideas(analyzed, research_df=None, limit=12):
    """Idee ancorate a tre evidenze: performance reale del vincitore, coperture
    esterne comparabili e forza dei pattern ricorrenti. Nessun punteggio inventato."""
    profile_w, patterns, metric = mine_patterns(analyzed)
    if profile_w.empty:
        return pd.DataFrame()
    pattern_scores = {(r.pattern_type, r.pattern): r.pattern_score for _, r in patterns.iterrows()} if not patterns.empty else {}
    max_perf = max(float(profile_w.performance.max()), 1.0)
    ideas = []
    for _, w in profile_w.head(limit).iterrows():
        evidence = pd.DataFrame()
        if research_df is not None and not getattr(research_df, "empty", True) and "source_url" in research_df:
            evidence = research_df[research_df.source_url.eq(w.url)]
            if "url" in evidence:
                evidence = evidence[evidence.url.fillna("").ne("")]
            if "competitor_match_score" in evidence:
                evidence = evidence.sort_values("competitor_match_score", ascending=False)
        evidence_count = len(evidence)
        best_match = float(evidence.competitor_match_score.max()) if evidence_count and "competitor_match_score" in evidence else 0.0
        matched = [(key[1], pattern_scores[key]) for key in _pattern_keys(w) if key in pattern_scores]
        recipe_items = list(dict.fromkeys(value for value, _ in sorted(matched, key=lambda x: -x[1])))[:5] or list(w.title_patterns)[:3]
        pattern_strength = sum(score for _, score in matched) / len(matched) if matched else 30.0
        perf_pct = w.performance / max_perf * 100
        score = round(perf_pct * .45 + best_match * .30 + pattern_strength * .25, 1)
        if score >= 70 and evidence_count >= 2:
            decision, urgency = "Pubblica ora", "Entro 24 ore"
        elif score >= 55 and evidence_count >= 1:
            decision, urgency = "Prepara e valida", "Entro 24-48 ore"
        elif evidence_count == 0:
            decision, urgency = "Da validare con fonti", "Cerca prima coperture esterne comparabili"
        else:
            decision, urgency = "Monitora", "Rivaluta entro 72 ore"
        lead_pattern = recipe_items[0] if recipe_items else w.hook
        metric_label = {"clicks_current": "click Discover", "engagement_score": "punti engagement", "opportunity_score": "punti opportunità"}.get(metric, metric)
        advice = (f"«{w.title[:70]}» ha già funzionato ({int(w.performance)} {metric_label}). "
                  f"Replica il pattern [{lead_pattern}] su uno sviluppo fresco dello stesso interesse"
                  + (f", confermato da {evidence_count} coperture esterne." if evidence_count else "; serve prima un trigger verificabile."))
        ideas.append({
            "idea_id": hashlib.sha1(str(w.url).encode("utf-8")).hexdigest()[:10],
            "source_url": w.url, "source_title": w.title, "theme": w.theme,
            "hook": w.hook, "angle": w.angle, "tone": w.tone, "format": w.format,
            "entities": w.entities, "title_recipe": " · ".join(recipe_items),
            "recommended_headline": _headline_draft(w.entities, w.theme, w.hook, set(w.title_patterns)),
            "evidence_count": evidence_count, "best_match_score": round(best_match, 1),
            "evidence_urls": "\n".join(evidence.url.dropna().astype(str).head(5)) if evidence_count else "",
            "comparable_titles": "; ".join(evidence.title.dropna().astype(str).head(3)) if evidence_count else "",
            "performance_percentile": round(perf_pct, 1), "pattern_strength": round(pattern_strength, 1),
            "replication_score": score, "editorial_decision": decision, "urgency": urgency,
            "replication_advice": advice,
            "differentiation": f"Non duplicare «{w.title[:60]}»: stesso pattern e stesso interesse, ma fatto nuovo e angolo distinto.",
        })
    return pd.DataFrame(ideas).sort_values("replication_score", ascending=False).reset_index(drop=True)
