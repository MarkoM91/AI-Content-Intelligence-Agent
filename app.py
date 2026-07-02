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
from src.audience_intelligence import build_audience_dna, build_discover_expansion

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
  .hero .pipe span:nth-child(n+5){display:none;}
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
<div class="eyebrow">Editorial intelligence workspace</div>
<h1>Dai segnali di audience alla prossima decisione editoriale.</h1>
<p>Un workflow verificabile per capire cosa funziona, leggere il mercato e trasformare le evidenze in contenuti pronti da approvare.</p>
<div class="pipe"><span>01 · Signals</span><span>02 · Audience DNA</span><span>03 · Discover Expansion</span><span>04 · Editorial Studio</span><span>05 · Publish & Learn</span></div>
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

def _opportunity_card(item):
    title=_html.escape(str(item.get("recommended_headline") or item.get("adjacent_topic","Territorio adiacente")))
    argument=_html.escape(str(item.get("editorial_advice") or item.get("proposed_argument","")))
    cluster=_html.escape(str(item.get("winning_cluster","")))
    status=_html.escape(str(item.get("validation_status","")))
    decision=_html.escape(str(item.get("editorial_decision","Da valutare")))
    urgency=_html.escape(str(item.get("urgency","")))
    score=float(item.get("discover_potential",0) or 0)
    color="#176b52" if score>=70 else "#a76532" if score>=55 else "#66736e"
    return (f'<div class="sugg-card"><div class="sugg-head"><h4>{title}</h4>'
            f'<span class="badge" style="background:{color}18;color:{color}">Potential {score:.0f}</span></div>'
            f'<p class="sugg-reason"><b>{decision}</b> · {argument}</p><div class="sugg-meta"><span>Quando · {urgency}</span>'
            f'<span>Origine · {cluster}</span><span>Adiacenza · {_html.escape(str(item.get("adjacency_type","")))}</span><span>{status}</span></div></div>')

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
    if "discover_potential" in d.columns: cfg["discover_potential"]=st.column_config.ProgressColumn("Discover potential",min_value=0,max_value=100,format="%.0f")
    if "competitor_match_score" in d.columns: cfg["competitor_match_score"]=st.column_config.ProgressColumn("Match",min_value=0,max_value=100,format="%.0f")
    for c,(lbl,fmt) in {"clicks":("Click","%d"),"clicks_current":("Click","%d"),"impressions":("Impression","%d"),"impressions_current":("Impression","%d"),"growth_pct":("Crescita %","%.0f%%"),"position":("Posizione","%.1f")}.items():
        if c in d.columns: cfg[c]=st.column_config.NumberColumn(lbl,format=fmt)
    for c,(lbl,fmt) in {"pageviews":("Pageview","%d"),"avg_time_seconds":("Tempo medio","%.1fs"),"total_time_seconds":("Engagement totale","%.0fs")}.items():
        if c in d.columns: cfg[c]=st.column_config.NumberColumn(lbl,format=fmt)
    st.dataframe(d,use_container_width=True,column_config=cfg,hide_index=True)

DEFAULTS={"analyzed":None,"short_df":None,"long_df":None,"gsc_info":{},"crawl_log":[],"research_df":None,"audience_dna":None,"opportunities":None,"briefs":[],"approvals":[],"publishing_queue":[],"hermes_notes":[],"mode_label":"Demo CSV"}
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

