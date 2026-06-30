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
    keys=["url","title","clicks_current","impressions_current","ctr_current","growth_pct","status","opportunity_score","topic","keywords","h1","meta_description","paragraph_context","fresh_research_summary","competitor_domains_found","fresh_angles"]
    philosophy=_philosophy()
    return f'''Sei l'editor SEO di una testata news italiana. Filosofia editoriale (vincolante):\n{philosophy}\n\nCrea un brief in italiano, solo JSON valido, con chiavi: titolo_consigliato, angolo, target, formato_suggerito, cta, outline (array), query_ricerca, angoli_mancanti, perche_funziona, rischi_note, azioni_consigliate (array). Priorità: titolo ad alto CTR senza clickbait ingannevole, formato news breve (4-6 paragrafi), freschezza.\nContesto: {context}\nObiettivo: {goal}\nDati: {json.dumps({k:row.get(k,"") for k in keys},ensure_ascii=False,default=str)}'''
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
