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

def _render_editorial_brief(brief):
    decision=str(brief.get("consiglio_editoriale") or "Da valutare")
    note=str(brief.get("nota_editoriale") or brief.get("perche_adesso") or "")
    title=str(brief.get("titolo_scelto") or brief.get("titolo_consigliato") or "Titolo da definire")
    alternatives=brief.get("titoli_alternativi") or brief.get("varianti_titolo") or []
    meta=str(brief.get("meta_description") or "")
    st.markdown(f"### {decision}")
    if note: st.info(note)
    st.markdown(f"**Titolo scelto · {len(title)} caratteri**\n\n{title}")
    if brief.get("perche_questo_titolo"): st.caption(str(brief["perche_questo_titolo"]))
    if alternatives:
        st.markdown("**Alternative di titolo**")
        for index,alternative in enumerate(alternatives[:5],1):
            alternative=str(alternative)
            st.markdown(f"{index}. {alternative} · `{len(alternative)} caratteri`")
    if meta: st.markdown(f"**Meta description · {len(meta)} caratteri**\n\n{meta}")
    c1,c2,c3=st.columns(3)
    c1.markdown(f"**Timing**\n\n{brief.get('timing','Da definire')}")
    c2.markdown(f"**Formato**\n\n{brief.get('formato_suggerito','Da definire')}")
    c3.markdown(f"**Focus**\n\n{brief.get('focus_query') or brief.get('target','Da definire')}")
    st.markdown(f"**Angolo editoriale**\n\n{brief.get('angolo','Da definire')}")
    st.markdown(f"**Cosa aggiunge rispetto agli altri**\n\n{brief.get('differenziazione','Da definire')}")
    sections=[("Elementi nuovi da trovare","elementi_nuovi"),("Struttura consigliata","struttura_articolo"),("Fonti e verifiche","fonti_da_verificare"),("Azioni della redazione","azioni_consigliate")]
    for label,key in sections:
        values=brief.get(key) or (brief.get("outline") if key=="struttura_articolo" else [])
        if values:
            st.markdown(f"**{label}**")
            for value in values: st.markdown(f"- {value}")
    if brief.get("link_interno"): st.markdown(f"**Link interno suggerito**\n\n{brief['link_interno']}")
    if brief.get("rischi_note"): st.warning(f"Rischi e cautele: {brief['rischi_note']}")

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
    """Trasforma un'idea in brief operativo con coda di approvazione."""
    iid=idea["idea_id"]
    row={**idea,"url":idea.get("source_url",""),"topic":idea.get("theme",""),"title":idea.get("source_title",""),"keywords":idea.get("entities",""),"status":idea.get("editorial_decision",""),"winning_cluster":f"{idea.get('theme','')} · {idea.get('hook','')}","winning_hook":idea.get("hook",""),"recommended_format":idea.get("format",""),"editorial_advice":idea.get("replication_advice",""),"proposed_argument":f"Replicare il pattern vincente ({idea.get('title_recipe','')}) su uno sviluppo nuovo dello stesso interesse.","discover_potential":idea.get("replication_score",0),"opportunity_score":idea.get("replication_score",0),"fresh_research_summary":idea.get("comparable_titles","") or idea.get("differentiation","")}
    brief,error=generate_brief(row,brief_mode,llm_provider,model,context,goal)
    brief.update({"source_url":row["url"],"idea_id":iid,"replication_score":idea.get("replication_score",0),"origin_cluster":row["winning_cluster"],"origin_pattern":idea.get("title_recipe",""),"stato_produzione":"In revisione","owner":"Da assegnare","deadline":"","published_url":""})
    st.session_state.briefs=[b for b in st.session_state.briefs if b.get("idea_id")!=iid]+[brief]
    st.session_state.approvals=[a for a in st.session_state.approvals if a.get("idea_id")!=iid]+[{**a,"source_url":row["url"],"idea_id":iid} for a in propose_actions(brief,row)]
    return error

tabs=st.tabs(["01  Cosa ha funzionato","02  Cosa pubblicare","03  Brief e consegna"])

with tabs[0]:
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
            d3.metric("Metrica di successo",{"clicks_current":"Click Discover","engagement_score":"Engagement","opportunity_score":"Opportunità"}.get(st.session_state.perf_metric,st.session_state.perf_metric))
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