with st.sidebar:
    st.markdown("**NEWSROOM OS**")
    st.caption("Configura il contesto. Il lavoro editoriale resta nell'area principale.")
    st.header("Mandato editoriale")
    client=st.text_input("Cliente / progetto","Agenzia digitale demo")
    context=st.text_area("Target, mercato e tono","Editore italiano; tono autorevole, chiaro e verificabile.")
    goal=st.text_input("Obiettivo","Crescita organica e opportunità editoriali")
    st.header("Fonte dati")
    input_mode=st.radio("Modalità",["Google Search Console API","Export engagement CSV (7 giorni)","Demo CSV"])
    st.header("Profondità analisi")
    max_crawl=st.slider("URL da analizzare",1,20,5); delay=st.number_input("Pausa tra richieste (s)",0.0,5.0,.2,.1)
    st.header("Ricerca di mercato")
    research_provider=st.selectbox("Provider",["AI (LLM) + Web scraper","Serper + Google News","Web scraper + Google News","Hermes Agent + Web scraper","Google News RSS","RSS personalizzati","Piano locale"],help="AI (LLM) raffina le evidenze con OpenAI/Anthropic e usa il match semantico via embeddings; richiede una API key in .env, altrimenti torna automaticamente alle euristiche locali.")
    engagement_loaded=st.session_state.analyzed is not None and "pageviews" in st.session_state.analyzed
    seed_options=(["Top per engagement totale","Alta permanenza","Filoni ricorrenti"] if engagement_loaded else [])+["Top per click (cosa funziona)","Migliori per opportunità","In crescita"]
    seed_strategy=st.selectbox("Contenuti da analizzare",seed_options,help="Scegli il segnale editoriale da usare come base per la ricerca competitor.")
    freshness_label=st.selectbox("Freschezza fonti",["Ultime 24h","Ultimi 7 giorni","Ultimi 30 giorni"],index=1,help="Finestra temporale della ricerca web competitor. 24h = solo contenuti pubblicati oggi/ieri (notizia del momento).")
    freshness={"Ultime 24h":"1d","Ultimi 7 giorni":"7d","Ultimi 30 giorni":"30d"}[freshness_label]
    include_reddit=st.checkbox("Includi Reddit (best-effort)",value=False,help="Aggiunge articoli linkati su Reddit. Gratuito, ma Reddit blocca spesso gli IP server: se non risponde viene ignorato senza errori.")
    min_match=st.slider("Soglia di pertinenza fonti (%)",0,100,35,help="Mostra solo le coperture competitor con un match (semantico o euristico) sopra questa soglia. Alza il valore per fonti più precise.")
    own_domain=st.text_input("Dominio proprio da escludere","affaritaliani.it")
    from src.fresh_research import DEFAULT_RSS_FEEDS
    feeds=st.text_area("Feed RSS, uno per riga","\n".join(DEFAULT_RSS_FEEDS),height=160)
    hermes_command=st.text_input("Comando Hermes","hermes",help="Usato solo con Hermes Agent + Web scraper")
    st.header("Motore editoriale")
    brief_mode=st.radio("Motore",["AI con LLM","Regole locali"])
    llm_provider=st.selectbox("LLM",["OpenAI","Anthropic"],disabled=brief_mode=="Regole locali")
    model=st.text_input("Modello (vuoto = predefinito)",disabled=brief_mode=="Regole locali")

tabs=st.tabs(["01  Signals","02  Audience DNA","03  Discover Expansion","04  Editorial Studio","05  Publish & Learn"])
with tabs[0]:
    st.caption("STEP 01 · RACCOGLI LE EVIDENZE")
    st.subheader("Collega il segnale che vuoi trasformare in decisioni")
    if input_mode=="Demo CSV":
        st.info("Dataset dimostrativo incluso: periodo corrente di 3 giorni e baseline di 7 giorni.")
        if st.button("Carica e analizza demo",type="primary"):
            st.session_state.short_df=pd.read_csv("sample_short_3d.csv"); st.session_state.long_df=pd.read_csv("sample_long_7d.csv")
            st.session_state.analyzed=analyze_comparison(st.session_state.short_df,st.session_state.long_df,3,7); st.session_state.mode_label=input_mode
            st.session_state.audience_dna=None; st.session_state.opportunities=None; st.session_state.research_df=None
    elif input_mode=="Export engagement CSV (7 giorni)":
        st.info("Carica un CSV con URL, pageview, tempo totale, tempo medio per view e flag. I nomi colonna comuni e gli export generici a 5 colonne vengono riconosciuti automaticamente.")
        engagement_upload=st.file_uploader("CSV pageview / engagement",type=["csv"],key="engagement_csv")
        if st.button("Analizza traffico ed engagement",type="primary",disabled=engagement_upload is None):
            try:
                raw_engagement=read_csv(engagement_upload)
                analyzed_engagement=analyze_engagement_export(raw_engagement)
                if analyzed_engagement.empty: st.warning("Il file non contiene URL analizzabili.")
                else:
                    st.session_state.short_df=raw_engagement
                    st.session_state.long_df=None
                    st.session_state.analyzed=analyzed_engagement
                    st.session_state.mode_label=input_mode
                    st.session_state.research_df=None; st.session_state.audience_dna=None; st.session_state.opportunities=None
                    st.success(f"Analizzati {len(analyzed_engagement)} articoli. Ora puoi usare questi segnali nella ricerca competitor.")
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
        else: st.warning("Configurazione GSC assente. In Streamlit Cloud aggiungi le sezioni [gsc] e [google_oauth] nei Secrets dell’app; non caricare credenziali su GitHub.")
        if st.button("Scarica da GSC",type="primary",disabled=not local_config_exists and not cloud_secrets_ready):
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
                    st.session_state.audience_dna=None; st.session_state.opportunities=None; st.session_state.research_df=None
                    snapshot_id=save_snapshot(st.session_state.analyzed,short,long,f"GSC Discover {current_days}g {info1['start']} → {info1['end']}",st.session_state.gsc_info)
                    st.success(f"Dati salvati nell’archivio locale (snapshot #{snapshot_id}).")
            except Exception as e: st.error(f"Impossibile scaricare i dati GSC: {e}")
    if st.session_state.short_df is not None: _show_table(st.session_state.short_df.head(50))

