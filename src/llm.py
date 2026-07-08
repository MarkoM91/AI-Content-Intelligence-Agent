import json,os,re
from .agents import local_brief
def _parse(text):
    clean=re.sub(r"^```(?:json)?|```$","",text.strip(),flags=re.I|re.M).strip(); match=re.search(r"\{.*\}",clean,re.S)
    return json.loads(match.group(0) if match else clean)
def _philosophy():
    try:
        from .fresh_research import load_philosophy
        return load_philosophy()
    except Exception: return ""

def _prompt(row,context,goal):
    keys=["url","title","clicks_current","impressions_current","ctr_current","growth_pct","status","opportunity_score","topic","keywords","h1","meta_description","paragraph_context","fresh_research_summary","competitor_domains_found","fresh_angles","winning_cluster","winning_hook","entities","proposed_argument","discover_potential","evidence_count","evidence_urls","editorial_decision","urgency","recommended_headline","editorial_advice","differentiation","source_title","title_recipe","tone","angle","comparable_titles","best_match_score","replication_score","materiale_fonti","titoli_vincenti"]
    philosophy=_philosophy()
    return f'''Sei il caporedattore di una testata news italiana orientata a Google Discover. Filosofia editoriale (vincolante):\n{philosophy}\n\nTrasforma i dati in una raccomandazione pronta per una riunione di redazione. Devi decidere cosa fare, non descrivere genericamente il tema. Parti dall'articolo che ha già funzionato (source_title) e dai pattern editoriali ricorrenti osservati nei vincitori (title_recipe: tratti di titolo, hook, formato, tono): il titolo scelto deve applicare quei pattern in modo naturale a uno sviluppo nuovo, senza duplicare l'articolo di origine né i contenuti comparabili (comparable_titles). Non promettere risultati Discover.\n\nRestituisci esclusivamente JSON valido con queste chiavi esatte:\n- consiglio_editoriale: una decisione netta tra Pubblica subito, Prepara e valida, Monitora, Non prioritario;\n- nota_editoriale: 2-3 frasi con potenziale, motivazione e condizione necessaria;\n- titolo_scelto: il titolo raccomandato, concreto e coerente con i fatti. DEVE essere un vero titolo da quotidiano online italiano — soggetto forte in apertura, virgola o due punti, virgolettato se le fonti lo offrono, promessa concreta — nello stile dei titoli che hanno già funzionato sul sito (vedi titoli_vincenti): replicane struttura e tono senza copiarli, niente stile blog o accademico. NON riutilizzare recommended_headline: è un segnaposto generato da regole, scrivi un titolo nuovo dai fatti del materiale;\n- perche_questo_titolo: perché è la scelta migliore per interesse, chiarezza e promessa;\n- titoli_alternativi: array di esattamente 5 titoli realmente diversi, ciascuno tra 60 e 95 caratteri (limite mobile), tutti nello stesso stile da quotidiano online ispirato a titoli_vincenti;\n- meta_description: massimo 158 caratteri, informativa e non duplicata dal titolo;\n- focus_query: tema o entità principale, senza keyword stuffing;\n- angolo: la prospettiva precisa del pezzo;\n- differenziazione: cosa offre in più rispetto alle coperture esistenti;\n- elementi_nuovi: array di almeno 3 fatti, dati, voci o conseguenze da trovare;\n- struttura_articolo: array di 4-6 paragrafi o sezioni con funzione editoriale chiara;\n- formato_suggerito: formato e indicazioni mobile-first;\n- timing: quando pubblicare e perché;\n- fonti_da_verificare: array di fonti primarie o controlli concreti;\n- link_interno: pagina o cluster interno da collegare;\n- rischi_note: rischi fattuali, legali, reputazionali, deontologici o di titolo (segnala esplicitamente se il tema tocca vittime non identificate, suicidio, minori o salute: in quei casi consiglio_editoriale deve essere prudente);\n- azioni_consigliate: array ordinato di passi eseguibili dalla redazione;\n- scelte_editoriali: array di 3-5 scelte motivate in prima persona (bilanciamento delle fonti, cosa è verificato e da quante fonti, cosa manca e come completarlo, perché il titolo scelto batte le alternative);\n- bozza_articolo: array di 7-10 paragrafi PRONTI per il CMS, ciascuno di 60-100 parole (500-800 parole totali: un articolo completo da quotidiano online, non un riassunto), scritti ESCLUSIVAMENTE dai fatti presenti in materiale_fonti — sfrutta TUTTI i fatti, i nomi, i numeri, le date e i virgolettati disponibili, inclusa la cronologia della vicenda ricostruibile dalle fonti — con attribuzioni esplicite («secondo…», virgolettati solo se presenti nelle fonti) e condizionale dove non confermato; apertura sul fatto nuovo, contesto e cronologia, sviluppo con dati e dichiarazioni, chiusura sulle domande aperte; se il materiale è povero scrivi comunque il pezzo più completo possibile con quei fatti e segnala in scelte_editoriali cosa manca;\n- stima_potenziale: stima onesta e prudente della distribuzione attesa (range di click) e perché.\n\nPer ogni titolo valuta implicitamente lunghezza, leggibilità mobile, entità riconoscibile e tensione informativa. Evita clickbait vuoto, formule generiche e affermazioni non sostenute. La nota editoriale deve poter dire anche “non pubblicare” quando le evidenze non bastano.\nContesto: {context}\nObiettivo: {goal}\nDati: {json.dumps({k:row.get(k,"") for k in keys},ensure_ascii=False,default=str)}'''
