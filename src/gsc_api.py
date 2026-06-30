from datetime import date,timedelta
from pathlib import Path
import pandas as pd,yaml
def load_config(path="gsc_config.yaml"):
    with open(path,encoding="utf-8") as f: return yaml.safe_load(f)
SCOPES=["https://www.googleapis.com/auth/webmasters.readonly"]

def get_credentials(config):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    g=config["gsc"]
    if g.get("authorized_user_info"):
        info=g["authorized_user_info"]
        creds=Credentials(token=None,refresh_token=info["refresh_token"],token_uri=info.get("token_uri","https://oauth2.googleapis.com/token"),client_id=info["client_id"],client_secret=info["client_secret"],scopes=SCOPES)
        creds.refresh(Request())
        return creds
    credentials_path=Path(g["credentials_path"])
    token_path=Path(g.get("token_path") or credentials_path.with_name("gsc-token.json"))
    creds=Credentials.from_authorized_user_file(token_path,SCOPES) if token_path.exists() else None
    if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
    if not creds or not creds.valid:
        flow=InstalledAppFlow.from_client_secrets_file(credentials_path,SCOPES); creds=flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True,exist_ok=True); token_path.write_text(creds.to_json(),encoding="utf-8")
    return creds

def fetch_gsc(config,days=3,end_date=None,credentials=None):
    from googleapiclient.discovery import build
    g=config["gsc"]; end=end_date or date.today()-timedelta(days=2); start=end-timedelta(days=days-1)
    creds=credentials or get_credentials(config)
    body={"startDate":str(start),"endDate":str(end),"dimensions":[g.get("dimension","page")],"rowLimit":g.get("row_limit",250),"type":"discover" if str(g.get("appearance","web")).lower()=="discover" else "web"}
    result=build("searchconsole","v1",credentials=creds).searchanalytics().query(siteUrl=g["property"],body=body).execute()
    rows=[{"url":r.get("keys",[""])[0],"clicks":r.get("clicks",0),"impressions":r.get("impressions",0),"ctr":r.get("ctr",0),"position":r.get("position",0)} for r in result.get("rows",[])]
    return pd.DataFrame(rows),{"start":str(start),"end":str(end),"type":body["type"],"rows":len(rows)}