def _develop_button(item,briefed):
    c1,c2=st.columns([1,4])
    label="Aggiorna brief" if item.idea_id in briefed else "Sviluppa il brief"
    if c1.button(label,key=f"dev_{item.idea_id}"):
        error=_develop_idea(item.to_dict())
        if error: st.warning(error)
        else: st.success("Brief pronto nella scheda 03.")
    if item.idea_id in briefed: c2.caption("Brief già creato: lo trovi nella scheda 03 · Brief e consegna.")

with tabs[1]:
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
        st.markdown("Il sistema naviga il web — Google News, i siti dei competitor, i feed di settore — legge le pagine e trova **contenuti adiacenti** agli articoli che hanno già generato traffico: stesso interesse del pubblico, sviluppo nuovo.")
        if use_hermes:
            from src.fresh_research import hermes_available
            if not hermes_available(hermes_command): st.caption("Hermes Agent non trovato nel PATH: la ricerca funzionerà comunque con lo scoring locale.")
        if st.button("Cerca sul web i contenuti adiacenti",type="primary"):
            with st.status("Navigo il web alla ricerca di contenuti adiacenti...",expanded=False) as _status:
                def _progress(done,total,label): _status.update(label=f"({done}/{total}) Cerco e leggo le coperture adiacenti a «{label}»...")
                research,enriched,notes=add_research_to_dataframe(st.session_state.analyzed,provider,own_domain,[x for x in feeds.splitlines() if x.strip()],audience_context=context,use_hermes=use_hermes,hermes_command=hermes_command,use_llm=use_llm,llm_provider=llm_provider,llm_model=model,seed_strategy=seed_strategy,freshness=freshness,include_reddit=include_reddit,serper_api_key=os.getenv("SERPER_API_KEY","") if use_serper else "",progress=_progress)
                research=annotate_comparables(research,st.session_state.winners_profile)
                st.session_state.research_df=research; st.session_state.analyzed=enriched; st.session_state.hermes_notes=notes
                st.session_state.ideas=build_replication_ideas(enriched,research)
                found=len(research[research.url.fillna("").ne("")]) if research is not None and not research.empty and "url" in research else 0
                _status.update(label=f"Fatto: {found} contenuti adiacenti trovati e letti.",state="complete")
        ideas=st.session_state.ideas
        research=st.session_state.research_df
        briefed={b.get("idea_id") for b in st.session_state.briefs}
        if research is None:
            if ideas is not None and not ideas.empty:
                st.caption("In attesa della ricerca web, queste sono le prime proposte basate solo sui tuoi dati.")
                for _,item in ideas.head(3).iterrows():
                    st.markdown(_idea_card(item),unsafe_allow_html=True)
                    _develop_button(item,briefed)
        elif ideas is not None and not ideas.empty:
            real=research[research.url.fillna("").ne("")] if "url" in research else research.iloc[0:0]
            if "competitor_match_score" in real.columns: real=real[pd.to_numeric(real.competitor_match_score,errors="coerce").fillna(0).ge(min_match)]
            ready=int(ideas.editorial_decision.isin(["Pubblica ora","Prepara e valida"]).sum())
            m1,m2,m3=st.columns(3)
            m1.metric("Contenuti adiacenti trovati",len(real)); m2.metric("Proposte pronte",ready); m3.metric("Finestra fonti",freshness_label)
            for _,item in ideas.head(5).iterrows():
                st.markdown("---")
                st.markdown(f"**Ha funzionato da te** · {item.source_title}")
                adjacent=real[real.source_url.eq(item.source_url)].head(3) if "source_url" in real.columns else real.iloc[0:0]
                if len(adjacent):
                    st.markdown("**Cosa sta uscendo di adiacente sul web**")
                    for _,src in adjacent.iterrows():
                        publisher=str(src.get("publisher") or src.get("competitor_domain") or "")
                        st.markdown(f"- [{src.title}]({src.url}) — {publisher} · pertinenza {float(src.competitor_match_score or 0):.0f}%")
                else:
                    ev=int(item.evidence_count or 0)
                    if ev: st.caption(f"{ev} coperture trovate ma sotto la soglia di pertinenza ({min_match}%): abbassala nelle impostazioni avanzate per vederle.")
                    else: st.caption("Nessuna copertura adiacente trovata: interesse da monitorare, non forzare l'uscita.")
                st.markdown(_idea_card(item),unsafe_allow_html=True)
                _develop_button(item,briefed)
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

