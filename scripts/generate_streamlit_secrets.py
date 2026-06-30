"""Generate a Git-ignored Streamlit secrets file from the local GSC OAuth token."""
import json
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[1]
config=yaml.safe_load((ROOT/"gsc_config.yaml").read_text(encoding="utf-8"))
gsc=config["gsc"]
token_path=Path(gsc.get("token_path") or Path(gsc["credentials_path"]).with_name("gsc-token.json"))
token=json.loads(token_path.read_text(encoding="utf-8"))

def value(item):
    return json.dumps(str(item),ensure_ascii=False)

content=f'''[gsc]
property = {value(gsc["property"])}
appearance = {value(gsc.get("appearance","discover"))}
dimension = {value(gsc.get("dimension","page"))}
row_limit = {int(gsc.get("row_limit",250))}
range_days = 90

[google_oauth]
client_id = {value(token["client_id"])}
client_secret = {value(token["client_secret"])}
refresh_token = {value(token["refresh_token"])}
token_uri = {value(token.get("token_uri","https://oauth2.googleapis.com/token"))}
'''
destination=ROOT/".streamlit"/"secrets.toml"
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(content,encoding="utf-8")
print(f"Creato: {destination}")