with tabs[1]:
    st.caption("STEP 02 · CAPIRE PERCHÉ HA FUNZIONATO")
    st.subheader("Ricostruisci il DNA degli interessi che Discover ha premiato")
    analyzed=st.session_state.analyzed
    if analyzed is None: st.info("Carica o genera i dati nella scheda Dati.")
    else:
        if "pageviews" in analyzed:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Articoli",len(analyzed)); c2.metric("Pageview",f"{int(analyzed.pageviews.sum()):,}")
            c3.metric("Tempo medio / view",f"{analyzed.avg_time_seconds.mean():.1f}s")
            c4.metric("Engagement totale",f"{int(analyzed.total_time_seconds.sum()/3600):,}h")
            st.subheader("Segnali editoriali")
            themes=summarize_editorial_themes(analyzed)
            if not themes.empty: _show_table(themes)
            left,right=st.columns(2)
            with left:
                st.markdown("**Traffico più alto**")
                _show_table(analyzed.sort_values("pageviews",ascending=False)[["title","url","pageviews","avg_time_seconds","editorial_signal"]].head(10))
            with right:
                st.markdown("**Permanenza più alta**")
                _show_table(analyzed.sort_values("avg_time_seconds",ascending=False)[["title","url","pageviews","avg_time_seconds","editorial_signal"]].head(10))
        else:
            c1,c2,c3=st.columns(3); c1.metric("URL",len(analyzed)); c2.metric("Impression correnti",int(analyzed.impressions_current.sum())); c3.metric("Click correnti",int(analyzed.clicks_current.sum()))
        st.markdown("L'analisi separa tema, entità, hook e formato: non cerca keyword, ricostruisce il profilo di interesse attivato dai contenuti vincenti.")
        if st.button("Costruisci Audience DNA",type="primary"):
            st.session_state.audience_dna=build_audience_dna(analyzed)
            st.session_state.opportunities=None
        if st.session_state.audience_dna is not None:
            dna=st.session_state.audience_dna
            if dna.empty: st.info("Non ci sono ancora segnali sufficienti per costruire l'Audience DNA.")
            else:
                d1,d2,d3=st.columns(3)
                d1.metric("Cluster vincenti",dna.interest_cluster.nunique())
                d2.metric("Entità riconosciute",len({x.strip() for values in dna.entities for x in str(values).split(",") if x.strip()}))
                d3.metric("Forza media",f"{dna.audience_strength.mean():.0f}/100")
                st.subheader("Mappa degli interessi validati")
                _show_table(dna[["source_title","interest_cluster","entities","winning_hook","winning_format","audience_strength","why_it_worked"]])
        _show_table(analyzed)
        if st.button("Avvia crawler sulle URL principali"):
            with st.spinner("Crawler in esecuzione..."):
                enriched,logs=enrich_analyzed_dataframe(analyzed,max_crawl,delay); st.session_state.analyzed=enriched; st.session_state.crawl_log=logs
            st.success("Arricchimento completato.")
        if st.session_state.crawl_log: st.dataframe(pd.DataFrame(st.session_state.crawl_log),use_container_width=True)

