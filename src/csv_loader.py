import io
import re
import pandas as pd

ALIASES = {
    "url": ["url", "page", "pages", "top_pages", "top page", "pagina", "pagine", "landing_page"],
    "clicks": ["clicks", "click", "clic"],
    "impressions": ["impressions", "impressioni"],
    "ctr": ["ctr", "click_through_rate", "percentuale_di_clic"],
    "title": ["title", "titolo"], "position": ["position", "posizione"],
}

def _key(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def _number(value):
    if pd.isna(value) or value == "": return 0.0
    text = str(value).strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else: text = text.replace(",", ".")
    return pd.to_numeric(text, errors="coerce") if text else 0.0

def normalize_gsc_export(df):
    if df is None or df.empty: return pd.DataFrame(columns=["url", "clicks", "impressions", "ctr", "title", "position"])
    lookup = {_key(c): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    for target, aliases in ALIASES.items():
        source = next((lookup.get(_key(a)) for a in aliases if lookup.get(_key(a))), None)
        out[target] = df[source] if source else ("" if target in ("url", "title") else 0)
    out["url"] = out["url"].fillna("").astype(str).str.strip()
    out["title"] = out["title"].fillna("").astype(str)
    for col in ("clicks", "impressions", "position"): out[col] = out[col].map(_number).fillna(0).astype(float)
    def ctr(v):
        if pd.isna(v) or v == "": return 0.0
        s = str(v).strip(); n = float(_number(s) or 0)
        if "%" in s or n > 1: n /= 100
        return max(0.0, min(n, 1.0))
    out["ctr"] = out["ctr"].map(ctr)
    missing = (out["ctr"] == 0) & (out["impressions"] > 0)
    out.loc[missing, "ctr"] = out.loc[missing, "clicks"] / out.loc[missing, "impressions"]
    return out[out["url"].ne("")].reset_index(drop=True)

def read_csv(upload):
    if upload is None: return None
    raw = upload.getvalue() if hasattr(upload, "getvalue") else open(upload, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try: return pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError): continue
    raise ValueError("CSV non leggibile: controlla codifica e separatore.")