def _call_llm(prompt,provider,model,max_tokens=4500):
    if provider=="Anthropic":
        from anthropic import Anthropic
        key=os.getenv("ANTHROPIC_API_KEY"); assert key,"ANTHROPIC_API_KEY mancante"
        return Anthropic(api_key=key).messages.create(model=model or "claude-3-5-sonnet-latest",max_tokens=max_tokens,messages=[{"role":"user","content":prompt}]).content[0].text
    from openai import OpenAI
    key=os.getenv("OPENAI_API_KEY"); assert key,"OPENAI_API_KEY mancante"
    return OpenAI(api_key=key).chat.completions.create(model=model or "gpt-4o",messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"}).choices[0].message.content

def _expand_bozza(row,brief,provider,model):
    """Seconda passata dedicata al pezzo: i modelli tagliano la bozza quando devono
    riempire 17 campi JSON insieme; una chiamata solo-articolo rispetta la lunghezza."""
    materiale=str(row.get("materiale_fonti","") or "").strip()
    if not materiale: return brief
    words=sum(len(str(p).split()) for p in brief.get("bozza_articolo") or [])
    if words>=350: return brief
    prompt=(f"Sei un redattore di un quotidiano online italiano. Scrivi l'articolo COMPLETO pronto per il CMS.\n"
            f"Titolo scelto: {brief.get('titolo_scelto','')}\nAngolo: {brief.get('angolo','')}\n"
            f"Regole vincolanti: 7-10 paragrafi, 500-800 parole totali, ogni paragrafo 60-100 parole; usa ESCLUSIVAMENTE fatti, nomi, numeri, date e virgolettati presenti nel MATERIALE (attribuisci sempre: «secondo...», virgolettati solo se presenti); condizionale dove non confermato; apertura sul fatto nuovo, contesto e cronologia, sviluppo con dati e dichiarazioni, chiusura sulle domande aperte; nessun fatto inventato.\n"
            f'Rispondi solo JSON: {{"bozza_articolo":["paragrafo 1","paragrafo 2","..."]}}\n\nMATERIALE:\n{materiale}')
    try:
        data=_parse(_call_llm(prompt,provider,model))
        paragraphs=[str(p).strip() for p in data.get("bozza_articolo",[]) if str(p).strip()]
        if sum(len(p.split()) for p in paragraphs)>words: brief["bozza_articolo"]=paragraphs
    except Exception: pass
    return brief

def generate_brief(row,mode="Regole locali",provider="OpenAI",model="",client_context="",goal="Crescita organica"):
    if mode=="Regole locali": return local_brief(row,client_context,goal),None
    try:
        brief=_parse(_call_llm(_prompt(row,client_context,goal),provider,model))
        return _expand_bozza(row,brief,provider,model),None
    except Exception as e: return local_brief(row,client_context,goal),f"Fallback alle regole locali: {e}"
