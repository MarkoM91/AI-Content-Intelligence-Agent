from datetime import date,timedelta
import pandas as pd,yaml
def load_config(path="gsc_config.yaml"):
    with open(path,encoding="utf-8") as f: return yaml.safe_load(f)
def fetch_gsc(config,days=3,end_date=None):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    g=config["gsc"]; end=end_date or date.today()-timedelta(days=2); start=end-timedelta(days=days-1)
    flow=InstalledAppFlow.from_client_secrets_file(g["credentials_path"],["https://www.googleapis.com/auth/webmasters.readonly"]); creds=flow.run_local_server(port=0)
    body={"startDate":str(start),"endDate":str(end),"dimensions":[g.get("dimension","page")],"rowLimit":g.get("row_limit",250),"type":"discover" if str(g.get("appearance","web")).lower()=="discover" else "web"}
    result=build("searchconsole","v1",credentials=creds).searchanalytics().query(siteUrl=g["property"],body=body).execute()
    rows=[{"url":r.get("keys",[""])[0],"clicks":r.get("clicks",0),"impressions":r.get("impressions",0),"ctr":r.get("ctr",0),"position":r.get("position",0)} for r in result.get("rows",[])]
    return pd.DataFrame(rows),{"start":str(start),"end":str(end),"type":body["type"],"rows":len(rows)}
