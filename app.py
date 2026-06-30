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

load_dotenv()
import os
for _secret_key in ("OPENAI_API_KEY","ANTHROPIC_API_KEY"):
    try:
        if not os.getenv(_secret_key) and _secret_key in st.secrets: os.environ[_secret_key]=str(st.secrets[_secret_key])
    except Exception: pass
st.set_page_config(page_title="AI Content Intelligence Agent",page_icon="🧭",layout="wide")
st.title("AI Content Intelligence Agent")
st.caption("GSC/Discover → scoring → crawler → competitor research → brief → approvazione umana → report")

DEFAULTS={"analyzed":None,"short_df":None,"long_df":None,"gsc_info":{},"crawl_log":[],"research_df":None,"briefs":[],"approvals":[],"hermes_notes":[],"mode_label":"Demo CSV"}
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
    st.header("Contesto cliente")
    client=st.text_input("Cliente / progetto","Agenzia digitale demo")
    context=st.text_area("Target, mercato e tono","Editore italiano; tono autorevole, chiaro e verificabile.")
    goal=st.text_input("Obiettivo","Crescita organica e opportunità editoriali")
    st.header("Dati")
    input_mode=st.radio("Modalità",["Google Search Console API","Demo CSV"])
    st.header("Crawler pagine")
    max_crawl=st.slider("URL da analizzare",1,20,5); delay=st.number_input("Pausa tra richieste (s)",0.0,5.0,.2,.1)
    st.header("Ricerca competitor/fresca")
    research_provider=st.selectbox("Provider",["AI (LLM) + Web scraper","Web scraper + Google News","Hermes Agent + Web scraper","Google News RSS","RSS personalizzati","Piano locale"],help="AI (LLM) raffina le evidenze con OpenAI/Anthropic e usa il match semantico via embeddings; richiede una API key in .env, altrimenti torna automaticamente alle euristiche locali.")
    seed_strategy=st.selectbox("Contenuti da analizzare",["Top per click (cosa funziona)","Migliori per opportunità","In crescita"],help="Da quali contenuti Discover partire per cercare coperture competitor simili.")
    min_match=st.slider("Soglia di pertinenza fonti (%)",0,100,35,help="Mostra solo le coperture competitor con un match (semantico o euristico) sopra questa soglia. Alza il valore per fonti più precise.")
    own_domain=st.text_input("Dominio proprio da escludere","affaritaliani.it")
    feeds=st.text_area("Feed RSS, uno per riga","https://www.ansa.it/sito/ansait_rss.xml\nhttps://www.ilsole24ore.com/rss/italia.xml\nhttps://www.agi.it/rss\nhttps://www.rainews.it/rss/tutti\nhttps://www.wired.it/feed/rss\nhttps://www.corriere.it/rss/homepage.xml")
    hermes_command=st.text_input("Comando Hermes","hermes",help="Usato solo con Hermes Agent + Web scraper")
    st.header("Generazione brief")
    brief_mode=st.radio("Motore",["AI con LLM","Regole locali"])
    llm_provider=st.selectbox("LLM",["OpenAI","Anthropic"],disabled=brief_mode=="Regole locali")
    model=st.text_input("Modello (vuoto = predefinito)",disabled=brief_mode=="Regole locali")

tabs=st.tabs(["1. Dati","2. Analisi + crawler","3. Competitor research","4. Brief e approvazioni","5. Report"])
with tabs[0]:
    st.subheader("Acquisizione dati")
    if input_mode=="Demo CSV":
        st.info("Dataset dimostrativo incluso: periodo corrente di 3 giorni e baseline di 7 giorni.")
        if st.button("Carica e analizza demo",type="primary"):
            st.session_state.short_df=pd.read_csv("sample_short_3d.csv"); st.session_state.long_df=pd.read_csv("sample_long_7d.csv")
            st.session_state.analyzed=analyze_comparison(st.session_state.short_df,st.session_state.long_df,3,7); st.session_state.mode_label=input_mode
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
                    snapshot_id=save_snapshot(st.session_state.analyzed,short,long,f"GSC Discover {current_days}g {info1['start']} → {info1['end']}",st.session_state.gsc_info)
                    st.success(f"Dati salvati nell’archivio locale (snapshot #{snapshot_id}).")
            except Exception as e: st.error(f"Impossibile scaricare i dati GSC: {e}")
    if st.session_state.short_df is not None: st.dataframe(st.session_state.short_df.head(50),use_container_width=True)

