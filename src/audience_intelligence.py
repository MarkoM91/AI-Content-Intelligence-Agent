"""Audience-DNA extraction and Discover-adjacent opportunity scoring."""
import hashlib
import re
from urllib.parse import urlparse

import pandas as pd


STOP = {
    "alla", "allo", "anche", "come", "dalla", "delle", "degli", "della", "dopo",
    "nelle", "nella", "perché", "questo", "questa", "sono", "sulla", "sulle", "italia",
    "italiano", "italiana", "guida", "news", "oggi", "tutto", "verso", "with", "from",
}

HOOK_RULES = {
    "denaro e accesso esclusivo": ("stipend", "salari", "compens", "patrimon", "milion", "miliard", "finanz", "soldi", "prezzo"),
    "nuova prova o rivelazione": ("video", "prova", "interrog", "inedit", "rivela", "segreto", "document", "inchiesta"),
    "conflitto e conseguenze": ("scontro", "contro", "crisi", "rischio", "crollo", "accusa", "polem", "licenzi", "addio"),
    "impatto personale": ("cambia", "famiglie", "lavoro", "mutui", "pension", "bonus", "tasse", "risparmi"),
    "autorità e spiegazione": ("analisi", "esperto", "spiega", "studio", "dati", "report", "classifica"),
    "utilità immediata": ("come", "guida", "quando", "orari", "apert", "scadenza", "cosa fare"),
}

ADJACENCIES = {
    "denaro e accesso esclusivo": [
        ("entità parallela", "compensi, patrimonio e investimenti dei protagonisti collegati", "Mostrare numeri normalmente poco accessibili e confrontarli con il personaggio vincente."),
        ("struttura nascosta", "società, proprietà e partecipazioni dietro la storia", "Ricostruire chi controlla cosa e quali interessi economici si incrociano."),
        ("confronto", "chi guadagna di più nello stesso settore", "Trasformare il dato isolato in una gerarchia comparabile e verificabile."),
    ],
    "nuova prova o rivelazione": [
        ("sviluppo seriale", "nuove prove, testimonianze e contraddizioni", "Aggiornare il caso attraverso il dettaglio nuovo che cambia la lettura precedente."),
        ("protagonista adiacente", "il ruolo dei personaggi secondari nella vicenda", "Spostare il punto di vista su un soggetto già presente nell'interesse del pubblico."),
        ("ricostruzione", "timeline completa e passaggi ancora irrisolti", "Ridurre la complessità collegando passato, novità e domande aperte."),
    ],
    "conflitto e conseguenze": [
        ("conseguenza", "chi perde, chi guadagna e cosa cambia adesso", "Portare il conflitto dal rumore alle conseguenze concrete per il pubblico."),
        ("scenario", "i prossimi sviluppi e le decisioni possibili", "Costruire scenari verificabili partendo dai protagonisti già validati."),
        ("precedente", "casi simili e come sono finiti", "Usare precedenti comparabili per spiegare la traiettoria probabile."),
    ],
    "impatto personale": [
        ("segmento adiacente", "come cambia per famiglie, imprese e risparmiatori", "Applicare lo stesso tema a segmenti di pubblico con conseguenze differenti."),
        ("decisione pratica", "cosa conviene fare ora e quali errori evitare", "Convertire l'interesse in una decisione concreta e tempestiva."),
        ("comparazione", "vincitori, penalizzati e differenze territoriali", "Rendere visibile l'impatto con dati e confronti immediati."),
    ],
    "autorità e spiegazione": [
        ("dato nuovo", "numeri aggiornati e cosa raccontano davvero", "Aggiornare l'evidenza e interpretarla per lo stesso interesse di audience."),
        ("voce autorevole", "esperti e protagonisti a confronto", "Usare fonti riconoscibili per aumentare fiducia e profondità."),
        ("caso concreto", "chi sta già applicando il cambiamento", "Passare dalla spiegazione astratta a esempi osservabili e attuali."),
    ],
    "utilità immediata": [
        ("aggiornamento", "nuove date, regole e condizioni", "Aggiornare il servizio prima che perda utilità per l'audience."),
        ("segmento", "la guida specifica per un pubblico adiacente", "Riutilizzare il bisogno con una risposta più mirata."),
        ("errore da evitare", "cosa si sbaglia più spesso e quanto costa", "Aggiungere rischio e conseguenza concreta alla promessa di utilità."),
    ],
}


def _words(value):
    return [w for w in re.findall(r"[a-zà-ÿ0-9]+", str(value).lower()) if len(w) > 2 and w not in STOP]


def infer_hook(text):
    lower = str(text).lower()
    ranked = [(sum(term in lower for term in terms), label) for label, terms in HOOK_RULES.items()]
    score, label = max(ranked)
    return label if score else "curiosità e aggiornamento"


def infer_format(text, intent=""):
    lower = f"{text} {intent}".lower()
    if any(x in lower for x in ("intervista", "parla", "dichiara")): return "Intervista / voce"
    if any(x in lower for x in ("classifica", "quanto", "stipend", "dati", "report")): return "Numeri / classifica"
    if any(x in lower for x in ("come", "guida", "cosa fare", "quando")): return "Servizio / guida"
    if any(x in lower for x in ("analisi", "perché", "scenario", "cosa cambia")): return "Analisi / scenario"
    return "News / sviluppo"