with tabs[2]:
    st.caption("STEP 03 · ESPANDERE L'INTERESSE, NON COPIARE L'ARTICOLO")
    st.subheader("Scopri territori adiacenti con potenziale Discover")
    if st.session_state.analyzed is None: st.info("Prima importa i segnali nella tab 01.")
    else:
        if st.session_state.audience_dna is None:
            st.session_state.audience_dna=build_audience_dna(st.session_state.analyzed)
        if st.session_state.opportunities is not None and "editorial_advice" not in st.session_state.opportunities.columns:
            st.session_state.opportunities=build_discover_expansion(st.session_state.analyzed,st.session_state.research_df)
        provider=research_provider
        use_hermes=provider=="Hermes Agent + Web scraper"
        use_llm=provider=="AI (LLM) + Web scraper"
        use_serper=provider=="Serper + Google News"
        if provider in ("Hermes Agent + Web scraper","AI (LLM) + Web scraper","Google News RSS","Serper + Google News"): provider="Web scraper + Google News"
        signal_source="pageview ed engagement" if "pageviews" in st.session_state.analyzed else "Google Discover"
        st.caption(f"Base: Audience DNA derivato da {signal_source} · Freschezza validazione: {freshness_label}. Le fonti esterne validano l'adiacenza; non determinano da sole le idee.")
        if use_llm:
            st.success("Modalità AI: match semantico via embeddings e raffinamento LLM; senza API key il sistema usa euristiche e scoring locali.")
        if use_hermes:
            from src.fresh_research import hermes_available
            if hermes_available(hermes_command): st.success("Hermes Agent rilevato: le evidenze saranno passate all’agente.")
            else: st.warning("Hermes Agent non è installato o non è nel PATH. Il web scraper funzionerà comunque con suggerimenti locali.")
        local_col,web_col=st.columns(2)
        if local_col.button("Genera mappa di adiacenza"):
            st.session_state.opportunities=build_discover_expansion(st.session_state.analyzed,st.session_state.research_df)
        if web_col.button("Valida con fonti fresche",type="primary"):
            with st.spinner("Espansione dei cluster vincenti e validazione delle adiacenze..."):
                research,enriched,notes=add_research_to_dataframe(st.session_state.analyzed,provider,own_domain,[x for x in feeds.splitlines() if x.strip()],audience_context=context,use_hermes=use_hermes,hermes_command=hermes_command,use_llm=use_llm,llm_provider=llm_provider,llm_model=model,seed_strategy=seed_strategy,freshness=freshness,include_reddit=include_reddit,serper_api_key=os.getenv("SERPER_API_KEY","") if use_serper else "")
                st.session_state.research_df=research; st.session_state.analyzed=enriched; st.session_state.hermes_notes=notes
                st.session_state.opportunities=build_discover_expansion(enriched,research)
        if st.session_state.opportunities is not None:
            opportunities=st.session_state.opportunities
            valid_count=int(opportunities.validation_status.eq("Validata da fonti fresche").sum()) if not opportunities.empty else 0
            o1,o2,o3,o4=st.columns(4)
            o1.metric("Consigli: pubblica ora",int(opportunities.editorial_decision.eq("Pubblica ora").sum()))
            o2.metric("Da preparare",int(opportunities.editorial_decision.eq("Prepara e valida").sum()))
            o3.metric("Validati da fonti",valid_count)
            o4.metric("Potential medio",f"{opportunities.discover_potential.mean():.0f}/100" if not opportunities.empty else "0/100")
            st.success("Qui non trovi solo dati: ogni card ti dice se pubblicare, cosa pubblicare, con quale titolo e in quale finestra temporale.")
            st.caption("Il potential è relativo e non garantisce distribuzione su Discover.")
            for _,item in opportunities.head(12).iterrows(): st.markdown(_opportunity_card(item),unsafe_allow_html=True)
            with st.expander("Scoring trasparente e tutte le opportunità"):
                _show_table(opportunities)
        if st.session_state.research_df is not None:
            research=st.session_state.research_df
            real=research[research.url.fillna("").ne("")] if "url" in research else research
            with st.expander(f"Evidenze esterne · {len(real)} fonti reali"):
                _show_table(research)
            for note in st.session_state.hermes_notes:
                result=note.get("result")
                if isinstance(result,str): st.info(result)
                elif isinstance(result,dict) and result.get("suggestions"):
                    st.subheader("Raccomandazioni AI (LLM / Hermes)")
                    for suggestion in result["suggestions"]:
                        urls=suggestion.get("source_urls") or []
                        st.markdown(_suggestion_card({"article_suggestion":suggestion.get("title","Idea AI"),"audience_reason":suggestion.get("audience_reason",""),"recommended_format":suggestion.get("format",""),"angle":suggestion.get("angle",""),"url":urls[0] if isinstance(urls,list) and urls else "","competitor_match_score":0}),unsafe_allow_html=True)

