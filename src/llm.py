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
    keys=["url","title","clicks_current","impressions_current","ctr_current","growth_pct","status","opportunity_score","topic","keywords","h1","meta_description","paragraph_context","fresh_research_summary","competitor_domains_found","fresh_angles","winning_cluster","winning_hook","entities","adjacency_type","adjacent_topic","proposed_argument","discover_potential","evidence_count","evidence_urls","editorial_decision","urgency","recommended_headline","editorial_advice","differentiation"]
    philosophy=_philosophy()
    return f'''Sei il direttore editoriale di una testata news italiana orientata a Google Discover. Filosofia editoriale (vincolante):\n{philosophy}\n\nDevi dare un consiglio operativo, non una descrizione generica. Parti dal cluster che ha già funzionato e dalle fonti disponibili. Restituisci solo JSON valido con chiavi: consiglio_editoriale (Pubblica ora, Prepara e valida, Monitora o Non prioritario), titolo_consigliato, varianti_titolo (array di 3), angolo, differenziazione, perche_adesso, target, formato_suggerito, timing, hook_apertura, cta, outline (array), fonti_da_verificare (array), rischi_note, azioni_consigliate (array). Spiega esattamente cosa pubblicare, perché ora e cosa aggiungere rispetto alle coperture esistenti. Non promettere risultati Discover e non produrre titoli generici.\nContesto: {context}\nObiettivo: {goal}\nDati: {json.dumps({k:row.get(k,"") for k in keys},ensure_ascii=False,default=str)}'''
def generate_brief(row,mode="Regole locali",provider="OpenAI",model="",client_context="",goal="Crescita organica"):
    if mode=="Regole locali": return local_brief(row,client_context,goal),None
    try:
        prompt=_prompt(row,client_context,goal)
        if provider=="Anthropic":
            from anthropic import Anthropic
            key=os.getenv("ANTHROPIC_API_KEY"); assert key,"ANTHROPIC_API_KEY mancante"
            text=Anthropic(api_key=key).messages.create(model=model or "claude-3-5-sonnet-latest",max_tokens=1800,messages=[{"role":"user","content":prompt}]).content[0].text
        else:
            from openai import OpenAI
            key=os.getenv("OPENAI_API_KEY"); assert key,"OPENAI_API_KEY mancante"
            text=OpenAI(api_key=key).chat.completions.create(model=model or "gpt-4o-mini",messages=[{"role":"user","content":prompt}],response_format={"type":"json_object"}).choices[0].message.content
        return _parse(text),None
    except Exception as e: return local_brief(row,client_context,goal),f"Fallback alle regole locali: {e}"