with tabs[1]:
    analyzed=st.session_state.analyzed
    if analyzed is None: st.info("Carica o genera i dati nella scheda Dati.")
    else:
        c1,c2,c3=st.columns(3); c1.metric("URL",len(analyzed)); c2.metric("Impression correnti",int(analyzed.impressions_current.sum())); c3.metric("Click correnti",int(analyzed.clicks_current.sum()))
        st.dataframe(analyzed,use_container_width=True)
        if st.button("Avvia crawler sulle URL principali"):
            with st.spinner("Crawler in esecuzione..."):
                enriched,logs=enrich_analyzed_dataframe(analyzed,max_crawl,delay); st.session_state.analyzed=enriched; st.session_state.crawl_log=logs
            st.success("Arricchimento completato.")
        if st.session_state.crawl_log: st.dataframe(pd.DataFrame(st.session_state.crawl_log),use_container_width=True)

with tabs[2]:
    if st.session_state.analyzed is None: st.info("Prima esegui l’analisi.")
    else:
        provider=research_provider
        use_hermes=provider=="Hermes Agent + Web scraper"
        use_llm=provider=="AI (LLM) + Web scraper"
        if provider in ("Hermes Agent + Web scraper","AI (LLM) + Web scraper","Google News RSS"): provider="Web scraper + Google News"
        st.caption(f"Base: «{seed_strategy}» sui tuoi dati Discover. Per ogni contenuto trova coperture competitor simili, estrae il testo e propone contenuti originali.")
        if use_llm:
            st.success("Modalità AI: match semantico via embeddings e raffinamento LLM; senza API key il sistema usa euristiche e scoring locali.")
        if use_hermes:
            from src.fresh_research import hermes_available
            if hermes_available(hermes_command): st.success("Hermes Agent rilevato: le evidenze saranno passate all’agente.")
            else: st.warning("Hermes Agent non è installato o non è nel PATH. Il web scraper funzionerà comunque con suggerimenti locali.")
        if st.button("Avvia ricerca competitor",type="primary"):
            with st.spinner("Ricerca guidata dai topic che stanno già funzionando..."):
                research,enriched,notes=add_research_to_dataframe(st.session_state.analyzed,provider,own_domain,[x for x in feeds.splitlines() if x.strip()],audience_context=context,use_hermes=use_hermes,hermes_command=hermes_command,use_llm=use_llm,llm_provider=llm_provider,llm_model=model,seed_strategy=seed_strategy)
                st.session_state.research_df=research; st.session_state.analyzed=enriched; st.session_state.hermes_notes=notes
        if st.session_state.research_df is not None:
            research=st.session_state.research_df
            real=research[research.url.fillna("").ne("")] if "url" in research else research
            c1,c2,c3=st.columns(3)
            c1.metric("Fonti reali",len(real)); c2.metric("Domini",real.competitor_domain.replace("",pd.NA).dropna().nunique() if "competitor_domain" in real else 0); c3.metric("Pagine estratte",real.scrape_status.fillna("").str.startswith("OK").sum() if "scrape_status" in real else 0)
            st.subheader("Suggerimenti editoriali dai tuoi contenuti Discover che funzionano")
            relevant=real[real.competitor_match_score.fillna(0)>=min_match] if "competitor_match_score" in real else real
            suggestions=relevant.sort_values("competitor_match_score",ascending=False).drop_duplicates(["source_url","article_suggestion"]).head(12)
            if suggestions.empty:
                st.info(f"Nessuna fonte competitor sopra la soglia di pertinenza ({min_match}%). Abbassa la soglia nella sidebar o riprova la ricerca.")
            for _,item in suggestions.iterrows():
                with st.container(border=True):
                    st.markdown(f"#### {item.get('article_suggestion','Idea da sviluppare')}")
                    st.write(item.get("audience_reason",""))
                    st.caption(f"Formato: {item.get('recommended_format','')} · Angolo competitor: {item.get('angle','')} · Match: {item.get('competitor_match_score',0)}")
                    if item.get("url"): st.link_button("Apri fonte",item["url"])
            with st.expander("Evidenze e dati tecnici"):
                st.dataframe(research,use_container_width=True)
            for note in st.session_state.hermes_notes:
                result=note.get("result")
                if isinstance(result,str): st.info(result)
                elif isinstance(result,dict) and result.get("suggestions"):
                    st.subheader("Raccomandazioni AI (LLM / Hermes)")
                    for suggestion in result["suggestions"]:
                        with st.container(border=True):
                            st.markdown(f"#### {suggestion.get('title','Idea Hermes')}")
                            st.write(suggestion.get("audience_reason",""))
                            st.caption(f"Formato: {suggestion.get('format','')} · Angolo: {suggestion.get('angle','')}")

