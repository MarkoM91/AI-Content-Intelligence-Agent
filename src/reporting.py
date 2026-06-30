import json, math
def safe_int(v):
    try: return 0 if v is None or (isinstance(v,float) and math.isnan(v)) else int(float(v))
    except (ValueError,TypeError): return 0
def _clean(v): return "" if v is None or (isinstance(v,float) and math.isnan(v)) else v
def generate_markdown_report(analyzed,research_df=None,briefs=None,client="Cliente demo"):
    research_df=research_df if research_df is not None else []
    domains=[] if not hasattr(research_df,"columns") or "competitor_domain" not in research_df else sorted(x for x in research_df.competitor_domain.dropna().unique() if x)
    lines=[f"# AI Content Intelligence Report — {client}","",f"Contenuti analizzati: **{len(analyzed)}**  ",f"Fonti competitor/fresche: **{len(research_df)}**  ",f"Domini competitor: **{', '.join(domains) or 'nessuno / piano locale'}**","","## Opportunità principali",""]
    for _,r in analyzed.head(10).iterrows(): lines += [f"### {r.get('title') or r.get('topic')}",f"- URL: {r.get('url','')}",f"- Stato: **{r.get('status','')}** — score {r.get('opportunity_score',0)}",f"- Click: {safe_int(r.get('clicks_current'))}; impression: {safe_int(r.get('impressions_current'))}; CTR: {float(r.get('ctr_current',0) or 0):.1%}",f"- Angoli: {_clean(r.get('fresh_angles',''))}",f"- Gap: {_clean(r.get('fresh_research_summary',''))}",""]
    if briefs:
        lines += ["## Brief proposti",""]+[f"- **{b.get('titolo_consigliato','')}** — {b.get('angolo','')}" for b in briefs]
    return "\n".join(lines)
def generate_json_export(analyzed,research_df=None,briefs=None,approvals=None,metadata=None):
    records=lambda df: [] if df is None else [{k:_clean(v) for k,v in row.items()} for row in df.to_dict("records")]
    return json.dumps({"metadata":metadata or {},"analyzed":records(analyzed),"fresh_research":records(research_df),"briefs":briefs or [],"approvals":approvals or []},ensure_ascii=False,indent=2,default=str)