with tabs[3]:
    st.caption("STEP 04 · DALL'IDEA ALLA DECISIONE")
    st.subheader("Trasforma un territorio adiacente in una proposta editoriale")
    if st.session_state.opportunities is None or st.session_state.opportunities.empty: st.info("Prima genera almeno un territorio nella tab Discover Expansion.")
    else:
        options=st.session_state.opportunities.head(30)
        selected=st.selectbox("Consiglio da sviluppare",options.opportunity_id,format_func=lambda oid: f"{options.loc[options.opportunity_id.eq(oid),'editorial_decision'].iloc[0]} · {options.loc[options.opportunity_id.eq(oid),'recommended_headline'].iloc[0]}")
        selected_opp=options.loc[options.opportunity_id.eq(selected)].iloc[0].to_dict()
        st.markdown(_opportunity_card(selected_opp),unsafe_allow_html=True)
        if st.button("Apri in Editorial Studio",type="primary"):
            row={**selected_opp,"url":selected_opp.get("source_url",""),"topic":selected_opp.get("adjacent_topic",""),"title":selected_opp.get("recommended_headline") or selected_opp.get("adjacent_topic",""),"status":selected_opp.get("editorial_decision",""),"opportunity_score":selected_opp.get("discover_potential",0),"fresh_research_summary":selected_opp.get("differentiation") or selected_opp.get("proposed_argument","")}
            brief,error=generate_brief(row,brief_mode,llm_provider,model,context,goal)
            brief.update({"source_url":row["url"],"opportunity_id":selected,"discover_potential":selected_opp.get("discover_potential",0),"origin_cluster":selected_opp.get("winning_cluster","")})
            st.session_state.briefs=[b for b in st.session_state.briefs if b.get("opportunity_id")!=selected]+[brief]
            st.session_state.approvals=[a for a in st.session_state.approvals if a.get("opportunity_id")!=selected]+[{**a,"source_url":row["url"],"opportunity_id":selected} for a in propose_actions(brief,row)]
            queue_item={"opportunity_id":selected,"title":brief.get("titolo_consigliato",selected_opp.get("adjacent_topic","")),"owner":"Da assegnare","deadline":"","status":"In revisione","published_url":"","predicted_potential":float(selected_opp.get("discover_potential",0) or 0),"actual_clicks":0,"actual_avg_time":0.0,"learning":""}
            st.session_state.publishing_queue=[q for q in st.session_state.publishing_queue if q.get("opportunity_id")!=selected]+[queue_item]
            if error: st.warning(error)
        for i,b in enumerate(st.session_state.briefs):
            with st.expander(b.get("titolo_consigliato",f"Brief {i+1}"),expanded=i==len(st.session_state.briefs)-1): st.json(b)
        if st.session_state.approvals:
            st.subheader("Coda di approvazione umana")
            for i,a in enumerate(st.session_state.approvals):
                c1,c2,c3=st.columns([4,1,2]); c1.markdown(f"**{a['azione']}**  \n{a['motivo']} — Responsabile: {a['responsabile']}"); c2.write(f"Rischio: {a['rischio']}")
                opts=["In attesa","Approva","Modifica","Rifiuta","Auto-approvata"]; a["stato"]=c3.selectbox("Stato",opts,index=opts.index(a["stato"]),key=f"approval_{i}",label_visibility="collapsed")