def extract_entities(title, topic=""):
    title = str(title or "")
    proper = re.findall(r"\b[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+(?:\s+[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+){0,2}\b", title)
    entities = [x for x in proper if x.lower() not in STOP]
    if not entities:
        entities = [w.title() for w in _words(topic)[:3]]
    return list(dict.fromkeys(entities))[:5]


def _performance_score(row):
    if "engagement_score" in row and pd.notna(row.get("engagement_score")):
        return float(row.get("engagement_score", 0) or 0)
    return float(row.get("opportunity_score", 0) or 0)


def build_audience_dna(analyzed, limit=12):
    if analyzed is None or analyzed.empty:
        return pd.DataFrame()
    rows = []
    ranked = analyzed.copy()
    ranked["_strength"] = ranked.apply(_performance_score, axis=1)
    for _, source in ranked.sort_values("_strength", ascending=False).head(limit).iterrows():
        title = str(source.get("h1") or source.get("title_crawled") or source.get("title") or source.get("topic") or "")
        topic = str(source.get("topic") or "")
        hook = infer_hook(f"{title} {topic} {source.get('paragraph_context','')}")
        entities = extract_entities(title, topic)
        category = str(source.get("editorial_theme") or source.get("category") or "generale")
        content_format = infer_format(title, source.get("intent", ""))
        tokens = _words(f"{title} {topic}")[:7]
        cluster = f"{category} · {hook}"
        rows.append({
            "source_url": source.get("url", ""), "source_title": title, "interest_cluster": cluster,
            "primary_topic": " ".join(tokens[:4]), "entities": ", ".join(entities),
            "winning_hook": hook, "winning_format": content_format,
            "audience_strength": round(_performance_score(source), 1),
            "performance_signal": source.get("editorial_signal") or source.get("status", ""),
            "why_it_worked": f"Interesse «{category}» attivato con la leva «{hook}» nel formato {content_format.lower()}.",
        })
    return pd.DataFrame(rows).sort_values("audience_strength", ascending=False).reset_index(drop=True)


def _fresh_evidence(research_df, source_url):
    if research_df is None or getattr(research_df, "empty", True) or "source_url" not in research_df:
        return pd.DataFrame()
    subset = research_df[research_df.source_url.eq(source_url)].copy()
    if "url" in subset: subset = subset[subset.url.fillna("").ne("")]
    return subset


def build_discover_expansion(analyzed, research_df=None, limit=12):
    dna = build_audience_dna(analyzed, limit=limit)
    if dna.empty:
        return pd.DataFrame()
    opportunities = []
    for _, seed in dna.iterrows():
        hook = seed.winning_hook
        templates = ADJACENCIES.get(hook, [
            ("entità adiacente", "protagonisti, organizzazioni e casi collegati", "Espandere l'interesse verso soggetti semanticamente vicini."),
            ("sviluppo", "cosa è cambiato e cosa succede adesso", "Dare continuità all'interesse attraverso un aggiornamento verificabile."),
            ("argomento", "conseguenze, numeri e domande ancora aperte", "Aprire un territorio adiacente senza replicare l'articolo vincente."),
        ])
        evidence = _fresh_evidence(research_df, seed.source_url)
        evidence_count = len(evidence)
        best_match = float(evidence.competitor_match_score.max()) if evidence_count and "competitor_match_score" in evidence else 0.0
        evidence_urls = "\n".join(evidence.url.dropna().astype(str).head(5)) if evidence_count and "url" in evidence else ""
        freshness = min(100.0, 25.0 + evidence_count * 12.0)
        for index, (adjacency_type, adjacent_topic, argument) in enumerate(templates):
            audience = float(seed.audience_strength)
            semantic = min(100.0, 72.0 + best_match * .22 - index * 4)
            entity = 82.0 if seed.entities else 58.0
            format_fit = max(60.0, 90.0 - index * 7)
            novelty = min(95.0, 68.0 + index * 10 - min(evidence_count, 5) * 2)
            score = audience * .30 + semantic * .25 + entity * .15 + freshness * .15 + format_fit * .10 + novelty * .05
            oid = hashlib.sha1(f"{seed.source_url}|{adjacency_type}|{adjacent_topic}".encode("utf-8")).hexdigest()[:10]
            opportunities.append({
                "opportunity_id": oid, "source_url": seed.source_url, "source_title": seed.source_title,
                "winning_cluster": seed.interest_cluster, "winning_hook": hook, "entities": seed.entities,
                "adjacency_type": adjacency_type, "adjacent_topic": adjacent_topic,
                "proposed_argument": argument, "recommended_format": seed.winning_format,
                "audience_affinity": round(audience, 1), "semantic_adjacency": round(semantic, 1),
                "entity_affinity": round(entity, 1), "freshness_score": round(freshness, 1),
                "format_fit": round(format_fit, 1), "editorial_novelty": round(novelty, 1),
                "discover_potential": round(score, 1), "evidence_count": evidence_count,
                "evidence_urls": evidence_urls, "validation_status": "Validata da fonti fresche" if evidence_count else "Ipotesi da validare",
            })
    return pd.DataFrame(opportunities).sort_values("discover_potential", ascending=False).reset_index(drop=True)