with tabs[2]:
    st.caption("STEP 03 · DAL BRIEF ALLA REDAZIONE")
    st.subheader("Brief operativi, approvazioni e consegna")
    if not st.session_state.briefs: st.info("Sviluppa un'idea nella scheda 02: il brief completo apparirà qui.")
    else:
        publish_ok={a.get("idea_id") for a in st.session_state.approvals if str(a.get("azione","")).startswith("Pubblicare") and a.get("stato") in ("Approva","Auto-approvata")}
        for b in st.session_state.briefs:
            if b.get("idea_id") in publish_ok and b.get("stato_produzione")=="In revisione": b["stato_produzione"]="Approvato"
        states=["In revisione","Approvato","Assegnato","Pubblicato","Archiviato"]
        s1,s2,s3=st.columns(3)
        s1.metric("Brief attivi",len(st.session_state.briefs))
        s2.metric("Approvati",sum(b.get("stato_produzione") in ("Approvato","Assegnato","Pubblicato") for b in st.session_state.briefs))
        s3.metric("Pubblicati",sum(b.get("stato_produzione")=="Pubblicato" for b in st.session_state.briefs))
        for i,b in enumerate(reversed(st.session_state.briefs)):
            iid=b.get("idea_id",f"brief{i}")
            title=b.get("titolo_scelto") or b.get("titolo_consigliato") or f"Brief {i+1}"
            with st.expander(f"{b.get('stato_produzione','In revisione')} · {title}",expanded=i==0):
                _render_editorial_brief(b)
                st.markdown("---")
                c1,c2,c3,c4=st.columns(4)
                b["stato_produzione"]=c1.selectbox("Stato",states,index=states.index(b.get("stato_produzione","In revisione")),key=f"stato_{iid}")
                b["owner"]=c2.text_input("Owner",b.get("owner","Da assegnare"),key=f"owner_{iid}")
                b["deadline"]=c3.text_input("Deadline",b.get("deadline",""),placeholder="YYYY-MM-DD",key=f"deadline_{iid}")
                b["published_url"]=c4.text_input("URL pubblicato",b.get("published_url",""),key=f"purl_{iid}")
                approvals=[a for a in st.session_state.approvals if a.get("idea_id")==iid]
                if approvals:
                    st.markdown("**Decisioni da prendere**")
                    for j,a in enumerate(approvals):
                        a1,a2,a3=st.columns([4,1,2])
                        a1.markdown(f"**{a['azione']}**  \n{a['motivo']} — Responsabile: {a['responsabile']}"); a2.write(f"Rischio: {a['rischio']}")
                        opts=["In attesa","Approva","Modifica","Rifiuta","Auto-approvata"]
                        a["stato"]=a3.selectbox("Stato",opts,index=opts.index(a["stato"]),key=f"appr_{iid}_{j}",label_visibility="collapsed")
        st.subheader("Consegna ed export")
        md=generate_markdown_report(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,client)
        workflow=generate_json_export(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,st.session_state.approvals,{"client":client,"mode":st.session_state.mode_label,"winning_patterns":[] if st.session_state.patterns is None else st.session_state.patterns.to_dict("records"),"replication_ideas":[] if st.session_state.ideas is None else st.session_state.ideas.to_dict("records")})
        c1,c2,c3=st.columns(3); c1.download_button("Scarica report Markdown",md,"report_ai_content.md","text/markdown"); c2.download_button("Scarica CSV analizzato",st.session_state.analyzed.to_csv(index=False).encode("utf-8-sig"),"contenuti_analizzati.csv","text/csv") if st.session_state.analyzed is not None else None; c3.download_button("Scarica workflow JSON",workflow,"workflow.json","application/json")
        if st.session_state.research_df is not None: st.download_button("Scarica ricerca competitor CSV",st.session_state.research_df.to_csv(index=False).encode("utf-8-sig"),"ricerca_competitor.csv","text/csv")
        with st.expander("Report completo"): st.markdown(md)