with tabs[4]:
    st.caption("STEP 05 · CHIUDERE IL CICLO")
    st.subheader("Pubblica, misura e restituisci apprendimento al sistema")
    if not st.session_state.publishing_queue: st.info("Le proposte aperte nell'Editorial Studio appariranno qui.")
    else:
        approved_ids={a.get("opportunity_id") for a in st.session_state.approvals if a.get("stato") in ("Approva","Auto-approvata")}
        for item in st.session_state.publishing_queue:
            if item.get("opportunity_id") in approved_ids and item.get("status")=="In revisione": item["status"]="Approvato"
        published=sum(q.get("status")=="Pubblicato" for q in st.session_state.publishing_queue)
        q1,q2,q3=st.columns(3); q1.metric("In pipeline",len(st.session_state.publishing_queue)); q2.metric("Pubblicati",published); q3.metric("Con feedback",sum(bool(q.get("actual_clicks") or q.get("actual_avg_time")) for q in st.session_state.publishing_queue))
        for i,item in enumerate(st.session_state.publishing_queue):
            with st.expander(item.get("title",f"Proposta {i+1}"),expanded=True):
                c1,c2,c3=st.columns(3)
                item["status"]=c1.selectbox("Stato",["In revisione","Approvato","Pianificato","Pubblicato","Archiviato"],index=["In revisione","Approvato","Pianificato","Pubblicato","Archiviato"].index(item.get("status","In revisione")),key=f"queue_status_{i}")
                item["owner"]=c2.text_input("Owner",item.get("owner","Da assegnare"),key=f"queue_owner_{i}")
                item["deadline"]=c3.text_input("Deadline",item.get("deadline",""),placeholder="YYYY-MM-DD",key=f"queue_deadline_{i}")
                item["published_url"]=st.text_input("URL pubblicato",item.get("published_url",""),key=f"queue_url_{i}")
                m1,m2,m3=st.columns(3)
                m1.metric("Potential previsto",f"{float(item.get('predicted_potential',0)):.0f}/100")
                item["actual_clicks"]=int(m2.number_input("Click Discover osservati",min_value=0,value=int(item.get("actual_clicks",0) or 0),key=f"queue_clicks_{i}"))
                item["actual_avg_time"]=float(m3.number_input("Permanenza media osservata",min_value=0.0,value=float(item.get("actual_avg_time",0) or 0),step=.1,key=f"queue_dwell_{i}"))
                item["learning"]=st.text_area("Cosa abbiamo imparato",item.get("learning",""),key=f"queue_learning_{i}",placeholder="Quale entità, hook o formato ha contribuito al risultato?")
                if item["actual_clicks"] or item["actual_avg_time"]:
                    quality="forte" if item["actual_avg_time"]>=15 else "media" if item["actual_avg_time"]>=9 else "debole"
                    st.success(f"Feedback acquisito: distribuzione {item['actual_clicks']} click · qualità di lettura {quality}. Questo dato può guidare la prossima Audience DNA.")
        md=generate_markdown_report(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,client); workflow=generate_json_export(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,st.session_state.approvals,{"client":client,"mode":st.session_state.mode_label,"audience_dna":[] if st.session_state.audience_dna is None else st.session_state.audience_dna.to_dict("records"),"discover_expansion":[] if st.session_state.opportunities is None else st.session_state.opportunities.to_dict("records"),"publishing_queue":st.session_state.publishing_queue})
        st.subheader("Consegna ed export")
        st.markdown(md)
        c1,c2,c3=st.columns(3); c1.download_button("Scarica report Markdown",md,"report_ai_content.md","text/markdown"); c2.download_button("Scarica CSV analizzato",st.session_state.analyzed.to_csv(index=False).encode("utf-8-sig"),"contenuti_analizzati.csv","text/csv"); c3.download_button("Scarica workflow JSON",workflow,"workflow.json","application/json")
        if st.session_state.research_df is not None: st.download_button("Scarica ricerca competitor CSV",st.session_state.research_df.to_csv(index=False).encode("utf-8-sig"),"ricerca_competitor.csv","text/csv")
