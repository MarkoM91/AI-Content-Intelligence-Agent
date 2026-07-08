import json
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from src.analysis import analyze_comparison
from src.crawler import enrich_analyzed_dataframe
from src.fresh_research import add_research_to_dataframe
from src.llm import generate_brief
from src.agents import propose_actions
from src.reporting import generate_markdown_report, generate_json_export
from src.storage import save_snapshot, load_snapshot
from src.csv_loader import read_csv
from src.engagement import analyze_engagement_export, summarize_editorial_themes
from src.pattern_analysis import mine_patterns, annotate_comparables, build_replication_ideas

load_dotenv()
import os
for _secret_key in ("OPENAI_API_KEY","ANTHROPIC_API_KEY","SERPER_API_KEY"):
    try:
        if not os.getenv(_secret_key) and _secret_key in st.secrets: os.environ[_secret_key]=str(st.secrets[_secret_key])
    except Exception: pass
st.set_page_config(page_title="AI Content Intelligence Agent",page_icon="🧭",layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root{--ink:#17231f;--muted:#66736e;--paper:#f7f8f5;--surface:#fff;--line:#dfe5e1;--accent:#176b52;--accent-2:#d7efe5;--warm:#a76532;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--ink);}
.stApp{background:var(--paper);}
.block-container{max-width:1320px;padding-top:1.25rem;padding-bottom:4rem;}
h1,h2,h3,h4{font-family:'Manrope',sans-serif!important;letter-spacing:-.025em;color:var(--ink);}
[data-testid="stSidebar"]{background:#eef1ed;border-right:1px solid #d8dfda;}
[data-testid="stSidebar"]>div:first-child{padding-top:1.4rem;}
[data-testid="stSidebar"] h2{font-size:1rem;text-transform:uppercase;letter-spacing:.09em;color:#42534c;margin-top:1.7rem;}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p{font-size:.86rem;}
input,textarea,[data-baseweb="select"]>div{border-color:#ced7d1!important;border-radius:10px!important;background:#fff!important;}
.hero{position:relative;overflow:hidden;background:#14241f;border:1px solid #2d4039;border-radius:20px;padding:34px 38px 30px;color:#fff;margin-bottom:18px;box-shadow:0 16px 45px rgba(25,43,37,.14);}
.hero:after{content:"";position:absolute;width:260px;height:260px;border:1px solid rgba(255,255,255,.09);border-radius:50%;right:-65px;top:-120px;box-shadow:0 0 0 42px rgba(255,255,255,.025),0 0 0 84px rgba(255,255,255,.018);}
.hero .eyebrow{color:#9fd2bf;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;}
.hero h1{position:relative;margin:0;max-width:780px;font-size:2.05rem;font-weight:800;line-height:1.15;color:#fff;z-index:1;}
.hero>p{position:relative;margin:.8rem 0 1.15rem;max-width:760px;color:#dce8e2;font-size:1rem;line-height:1.55;z-index:1;}
.hero .pipe{position:relative;display:flex;flex-wrap:wrap;gap:7px;z-index:1;}
.hero .pipe span{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:5px 11px;border-radius:999px;color:#e8f1ed;font-size:.74rem;font-weight:600;}
.trust-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 22px;}
.trust-item{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 15px;color:#4e5d57;font-size:.82rem;box-shadow:0 3px 12px rgba(23,35,31,.035);}
.trust-item b{display:block;color:var(--ink);font-family:'Manrope';font-size:.88rem;margin-bottom:2px;}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:0 4px 18px rgba(23,35,31,.045);}
[data-testid="stMetricLabel"]{color:var(--muted);font-weight:600;}
[data-testid="stMetricValue"]{font-family:'Manrope';font-weight:800;color:var(--accent);letter-spacing:-.035em;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:4px;background:#e9ede9;padding:5px;border-radius:12px;margin-bottom:18px;}
button[data-baseweb="tab"]{height:42px;border-radius:9px!important;padding:0 16px!important;font-weight:700;font-size:.86rem;color:#5e6c66;}
button[data-baseweb="tab"][aria-selected="true"]{background:#fff;color:var(--ink);box-shadow:0 2px 9px rgba(23,35,31,.08);}
button[data-baseweb="tab"]>div[data-testid="stMarkdownContainer"]>p{font-size:.86rem;}
.stButton>button,.stDownloadButton>button{border-radius:10px;border:1px solid #bfcac4;font-weight:700;min-height:42px;transition:all .18s ease;}
.stButton>button[kind="primary"]{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 7px 18px rgba(23,107,82,.18);}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--accent);color:var(--accent);transform:translateY(-1px);}
.stButton>button[kind="primary"]:hover{background:#115841;color:#fff;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:13px;overflow:hidden;background:#fff;}
[data-testid="stAlert"]{border-radius:12px;border-width:1px;}
[data-testid="stExpander"]{background:#fff;border:1px solid var(--line);border-radius:12px;}
.sugg-card{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:14px;padding:18px 20px;margin-bottom:13px;box-shadow:0 5px 20px rgba(23,35,31,.05);transition:transform .18s ease,box-shadow .18s ease;}
.sugg-card:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(23,35,31,.08);}
.sugg-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;}
.sugg-head h4{margin:0;font-size:1.03rem;font-weight:800;color:var(--ink);line-height:1.4;}
.sugg-reason{color:#56645e;font-size:.9rem;margin:.6rem 0 .85rem;line-height:1.55;}
.sugg-meta{display:flex;flex-wrap:wrap;gap:7px;align-items:center;}
.sugg-meta span{background:#f0f4f1;color:#3c534a;padding:4px 9px;border-radius:7px;font-size:.75rem;font-weight:600;}
.badge{padding:4px 10px;border-radius:999px;font-weight:800;font-size:.74rem;white-space:nowrap;}
.src-btn{margin-left:auto;background:var(--ink);color:#fff!important;text-decoration:none;padding:7px 13px;border-radius:8px;font-size:.78rem;font-weight:700;}
.src-btn:hover{background:var(--accent);}
div[class*="st-key-card"]{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 5px 20px rgba(23,35,31,.05);padding:1.05rem 1.2rem;}
.eyebrow-sm{font-size:.68rem;font-weight:800;letter-spacing:.12em;color:#8a978f;text-transform:uppercase;margin:2px 0 6px;}
.pill{display:inline-block;padding:4px 12px;border-radius:999px;font-weight:800;font-size:.74rem;white-space:nowrap;}
.charpill{display:inline-block;background:#eef2ef;border-radius:6px;padding:2px 8px;font-size:.7rem;font-weight:700;color:#4c5b54;vertical-align:middle;margin-left:8px;}
.headline-lg{font-family:'Manrope',sans-serif;font-size:1.32rem;font-weight:800;line-height:1.32;color:var(--ink);margin:0 0 6px;}
.win-ref{color:#66736e;font-size:.88rem;margin:0 0 2px;line-height:1.4;}
.src-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px dashed #e4e9e5;}
.src-row:last-child{border-bottom:none;}
.src-main{flex:1;min-width:0;}
.src-main a{color:var(--ink);font-weight:700;font-size:.9rem;text-decoration:none;line-height:1.35;}
.src-main a:hover{color:var(--accent);}
.src-sub{color:#79857f;font-size:.76rem;margin-top:2px;}
.matchbar{width:76px;flex-shrink:0;}
.matchbar .bar{height:5px;border-radius:3px;background:#e5eae6;overflow:hidden;}
.matchbar .bar i{display:block;height:5px;background:var(--accent);border-radius:3px;}
.matchbar .lbl{font-size:.68rem;font-weight:700;color:#6d7a74;text-align:right;margin-top:2px;}
.advice{color:#56645e;font-size:.92rem;line-height:1.55;margin:.15rem 0 .55rem;}
.chips{display:flex;flex-wrap:wrap;gap:7px;align-items:center;}
.chips span{background:#f0f4f1;color:#3c534a;padding:4px 10px;border-radius:7px;font-size:.75rem;font-weight:600;}
.decision-strip{border-radius:12px;padding:13px 16px;font-size:.92rem;line-height:1.5;margin:0 0 14px;}
.stat-strip{display:flex;gap:22px;flex-wrap:wrap;align-items:baseline;color:#5b6963;font-size:.85rem;font-weight:600;margin:2px 0 14px;}
.stat-strip b{color:var(--accent);font-family:'Manrope',sans-serif;font-size:1.1rem;margin-right:4px;}
.alt-title{display:flex;align-items:baseline;gap:8px;padding:6px 0;border-bottom:1px dashed #e4e9e5;font-size:.92rem;color:var(--ink);}
.alt-title:last-child{border-bottom:none;}
.alt-title .n{color:#9aa6a0;font-weight:800;font-size:.78rem;min-width:14px;}
div[class*="st-key-navtabs"] [role="radiogroup"]{gap:4px;background:#e9ede9;padding:5px;border-radius:12px;display:flex;flex-wrap:wrap;}
div[class*="st-key-navtabs"] label{background:transparent;border-radius:9px;padding:9px 16px;margin:0;}
div[class*="st-key-navtabs"] label>div:first-child{display:none;}
div[class*="st-key-navtabs"] label p{font-weight:700;font-size:.86rem;color:#5e6c66;}
div[class*="st-key-navtabs"] label:has(input:checked){background:#fff;box-shadow:0 2px 9px rgba(23,35,31,.08);}
div[class*="st-key-navtabs"] label:has(input:checked) p{color:var(--ink);}
@media(max-width:760px){
  .block-container{padding:1rem .85rem 5rem;}
  .hero{padding:25px 22px;border-radius:16px;}
  .hero h1{font-size:1.55rem;line-height:1.2;}
  .hero>p{font-size:.9rem;}
  .trust-strip{grid-template-columns:1fr;gap:7px;}
  .trust-item{padding:10px 12px;}
  [data-testid="stTabs"] [data-baseweb="tab-list"]{overflow-x:auto;justify-content:flex-start;}
  button[data-baseweb="tab"]{padding:0 12px!important;white-space:nowrap;}
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.6rem;}
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{min-width:100%!important;width:100%!important;flex:1 1 100%!important;}
  .sugg-head{display:block;}.badge{display:inline-block;margin-top:8px;}.src-btn{width:100%;text-align:center;margin:5px 0 0;}
}
</style>""",unsafe_allow_html=True)

st.markdown("""<div class="hero">
<div class="eyebrow">Il mattinale della redazione</div>
<h1>Cosa ha funzionato, cosa pubblicare, come scriverlo.</h1>
<p>Tre domande, tre schede. L'analisi parte da sola quando carichi i dati; i bottoni esistono solo dove serve una decisione umana.</p>
<div class="pipe"><span>01 · Cosa ha funzionato</span><span>02 · Cosa pubblicare</span><span>03 · Brief e consegna</span></div>
</div>
<div class="trust-strip">
  <div class="trust-item"><b>Evidenze prima delle idee</b>GSC, engagement e fonti reali guidano ogni proposta.</div>
  <div class="trust-item"><b>Controllo editoriale</b>Le decisioni sensibili restano human-in-the-loop.</div>
  <div class="trust-item"><b>Output operativo</b>Brief, priorità e report pronti per la redazione.</div>
</div>""",unsafe_allow_html=True)

import html as _html
def _match_badge(score):
    s=float(score or 0)
    if s<=0: return ""
    color="#16a34a" if s>=60 else "#d97706" if s>=35 else "#dc2626"
    return f'<span class="badge" style="background:{color}1a;color:{color}">Match {s:.0f}</span>'

def _suggestion_card(item):
    title=_html.escape(str(item.get("article_suggestion","Idea da sviluppare")))
    reason=_html.escape(str(item.get("audience_reason","")))
    fmt=_html.escape(str(item.get("recommended_format","") or "")); angle=_html.escape(str(item.get("angle","") or ""))
    dom=_html.escape(str(item.get("competitor_domain","") or "")); url=str(item.get("url","") or "")
    dom_chip=(f'<span style="background:#f6e8df;color:#8a4928">Benchmark · {dom}</span>' if item.get("is_benchmark") else f'<span>Fonte · {dom}</span>') if dom else ''
    meta=f'<span>Formato · {fmt}</span><span>Angolo · {angle}</span>'+dom_chip
    link=f'<a class="src-btn" href="{_html.escape(url)}" target="_blank">Apri evidenza ↗</a>' if url else ''
    return (f'<div class="sugg-card"><div class="sugg-head"><h4>{title}</h4>{_match_badge(item.get("competitor_match_score",0))}</div>'
            f'<p class="sugg-reason">{reason}</p><div class="sugg-meta">{meta}{link}</div></div>')

def _idea_card(item):
    title=_html.escape(str(item.get("recommended_headline") or item.get("source_title","Idea da sviluppare")))
    advice=_html.escape(str(item.get("replication_advice") or item.get("editorial_advice","")))
    decision=_html.escape(str(item.get("editorial_decision","Da valutare")))
    urgency=_html.escape(str(item.get("urgency","")))
    origin=_html.escape(str(item.get("source_title",""))[:60])
    evidence=int(item.get("evidence_count",0) or 0)
    score=float(item.get("replication_score",0) or 0)
    color="#176b52" if score>=70 else "#a76532" if score>=55 else "#66736e"
    ev_chip=f'<span>{evidence} fonti web a supporto</span>' if evidence else '<span style="background:#f6e8df;color:#8a4928">Ancora da validare sul web</span>'
    return (f'<div class="sugg-card"><div class="sugg-head"><h4>{title}</h4>'
            f'<span class="badge" style="background:{color}18;color:{color}">Priorità {score:.0f}</span></div>'
            f'<p class="sugg-reason"><b>{decision}</b> · {advice}</p><div class="sugg-meta"><span>Quando · {urgency}</span>'
            f'{ev_chip}<span>Origine · {origin}</span></div></div>')

DECISION_COLORS={"Pubblica ora":("#176b52","#e1f0e8"),"Pubblica subito":("#176b52","#e1f0e8"),"Prepara e valida":("#a76532","#f6ecdf"),"Monitora":("#66736e","#edf1ee"),"Da validare con fonti":("#8a6d3b","#f5efdf"),"Non prioritario":("#8d3f3f","#f7e7e7")}
def _decision_colors(decision):
    for key,val in DECISION_COLORS.items():
        if str(decision).lower().startswith(key.lower()): return val
    return ("#66736e","#edf1ee")

def _decision_pill(decision):
    ink,bg=_decision_colors(decision)
    return f'<span class="pill" style="background:{bg};color:{ink}">{_html.escape(str(decision))}</span>'

def _match_mini(score):
    s=max(0.0,min(100.0,float(score or 0)))
    return f'<div class="matchbar"><div class="bar"><i style="width:{s:.0f}%"></i></div><div class="lbl">{s:.0f}%</div></div>'

def _src_row(src):
    title=_html.escape(str(src.get("title",""))[:110]); url=_html.escape(str(src.get("url","")))
    publisher=_html.escape(str(src.get("publisher") or src.get("competitor_domain") or ""))
    date=_html.escape(str(src.get("published_date",""))[:16])
    sub=publisher+(f" · {date}" if date else "")
    return (f'<div class="src-row"><div class="src-main"><a href="{url}" target="_blank">{title}</a>'
            f'<div class="src-sub">{sub}</div></div>{_match_mini(src.get("competitor_match_score",0))}</div>')

def _render_editorial_brief(brief):
    decision=str(brief.get("consiglio_editoriale") or "Da valutare")
    note=str(brief.get("nota_editoriale") or brief.get("perche_adesso") or "")
    title=str(brief.get("titolo_scelto") or brief.get("titolo_consigliato") or "Titolo da definire")
    alternatives=brief.get("titoli_alternativi") or brief.get("varianti_titolo") or []
    meta=str(brief.get("meta_description") or "")
    ink,bg=_decision_colors(decision)
    st.markdown(f'<div class="decision-strip" style="background:{bg};color:{ink}"><b>{_html.escape(decision)}</b>'+(f" — {_html.escape(note)}" if note else "")+'</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="eyebrow-sm">Titolo scelto</div><div class="headline-lg">{_html.escape(title)}<span class="charpill">{len(title)} car</span></div>',unsafe_allow_html=True)
    if brief.get("perche_questo_titolo"): st.caption(str(brief["perche_questo_titolo"]))
    st.markdown(f'<div class="chips" style="margin:10px 0 14px"><span>Timing · {_html.escape(str(brief.get("timing","Da definire")))}</span><span>Formato · {_html.escape(str(brief.get("formato_suggerito","Da definire")))}</span><span>Focus · {_html.escape(str(brief.get("focus_query") or brief.get("target","Da definire")))}</span></div>',unsafe_allow_html=True)
    if meta: st.markdown(f'<div class="eyebrow-sm">Meta description</div><p style="margin:.1rem 0 .9rem;font-size:.94rem">{_html.escape(meta)}<span class="charpill">{len(meta)} car</span></p>',unsafe_allow_html=True)
    bozza=brief.get("bozza_articolo") or []
    if bozza:
        with st.container(key=f"card_bozza_{brief.get('idea_id','x')}"):
            st.markdown('<div class="eyebrow-sm">Bozza pronta per il CMS · scritta solo dai fatti raccolti</div>',unsafe_allow_html=True)
            for paragraph in bozza: st.markdown(str(paragraph))
    else:
        st.caption("La bozza completa del pezzo si genera con il motore «AI con LLM» (barra laterale) dopo la ricerca web: viene scritta solo dai fatti raccolti dalle fonti.")
    if alternatives:
        st.markdown('<div class="eyebrow-sm" style="margin-top:14px">Titoli alternativi</div>'+"".join(f'<div class="alt-title"><span class="n">{i}</span><span>{_html.escape(str(a))}</span><span class="charpill">{len(str(a))} car</span></div>' for i,a in enumerate(alternatives[:5],1)),unsafe_allow_html=True)
    if brief.get("scelte_editoriali"):
        st.markdown('<div class="eyebrow-sm" style="margin-top:14px">Scelte editoriali</div>',unsafe_allow_html=True)
        for value in brief["scelte_editoriali"]: st.markdown(f"- {value}")
    with st.expander("Istruzioni operative per la redazione"):
        st.markdown(f"**Angolo**  \n{brief.get('angolo','Da definire')}")
        st.markdown(f"**Cosa aggiunge rispetto agli altri**  \n{brief.get('differenziazione','Da definire')}")
        for label,key in (("Elementi nuovi da trovare","elementi_nuovi"),("Struttura consigliata","struttura_articolo"),("Fonti e verifiche","fonti_da_verificare"),("Azioni della redazione","azioni_consigliate")):
            values=brief.get(key) or (brief.get("outline") if key=="struttura_articolo" else [])
            if values:
                st.markdown(f"**{label}**")
                for value in values: st.markdown(f"- {value}")
        if brief.get("link_interno"): st.markdown(f"**Link interno suggerito**  \n{brief['link_interno']}")
    if brief.get("rischi_note"): st.warning(f"Rischi e cautele: {brief['rischi_note']}")
    if brief.get("stima_potenziale"): st.caption(f"Stima distribuzione: {brief['stima_potenziale']}")

def _show_table(df):
    """Tabella con formattazione ricca: barre per gli score, CTR in %,
    URL cliccabili. Applica solo le colonne presenti."""
    if df is None or getattr(df,"empty",True): return
    d=df.copy(); cfg={}
    for c in ("ctr","ctr_current","ctr_short","ctr_long"):
        if c in d.columns:
            d[c]=pd.to_numeric(d[c],errors="coerce")*100; cfg[c]=st.column_config.NumberColumn("CTR %",format="%.2f%%")
    if "url" in d.columns: cfg["url"]=st.column_config.LinkColumn("URL",display_text=r"https?://(?:www\.)?([^/]+/.{0,32})")
    if "opportunity_score" in d.columns: cfg["opportunity_score"]=st.column_config.ProgressColumn("Opportunità",min_value=0,max_value=100,format="%.0f")
    if "engagement_score" in d.columns: cfg["engagement_score"]=st.column_config.ProgressColumn("Engagement",min_value=0,max_value=100,format="%.0f")
    if "theme_score" in d.columns: cfg["theme_score"]=st.column_config.ProgressColumn("Forza filone",min_value=0,max_value=100,format="%.0f")
    if "audience_strength" in d.columns: cfg["audience_strength"]=st.column_config.ProgressColumn("Forza audience",min_value=0,max_value=100,format="%.0f")
    if "replication_score" in d.columns: cfg["replication_score"]=st.column_config.ProgressColumn("Replication score",min_value=0,max_value=100,format="%.0f")
    if "pattern_score" in d.columns: cfg["pattern_score"]=st.column_config.ProgressColumn("Forza pattern",min_value=0,max_value=100,format="%.0f")
    if "best_match_score" in d.columns: cfg["best_match_score"]=st.column_config.ProgressColumn("Miglior match",min_value=0,max_value=100,format="%.0f")
    if "prevalence_pct" in d.columns: cfg["prevalence_pct"]=st.column_config.NumberColumn("Nei vincitori",format="%.0f%%")
    if "baseline_pct" in d.columns: cfg["baseline_pct"]=st.column_config.NumberColumn("Nel resto",format="%.0f%%")
    if "lift" in d.columns: cfg["lift"]=st.column_config.NumberColumn("Lift",format="%.2f×")
    if "competitor_match_score" in d.columns: cfg["competitor_match_score"]=st.column_config.ProgressColumn("Match",min_value=0,max_value=100,format="%.0f")
    for c,(lbl,fmt) in {"clicks":("Click","%d"),"clicks_current":("Click","%d"),"impressions":("Impression","%d"),"impressions_current":("Impression","%d"),"growth_pct":("Crescita %","%.0f%%"),"position":("Posizione","%.1f")}.items():
        if c in d.columns: cfg[c]=st.column_config.NumberColumn(lbl,format=fmt)
    for c,(lbl,fmt) in {"pageviews":("Pageview","%d"),"avg_time_seconds":("Tempo medio","%.1fs"),"total_time_seconds":("Engagement totale","%.0fs")}.items():
        if c in d.columns: cfg[c]=st.column_config.NumberColumn(lbl,format=fmt)
    st.dataframe(d,use_container_width=True,column_config=cfg,hide_index=True)

def _run_analysis():
    """Ricalcola vincitori, pattern e shortlist. Nessun bottone: parte da sola."""
    profile,patterns,metric=mine_patterns(st.session_state.analyzed)
    st.session_state.winners_profile=profile; st.session_state.patterns=patterns; st.session_state.perf_metric=metric
    st.session_state.ideas=build_replication_ideas(st.session_state.analyzed,st.session_state.research_df)

DEFAULTS={"analyzed":None,"short_df":None,"long_df":None,"gsc_info":{},"crawl_log":[],"research_df":None,"winners_profile":None,"patterns":None,"perf_metric":"","ideas":None,"briefs":[],"approvals":[],"hermes_notes":[],"mode_label":"Demo CSV"}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v
if "archive_restored" not in st.session_state:
    st.session_state.archive_restored=True
    stored=load_snapshot()
    if stored and st.session_state.analyzed is None:
        st.session_state.short_df=stored["short_df"]
        st.session_state.long_df=stored["long_df"]
        st.session_state.analyzed=stored["analyzed"]
        st.session_state.gsc_info=stored["metadata"]
        st.session_state.mode_label=f"Snapshot locale #{stored['id']}"
        _run_analysis()

with st.sidebar:
    st.markdown("**NEWSROOM OS**")
    st.caption("Configura il contesto una volta. Il lavoro editoriale resta nelle tre schede.")
    st.header("Mandato editoriale")
    client=st.text_input("Cliente / progetto","Agenzia digitale demo")
    context=st.text_area("Target, mercato e tono","Editore italiano; tono autorevole, chiaro e verificabile.")
    goal=st.text_input("Obiettivo","Crescita organica e opportunità editoriali")
    st.header("Fonte dati")
    input_mode=st.radio("Modalità",["Google Search Console API","Export engagement CSV (7 giorni)","Demo CSV"])
    st.header("Motore editoriale")
    brief_mode=st.radio("Motore",["AI con LLM","Regole locali"])
    llm_provider=st.selectbox("LLM",["OpenAI","Anthropic"],disabled=brief_mode=="Regole locali")
    model=st.text_input("Modello (vuoto = predefinito)",disabled=brief_mode=="Regole locali")
    if brief_mode=="AI con LLM" and not os.getenv("OPENAI_API_KEY" if llm_provider=="OpenAI" else "ANTHROPIC_API_KEY"):
        st.warning(f"Nessuna chiave {llm_provider} trovata in .env: la bozza completa non verrà scritta e il pezzo userà le regole locali. Aggiungi la chiave a .env e riavvia.")
    with st.expander("Impostazioni avanzate"):
        research_provider=st.selectbox("Provider ricerca web",["AI (LLM) + Web scraper","Serper + Google News","Web scraper + Google News","Hermes Agent + Web scraper","Google News RSS","RSS personalizzati","Piano locale"],help="AI (LLM) usa match semantico via embeddings; Hermes Agent delega la validazione profonda delle evidenze all'agente locale. Senza API key il sistema torna alle euristiche locali.")
        engagement_loaded=st.session_state.analyzed is not None and "pageviews" in st.session_state.analyzed
        seed_options=(["Top per engagement totale","Alta permanenza","Filoni ricorrenti"] if engagement_loaded else [])+["Top per click (cosa funziona)","Migliori per opportunità","In crescita"]
        seed_strategy=st.selectbox("Contenuti da analizzare",seed_options)
        freshness_label=st.selectbox("Freschezza fonti",["Ultime 24h","Ultimi 7 giorni","Ultimi 30 giorni"],index=1)
        freshness={"Ultime 24h":"1d","Ultimi 7 giorni":"7d","Ultimi 30 giorni":"30d"}[freshness_label]
        include_reddit=st.checkbox("Includi Reddit (best-effort)",value=False)
        min_match=st.slider("Soglia di pertinenza fonti (%)",0,100,35)
        own_domain=st.text_input("Dominio proprio da escludere","affaritaliani.it")
        from src.fresh_research import DEFAULT_RSS_FEEDS
        feeds=st.text_area("Feed RSS, uno per riga","\n".join(DEFAULT_RSS_FEEDS),height=120)
        hermes_command=st.text_input("Comando Hermes","hermes")
        max_crawl=st.slider("URL da approfondire col crawler",1,20,5)
        delay=st.number_input("Pausa tra richieste (s)",0.0,5.0,.2,.1)

def _develop_idea(idea):
    """Trasforma un'idea in brief operativo con coda di approvazione.
    Passa al motore anche gli estratti delle fonti web, così il pezzo
    può essere scritto solo dai fatti raccolti."""
    iid=idea["idea_id"]
    materiale=""
    research=st.session_state.research_df
    if research is not None and not getattr(research,"empty",True) and "source_url" in research.columns:
        ev=research[research.source_url.eq(idea.get("source_url","")) & research.url.fillna("").ne("")]
        if "competitor_match_score" in ev.columns: ev=ev.sort_values("competitor_match_score",ascending=False)
        parts=[]
        for _,r in ev.head(6).iterrows():
            text=str(r.get("scraped_excerpt") or r.get("snippet") or "").strip()[:2400]
            if text: parts.append(f"FONTE: {r.get('title','')} ({r.get('competitor_domain','')}, {r.get('published_date','')})\n{text}")
        base=st.session_state.analyzed
        if base is not None and "paragraph_context" in base.columns:
            own=base.loc[base.url.eq(idea.get("source_url","")),"paragraph_context"]
            own_text=str(own.iloc[0] if len(own) else "").strip()
            if own_text: parts.insert(0,f"IL TUO ARTICOLO CHE HA FUNZIONATO (contesto di background):\n{own_text[:2000]}")
        materiale="\n\n".join(parts)[:12000]
    winners=st.session_state.winners_profile
    winning_titles=""
    if winners is not None and not winners.empty:
        titles=[str(t).strip() for t in winners.title.head(15) if str(t).strip() and len(str(t).split())>2]
        real=[t for t in titles if any(c.isupper() for c in t)]
        winning_titles="\n".join(f"- {t}" for t in (real or titles)[:8])
        if not real: winning_titles+="\n(Nota: sono slug di URL, non titoli reali: deducine i temi, ma modella lo stile del titolo sui veri titoli di quotidiano presenti in materiale_fonti.)"
    idea={**idea,"materiale_fonti":materiale,"titoli_vincenti":winning_titles}
    row={**idea,"url":idea.get("source_url",""),"topic":idea.get("theme",""),"title":idea.get("source_title",""),"keywords":idea.get("entities",""),"status":idea.get("editorial_decision",""),"winning_cluster":f"{idea.get('theme','')} · {idea.get('hook','')}","winning_hook":idea.get("hook",""),"recommended_format":idea.get("format",""),"editorial_advice":idea.get("replication_advice",""),"proposed_argument":f"Replicare il pattern vincente ({idea.get('title_recipe','')}) su uno sviluppo nuovo dello stesso interesse.","discover_potential":idea.get("replication_score",0),"opportunity_score":idea.get("replication_score",0),"fresh_research_summary":idea.get("comparable_titles","") or idea.get("differentiation","")}
    brief,error=generate_brief(row,brief_mode,llm_provider,model,context,goal)
    brief.update({"source_url":row["url"],"idea_id":iid,"replication_score":idea.get("replication_score",0),"origin_cluster":row["winning_cluster"],"origin_pattern":idea.get("title_recipe",""),"stato_produzione":"In revisione","owner":"Da assegnare","deadline":"","published_url":""})
    st.session_state.briefs=[b for b in st.session_state.briefs if b.get("idea_id")!=iid]+[brief]
    st.session_state.approvals=[a for a in st.session_state.approvals if a.get("idea_id")!=iid]+[{**a,"source_url":row["url"],"idea_id":iid} for a in propose_actions(brief,row)]
    return error

NAV_TABS=["01 · Cosa ha funzionato","02 · Cosa pubblicare","03 · Pubblica subito"]
_goto=st.session_state.pop("_goto_tab",None)
if _goto in NAV_TABS: st.session_state.navtabs=_goto
nav=st.radio("Fase del workflow",NAV_TABS,horizontal=True,key="navtabs",label_visibility="collapsed")

if nav==NAV_TABS[0]:
    st.caption("STEP 01 · LA DIAGNOSI DEL MATTINO")
    st.subheader("Cosa ha funzionato — e cosa vale la pena ripetere")
    if input_mode=="Demo CSV":
        st.info("Dataset dimostrativo incluso: periodo corrente di 3 giorni e baseline di 7 giorni.")
        if st.button("Carica e analizza demo",type="primary"):
            st.session_state.short_df=pd.read_csv("sample_short_3d.csv"); st.session_state.long_df=pd.read_csv("sample_long_7d.csv")
            st.session_state.analyzed=analyze_comparison(st.session_state.short_df,st.session_state.long_df,3,7); st.session_state.mode_label=input_mode
            st.session_state.research_df=None; _run_analysis()
    elif input_mode=="Export engagement CSV (7 giorni)":
        st.info("Carica un CSV con URL, pageview, tempo totale, tempo medio per view e flag. I nomi colonna comuni e gli export generici a 5 colonne vengono riconosciuti automaticamente.")
        engagement_upload=st.file_uploader("CSV pageview / engagement",type=["csv"],key="engagement_csv")
        if st.button("Carica e analizza",type="primary",disabled=engagement_upload is None):
            try:
                raw_engagement=read_csv(engagement_upload)
                analyzed_engagement=analyze_engagement_export(raw_engagement)
                if analyzed_engagement.empty: st.warning("Il file non contiene URL analizzabili.")
                else:
                    st.session_state.short_df=raw_engagement; st.session_state.long_df=None
                    st.session_state.analyzed=analyzed_engagement; st.session_state.mode_label=input_mode
                    st.session_state.research_df=None; _run_analysis()
                    st.success(f"Analizzati {len(analyzed_engagement)} articoli: vincitori e pattern sono pronti qui sotto.")
            except Exception as exc: st.error(f"Impossibile leggere l'export engagement: {exc}")
    else:
        cfg="gsc_config.yaml"
        range_days=st.number_input("Periodo Discover corrente (giorni)",min_value=7,max_value=480,value=90,step=1,help="Confrontato con il periodo precedente della stessa durata.")
        local_config_exists=Path(cfg).exists()
        cloud_secrets_ready=False
        if not local_config_exists:
            try: cloud_secrets_ready="gsc" in st.secrets and "google_oauth" in st.secrets
            except Exception: cloud_secrets_ready=False
        if local_config_exists: st.info("Configurazione locale rilevata. Il token OAuth verrà riutilizzato automaticamente.")
        elif cloud_secrets_ready: st.success("Configurazione GSC caricata in modo sicuro da Streamlit Secrets.")
        else: st.warning("Configurazione GSC assente. In Streamlit Cloud aggiungi le sezioni [gsc] e [google_oauth] nei Secrets dell'app; non caricare credenziali su GitHub.")
        if st.button("Scarica e analizza da GSC",type="primary",disabled=not local_config_exists and not cloud_secrets_ready):
            try:
                from src.gsc_api import load_config,fetch_gsc,get_credentials
                if local_config_exists:
                    conf=load_config(cfg)
                else:
                    gsc_secret=dict(st.secrets["gsc"]); oauth_secret=dict(st.secrets["google_oauth"])
                    gsc_secret.pop("short_days",None); gsc_secret.pop("long_days",None); gsc_secret.pop("range_days",None); gsc_secret["authorized_user_info"]=oauth_secret
                    conf={"gsc":gsc_secret}
                credentials=get_credentials(conf)
                current_days=int(range_days)
                short,info1=fetch_gsc(conf,current_days,credentials=credentials)
                baseline_end=date.fromisoformat(info1["start"])-timedelta(days=1)
                long,info2=fetch_gsc(conf,current_days,end_date=baseline_end,credentials=credentials)
                if short.empty: st.warning("GSC non ha restituito righe per il periodo selezionato.")
                else:
                    st.session_state.short_df=short; st.session_state.long_df=long; st.session_state.gsc_info={"current":info1,"baseline":info2}; st.session_state.analyzed=analyze_comparison(short,long,current_days,current_days)
                    st.session_state.research_df=None; _run_analysis()
                    snapshot_id=save_snapshot(st.session_state.analyzed,short,long,f"GSC Discover {current_days}g {info1['start']} → {info1['end']}",st.session_state.gsc_info)
                    st.success(f"Dati salvati nell'archivio locale (snapshot #{snapshot_id}). Vincitori e pattern sono pronti qui sotto.")
            except Exception as e: st.error(f"Impossibile scaricare i dati GSC: {e}")
    analyzed=st.session_state.analyzed
    if analyzed is None: st.info("Carica una fonte dati per avviare la diagnosi.")
    else:
        if "pageviews" in analyzed:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Articoli",len(analyzed)); c2.metric("Pageview",f"{int(analyzed.pageviews.sum()):,}")
            c3.metric("Tempo medio / view",f"{analyzed.avg_time_seconds.mean():.1f}s")
            c4.metric("Engagement totale",f"{int(analyzed.total_time_seconds.sum()/3600):,}h")
            themes=summarize_editorial_themes(analyzed)
            if not themes.empty:
                with st.expander("Filoni editoriali ricorrenti"): _show_table(themes)
        else:
            c1,c2,c3=st.columns(3); c1.metric("URL",len(analyzed)); c2.metric("Impression correnti",int(analyzed.impressions_current.sum())); c3.metric("Click correnti",int(analyzed.clicks_current.sum()))
        profile=st.session_state.winners_profile; patterns=st.session_state.patterns
        if profile is None: _run_analysis(); profile=st.session_state.winners_profile; patterns=st.session_state.patterns
        if profile is not None and not profile.empty:
            d1,d2,d3=st.columns(3)
            d1.metric("Vincitori analizzati",len(profile))
            d2.metric("Pattern ricorrenti",0 if patterns is None or patterns.empty else len(patterns))
            d3.metric("Metrica di successo",{"ctr_current":"CTR Discover","clicks_current":"Click Discover","engagement_score":"Engagement","opportunity_score":"Opportunità"}.get(st.session_state.perf_metric,st.session_state.perf_metric))
            if st.session_state.perf_metric=="ctr_current": st.caption("Vincitori = CTR più alto tra le pagine sopra la mediana di impression: un CTR alto su poche impression non è un successo replicabile.")
            if patterns is not None and not patterns.empty:
                st.subheader("Il verdetto: cosa si ripete nei contenuti vincenti")
                for _,p in patterns.head(6).iterrows():
                    st.markdown(f"**{p.pattern_type} · {p.pattern} · {p.pattern_score:.0f}/100**  \nPresente nel {p.prevalence_pct:.0f}% dei vincitori (resto del sito: {p.baseline_pct:.0f}%, lift {p.lift:.1f}×).  \n_Esempi: {p.examples}_")
            else:
                st.info("Nessun tratto ricorre in almeno 2 vincitori: servono più articoli nella finestra oppure il crawler qui sotto per usare i titoli reali.")
            with st.expander("Tutti i pattern con prevalenza, lift ed esempi"): _show_table(patterns)
            with st.expander("Profilo editoriale dei singoli vincitori"):
                prof_view=profile.copy()
                prof_view["title_patterns"]=prof_view.title_patterns.map(lambda v:" · ".join(v))
                prof_view["structure_patterns"]=prof_view.structure_patterns.map(lambda v:" · ".join(v))
                _show_table(prof_view)
            with st.expander("Tutte le performance della finestra"): _show_table(analyzed)
        if st.button("Approfondisci i vincitori con il crawler"):
            with st.spinner("Crawler in esecuzione: titoli reali, meta e attacco..."):
                enriched,logs=enrich_analyzed_dataframe(analyzed,max_crawl,delay); st.session_state.analyzed=enriched; st.session_state.crawl_log=logs
                _run_analysis()
            st.success("Arricchimento completato: pattern ricalcolati con i titoli reali.")
        if st.session_state.crawl_log:
            with st.expander("Log del crawler"): st.dataframe(pd.DataFrame(st.session_state.crawl_log),use_container_width=True)

def _render_dossier(item,adjacent,briefed):
    """Un dossier per opportunità: da cosa nasce, cosa esce sul web, la proposta."""
    iid=item.idea_id
    with st.container(key=f"card_dossier_{iid}"):
        head_l,head_r=st.columns([4,1.5],vertical_alignment="center")
        head_l.markdown(f'<div class="eyebrow-sm">Da cosa nasce</div><p class="win-ref">{_html.escape(str(item.source_title)[:110])}</p>',unsafe_allow_html=True)
        head_r.markdown(f'<div style="text-align:right">{_decision_pill(item.editorial_decision)}</div>',unsafe_allow_html=True)
        if len(adjacent):
            st.markdown('<div class="eyebrow-sm" style="margin-top:8px">Cosa sta uscendo sul web</div>'+"".join(_src_row(src) for _,src in adjacent.iterrows()),unsafe_allow_html=True)
        else:
            ev=int(item.evidence_count or 0)
            if ev: st.caption(f"{ev} coperture trovate ma sotto la soglia di pertinenza ({min_match}%): abbassala nelle impostazioni avanzate per vederle.")
            else: st.caption("Nessuna copertura adiacente trovata: interesse da monitorare, non forzare l'uscita.")
        st.markdown(f'<div class="eyebrow-sm" style="margin-top:12px">La proposta</div><div class="headline-lg">{_html.escape(str(item.recommended_headline))}</div><p class="advice">{_html.escape(str(item.replication_advice))}</p>',unsafe_allow_html=True)
        foot_l,foot_r=st.columns([2.6,1.3],vertical_alignment="center")
        foot_l.markdown(f'<div class="chips"><span>Quando · {_html.escape(str(item.urgency))}</span><span>{int(item.evidence_count or 0)} fonti web</span><span>Priorità {float(item.replication_score or 0):.0f}</span></div>',unsafe_allow_html=True)
        if foot_r.button("Aggiorna il pezzo" if iid in briefed else "Sviluppa il pezzo",key=f"dev_{iid}",type="primary" if str(item.editorial_decision)=="Pubblica ora" else "secondary",use_container_width=True):
            with st.spinner("Scrivo il pezzo dai fatti raccolti..."):
                error=_develop_idea(item.to_dict())
            if error: st.session_state["_dev_note"]=error
            st.session_state["_goto_tab"]="03 · Pubblica subito"
            st.rerun()
        if iid in briefed: st.caption("Pezzo già creato: lo trovi nella scheda 03 · Pubblica subito.")

if nav==NAV_TABS[1]:
    st.caption("STEP 02 · LA SCHERMATA DEL MATTINO")
    st.subheader("Cosa pubblicare oggi")
    if st.session_state.analyzed is None: st.info("Prima carica i dati nella scheda 01.")
    else:
        if st.session_state.ideas is None: _run_analysis()
        provider=research_provider
        use_hermes=provider=="Hermes Agent + Web scraper"
        use_llm=provider=="AI (LLM) + Web scraper"
        use_serper=provider=="Serper + Google News"
        if provider in ("Hermes Agent + Web scraper","AI (LLM) + Web scraper","Google News RSS","Serper + Google News"): provider="Web scraper + Google News"
        if use_hermes:
            from src.fresh_research import hermes_available
            if not hermes_available(hermes_command): st.caption("Hermes Agent non trovato nel PATH: la ricerca funzionerà comunque con lo scoring locale.")
        winners=st.session_state.winners_profile
        top25=winners.head(25) if winners is not None and not winners.empty else None
        AUTO_SEED="__auto__"
        seed_labels={AUTO_SEED:"I migliori 5 (automatico)"}
        if top25 is not None:
            for _,w in top25.iterrows():
                value=f"{w.performance*100:.1f}% CTR" if st.session_state.perf_metric=="ctr_current" else f"{int(w.performance)} {'click' if st.session_state.perf_metric=='clicks_current' else 'punti'}"
                seed_labels[w.url]=f"{str(w.title)[:80]} · {value}"
        ctrl_l,ctrl_r=st.columns([3,1.25],vertical_alignment="bottom")
        selected_seed=ctrl_l.selectbox("Parti da un articolo che ha funzionato (top 25)",list(seed_labels),format_func=lambda v: seed_labels.get(v,v),help="Il sistema naviga Google News, i siti dei competitor e i feed di settore, legge le pagine e trova contenuti adiacenti: stesso interesse del pubblico, sviluppo nuovo.")
        if ctrl_r.button("Cerca sul web",type="primary",use_container_width=True):
            with st.status("Navigo il web alla ricerca di contenuti adiacenti...",expanded=False) as _status:
                def _progress(done,total,label): _status.update(label=f"({done}/{total}) Cerco e leggo le coperture adiacenti a «{label}»...")
                base=st.session_state.analyzed
                if selected_seed==AUTO_SEED:
                    target=base[base.url.isin(top25.head(5).url)] if top25 is not None else base
                else:
                    target=base[base.url.eq(selected_seed)]
                research,_,notes=add_research_to_dataframe(target,provider,own_domain,[x for x in feeds.splitlines() if x.strip()],max_topics=5 if selected_seed==AUTO_SEED else 1,audience_context=context,use_hermes=use_hermes,hermes_command=hermes_command,use_llm=use_llm,llm_provider=llm_provider,llm_model=model,seed_strategy=seed_strategy,freshness=freshness,include_reddit=include_reddit,serper_api_key=os.getenv("SERPER_API_KEY","") if use_serper else "",progress=_progress)
                old=st.session_state.research_df
                if old is not None and not getattr(old,"empty",True) and "source_url" in research and "source_url" in old:
                    research=pd.concat([old[~old.source_url.isin(research.source_url.unique())],research],ignore_index=True)
                research=annotate_comparables(research,st.session_state.winners_profile)
                st.session_state.research_df=research; st.session_state.hermes_notes=notes
                st.session_state.ideas=build_replication_ideas(st.session_state.analyzed,research)
                found=len(research[research.url.fillna("").ne("")]) if research is not None and not research.empty and "url" in research else 0
                _status.update(label=f"Fatto: {found} contenuti adiacenti in archivio per questa sessione.",state="complete")
        ideas=st.session_state.ideas
        research=st.session_state.research_df
        briefed={b.get("idea_id") for b in st.session_state.briefs}
        if research is None:
            with st.container(key="card_empty02"):
                st.markdown('<div style="text-align:center;padding:30px 18px 34px"><div class="eyebrow-sm">La schermata del mattino parte da qui</div>'
                            '<div class="headline-lg" style="max-width:520px;margin:6px auto 8px">Scegli un articolo che ha funzionato e lancia la ricerca.</div>'
                            '<p style="color:#66736e;max-width:520px;margin:0 auto;font-size:.92rem;line-height:1.6">Il sistema naviga il web, legge le pagine e ti riporta i contenuti adiacenti già in uscita: per ogni articolo vincente ricevi le fonti trovate e una proposta pronta da sviluppare.</p></div>',unsafe_allow_html=True)
            if ideas is not None and not ideas.empty:
                with st.expander("Proposte preliminari basate solo sui tuoi dati (senza validazione web)"):
                    for _,item in ideas.head(3).iterrows(): st.markdown(_idea_card(item),unsafe_allow_html=True)
        elif ideas is not None and not ideas.empty:
            real=research[research.url.fillna("").ne("")] if "url" in research else research.iloc[0:0]
            if "competitor_match_score" in real.columns: real=real[pd.to_numeric(real.competitor_match_score,errors="coerce").fillna(0).ge(min_match)]
            ready=int(ideas.editorial_decision.isin(["Pubblica ora","Prepara e valida"]).sum())
            window_label={"1d":"24h","7d":"7 giorni","30d":"30 giorni"}.get(freshness,freshness)
            st.markdown(f'<div class="stat-strip"><span><b>{len(real)}</b>contenuti adiacenti</span><span><b>{ready}</b>proposte pronte</span><span><b>{window_label}</b>finestra fonti</span></div>',unsafe_allow_html=True)
            researched=set(research[research.url.fillna("").ne("")].source_url.unique()) if "source_url" in research.columns and "url" in research.columns else set()
            groups=ideas[ideas.source_url.isin(researched)] if researched else ideas.head(5)
            if researched and groups.empty: groups=ideas.head(5)
            for _,item in groups.head(8).iterrows():
                adjacent=real[real.source_url.eq(item.source_url)].head(3) if "source_url" in real.columns else real.iloc[0:0]
                _render_dossier(item,adjacent,briefed)
            with st.expander("Dettaglio completo per analisti"):
                st.markdown("**Tutte le idee con lo scoring trasparente** — priorità = performance del vincitore + fonti web + forza dei pattern.")
                _show_table(ideas)
                st.markdown(f"**Tutte le fonti web sopra la soglia di pertinenza ({min_match}%)**")
                cols=[c for c in ("source_url","title","publisher","competitor_domain","competitor_match_score","shared_patterns","angle","published_date","url") if c in real.columns]
                _show_table(real[cols] if cols else real)
            for note in st.session_state.hermes_notes:
                result=note.get("result")
                if isinstance(result,str): st.caption(result)
                elif isinstance(result,dict) and result.get("suggestions"):
                    st.subheader("Raccomandazioni AI (LLM / Hermes)")
                    for suggestion in result["suggestions"]:
                        urls=suggestion.get("source_urls") or []
                        st.markdown(_suggestion_card({"article_suggestion":suggestion.get("title","Idea AI"),"audience_reason":suggestion.get("audience_reason",""),"recommended_format":suggestion.get("format",""),"angle":suggestion.get("angle",""),"url":urls[0] if isinstance(urls,list) and urls else "","competitor_match_score":0}),unsafe_allow_html=True)
        else: st.info("Nessuna proposta generata: servono più segnali nella scheda 01.")

if nav==NAV_TABS[2]:
    st.caption("STEP 03 · PUBBLICA SUBITO")
    st.subheader("Il pezzo pronto per il CMS")
    _dev_note=st.session_state.pop("_dev_note",None)
    if _dev_note: st.warning(_dev_note)
    if not st.session_state.briefs:
        with st.container(key="card_empty03"):
            st.markdown('<div style="text-align:center;padding:30px 18px 34px"><div class="eyebrow-sm">Nessun pezzo ancora</div>'
                        '<div class="headline-lg" style="max-width:520px;margin:6px auto 8px">Sviluppa una proposta nella scheda 02.</div>'
                        '<p style="color:#66736e;max-width:520px;margin:0 auto;font-size:.92rem;line-height:1.6">Qui troverai il pezzo completo: titolo scelto in caratteri contati, bozza scritta solo dai fatti raccolti, scelte editoriali motivate e la scheda di produzione con approvazioni ed export.</p></div>',unsafe_allow_html=True)
    else:
        publish_ok={a.get("idea_id") for a in st.session_state.approvals if str(a.get("azione","")).startswith("Pubblicare") and a.get("stato") in ("Approva","Auto-approvata")}
        for b in st.session_state.briefs:
            if b.get("idea_id") in publish_ok and b.get("stato_produzione")=="In revisione": b["stato_produzione"]="Approvato"
        states=["In revisione","Approvato","Assegnato","Pubblicato","Archiviato"]
        briefs=list(reversed(st.session_state.briefs))
        approved=sum(b.get("stato_produzione") in ("Approvato","Assegnato","Pubblicato") for b in briefs)
        published=sum(b.get("stato_produzione")=="Pubblicato" for b in briefs)
        st.markdown(f'<div class="stat-strip"><span><b>{len(briefs)}</b>pezzi attivi</span><span><b>{approved}</b>approvati</span><span><b>{published}</b>pubblicati</span></div>',unsafe_allow_html=True)
        if len(briefs)>1:
            pick_labels={b.get("idea_id",str(i)): f"{b.get('stato_produzione','In revisione')} — {(b.get('titolo_scelto') or b.get('titolo_consigliato') or f'Pezzo {i+1}')[:46]}" for i,b in enumerate(briefs)}
            picked=st.radio("Pezzo",list(pick_labels),format_func=lambda k: pick_labels[k],horizontal=True,label_visibility="collapsed")
            b=next(x for x in briefs if x.get("idea_id")==picked)
        else: b=briefs[0]
        iid=b.get("idea_id","brief0")
        title=str(b.get("titolo_scelto") or b.get("titolo_consigliato") or "Titolo da definire")
        meta=str(b.get("meta_description") or "")
        main,side=st.columns([2.15,1],gap="large")
        with main:
            _render_editorial_brief(b)
        with side:
            st.markdown('<div class="eyebrow-sm">Scheda di produzione</div>',unsafe_allow_html=True)
            with st.container(key=f"card_prod_{iid}"):
                b["stato_produzione"]=st.selectbox("Stato",states,index=states.index(b.get("stato_produzione","In revisione")),key=f"stato_{iid}")
                b["owner"]=st.text_input("Owner",b.get("owner","Da assegnare"),key=f"owner_{iid}")
                b["deadline"]=st.text_input("Deadline",b.get("deadline",""),placeholder="YYYY-MM-DD",key=f"deadline_{iid}")
                b["published_url"]=st.text_input("URL pubblicato",b.get("published_url",""),key=f"purl_{iid}")
            approvals=[a for a in st.session_state.approvals if a.get("idea_id")==iid]
            if approvals:
                st.markdown('<div class="eyebrow-sm" style="margin-top:14px">Approvazioni</div>',unsafe_allow_html=True)
                with st.container(key=f"card_appr_{iid}"):
                    opts=["In attesa","Approva","Modifica","Rifiuta","Auto-approvata"]
                    for j,a in enumerate(approvals):
                        st.markdown(f'{a["azione"]}  \n<span style="font-size:.78rem;color:#79857f">{a["motivo"]} · Rischio {a["rischio"].lower()} · {a["responsabile"]}</span>',unsafe_allow_html=True)
                        a["stato"]=st.selectbox("Stato",opts,index=opts.index(a["stato"]),key=f"appr_{iid}_{j}",label_visibility="collapsed")
            st.markdown('<div class="eyebrow-sm" style="margin-top:14px">Title e meta per il CMS</div>',unsafe_allow_html=True)
            st.code(f"Title ({len(title)} car):\n{title}\n\nMeta description ({len(meta)} car):\n{meta or 'Da definire'}",language=None)
            st.markdown('<div class="eyebrow-sm" style="margin-top:14px">Consegna</div>',unsafe_allow_html=True)
            md=generate_markdown_report(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,client)
            workflow=generate_json_export(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,st.session_state.approvals,{"client":client,"mode":st.session_state.mode_label,"winning_patterns":[] if st.session_state.patterns is None else st.session_state.patterns.to_dict("records"),"replication_ideas":[] if st.session_state.ideas is None else st.session_state.ideas.to_dict("records")})
            st.download_button("Report Markdown",md,"report_ai_content.md","text/markdown",use_container_width=True)
            if st.session_state.analyzed is not None: st.download_button("CSV analizzato",st.session_state.analyzed.to_csv(index=False).encode("utf-8-sig"),"contenuti_analizzati.csv","text/csv",use_container_width=True)
            st.download_button("Workflow JSON",workflow,"workflow.json","application/json",use_container_width=True)
            if st.session_state.research_df is not None: st.download_button("Ricerca competitor CSV",st.session_state.research_df.to_csv(index=False).encode("utf-8-sig"),"ricerca_competitor.csv","text/csv",use_container_width=True)
        with st.expander("Report completo"): st.markdown(md)
