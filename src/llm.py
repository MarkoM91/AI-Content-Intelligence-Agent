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
    keys=["url","title","clicks_current","impressions_current","ctr_current","growth_pct","status","opportunity_score","topic","keywords","h1","meta_description","paragraph_context","fresh_research_summary","competitor_domains_found","fresh_angles","winning_cluster","winning_hook","entities","proposed_argument","discover_potential","evidence_count","evidence_urls","editorial_decision","urgency","recommended_headline","editorial_advice","differentiation","source_title","title_recipe","tone","angle","comparable_titles","best_match_score","replication_score","materiale_fonti"]
    philosophy=_philosophy()
    return f'''Sei il caporedattore di una testata news italiana orientata a Google Discover. Filosofia editoriale (vincolante):\n{philosophy}\n\nTrasforma i dati in una raccomandazione pronta per una riunione di redazione. Devi decidere cosa fare, non descrivere genericamente il tema. Parti dall'articolo che ha già funzionato (source_title) e dai pattern editoriali ricorrenti osservati nei vincitori (title_recipe: tratti di titolo, hook, formato, tono): il titolo scelto deve applicare quei pattern in modo naturale a uno sviluppo nuovo, senza duplicare l'articolo di origine né i contenuti comparabili (comparable_titles). Non promettere risultati Discover.\n\nRestituisci esclusivamente JSON valido con queste chiavi esatte:\n- consiglio_editoriale: una decisione netta tra Pubblica subito, Prepara e valida, Monitora, Non prioritario;\n- nota_editoriale: 2-3 frasi con potenziale, motivazione e condizione necessaria;\n- titolo_scelto: il titolo raccomandato, concreto e coerente con i fatti;\n- perche_questo_titolo: perché è la scelta migliore per interesse, chiarezza e promessa;\n- titoli_alternativi: array di esattamente 5 titoli realmente diversi, ciascuno tra 60 e 95 caratteri (limite mobile);\n- meta_description: massimo 158 caratteri, informativa e non duplicata dal titolo;\n- focus_query: tema o entità principale, senza keyword stuffing;\n- angolo: la prospettiva precisa del pezzo;\n- differenziazione: cosa offre in più rispetto alle coperture esistenti;\n- elementi_nuovi: array di almeno 3 fatti, dati, voci o conseguenze da trovare;\n- struttura_articolo: array di 4-6 paragrafi o sezioni con funzione editoriale chiara;\n- formato_suggerito: formato e indicazioni mobile-first;\n- timing: quando pubblicare e perché;\n- fonti_da_verificare: array di fonti primarie o controlli concreti;\n- link_interno: pagina o cluster interno da collegare;\n- rischi_note: rischi fattuali, legali, reputazionali, deontologici o di titolo (segnala esplicitamente se il tema tocca vittime non identificate, suicidio, minori o salute: in quei casi consiglio_editoriale deve essere prudente);\n- azioni_consigliate: array ordinato di passi eseguibili dalla redazione;\n- scelte_editoriali: array di 3-5 scelte motivate in prima persona (bilanciamento delle fonti, cosa è verificato e da quante fonti, cosa manca e come completarlo, perché il titolo scelto batte le alternative);\n- bozza_articolo: array di 4-6 paragrafi PRONTI per il CMS, scritti ESCLUSIVAMENTE dai fatti presenti in materiale_fonti, con attribuzioni esplicite («secondo…», virgolettati solo se presenti nelle fonti) e condizionale dove non confermato; array vuoto se materiale_fonti è insufficiente, spiegandolo in scelte_editoriali;\n- stima_potenziale: stima onesta e prudente della distribuzione attesa (range di click) e perché.\n\nPer ogni titolo valuta implicitamente lunghezza, leggibilità mobile, entità riconoscibile e tensione informativa. Evita clickbait vuoto, formule generiche e affermazioni non sostenute. La nota editoriale deve poter dire anche “non pubblicare” quando le evidenze non bastano.\nContesto: {context}\nObiettivo: {goal}\nDati: {json.dumps({k:row.get(k,"") for k in keys},ensure_ascii=False,default=str)}'''
def generate_brief(row,mode="Regole locali",provider="OpenAI",model="",client_context="",goal="Crescita organica"):
    if mode=="Regole locali": return local_brief(row,client_context,goal),None
    try:
        prompt=_prompt(row,client_context,goal)
        if provider=="Anthropic":
            from anthropic import Anthropic
            key=os.getenv("ANTHROPIC_API_KEY"); assert key,"ANTHROPIC_API_KEY mancante"
            text=Anthropic(api_key=key).messages.create(model=model or "claude-3-5-sonnet-latest",max_tokens=3000,messages=[{"role":"user","content":prompt}]).content[0].text
        else:
            from openai import OpenAI
            key=os.getenv("OPENAI_API_KEY"); assert key,"OPENAI_API_KEY mancante"
            text=OpenAI(api_key=key).chat.completions.create(model=model or "gpt-4o-mini",messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"}).choices[0].message.content
        return _parse(text),None
    except Exception as e: return local_brief(row,client_context,goal),f"Fallback alle regole locali: {e}"