with tabs[3]:
    if st.session_state.analyzed is None: st.info("Prima esegui l’analisi.")
    else:
        options=st.session_state.analyzed.head(20); selected=st.selectbox("Contenuto",options.url,format_func=lambda u: f"{options.loc[options.url.eq(u),'topic'].iloc[0]} — {u}")
        if st.button("Genera brief",type="primary"):
            row=options.loc[options.url.eq(selected)].iloc[0].to_dict(); brief,error=generate_brief(row,brief_mode,llm_provider,model,context,goal); brief["source_url"]=selected
            st.session_state.briefs=[b for b in st.session_state.briefs if b.get("source_url")!=selected]+[brief]
            st.session_state.approvals=[a for a in st.session_state.approvals if a.get("source_url")!=selected]+[{**a,"source_url":selected} for a in propose_actions(brief,row)]
            if error: st.warning(error)
        for i,b in enumerate(st.session_state.briefs):
            with st.expander(b.get("titolo_consigliato",f"Brief {i+1}"),expanded=True): st.json(b)
        if st.session_state.approvals:
            st.subheader("Coda di approvazione umana")
            for i,a in enumerate(st.session_state.approvals):
                c1,c2,c3=st.columns([4,1,2]); c1.markdown(f"**{a['azione']}**  \n{a['motivo']} — Responsabile: {a['responsabile']}"); c2.write(f"Rischio: {a['rischio']}")
                opts=["In attesa","Approva","Modifica","Rifiuta","Auto-approvata"]; a["stato"]=c3.selectbox("Stato",opts,index=opts.index(a["stato"]),key=f"approval_{i}",label_visibility="collapsed")

with tabs[4]:
    if st.session_state.analyzed is None: st.info("Non ci sono dati da esportare.")
    else:
        md=generate_markdown_report(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,client); workflow=generate_json_export(st.session_state.analyzed,st.session_state.research_df,st.session_state.briefs,st.session_state.approvals,{"client":client,"mode":st.session_state.mode_label})
        st.markdown(md)
        c1,c2,c3=st.columns(3); c1.download_button("Scarica report Markdown",md,"report_ai_content.md","text/markdown"); c2.download_button("Scarica CSV analizzato",st.session_state.analyzed.to_csv(index=False).encode("utf-8-sig"),"contenuti_analizzati.csv","text/csv"); c3.download_button("Scarica workflow JSON",workflow,"workflow.json","application/json")
        if st.session_state.research_df is not None: st.download_button("Scarica ricerca competitor CSV",st.session_state.research_df.to_csv(index=False).encode("utf-8-sig"),"ricerca_competitor.csv","text/csv")
