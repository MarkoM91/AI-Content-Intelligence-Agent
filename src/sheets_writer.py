import pandas as pd

SHEET_SCOPES=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]

def _credentials(config):
    from google.oauth2 import service_account
    if config.get("service_account_info"):
        return service_account.Credentials.from_service_account_info(config["service_account_info"],scopes=SHEET_SCOPES)
    return service_account.Credentials.from_service_account_file(config["service_account_path"],scopes=SHEET_SCOPES)

def _values(frame):
    if frame is None: return [["Nessun dato"]]
    clean=frame.copy().replace([float("inf"),float("-inf")],"").fillna("")
    return [list(clean.columns)]+[[v.item() if hasattr(v,"item") else v for v in row] for row in clean.to_numpy()]

def _worksheet(book,title,rows=1000,cols=30):
    title=title[:100]
    try: sheet=book.worksheet(title)
    except Exception: sheet=book.add_worksheet(title=title,rows=rows,cols=cols)
    sheet.clear()
    return sheet

def write_site_results(config,site_name,analyzed,research):
    import gspread
    client=gspread.authorize(_credentials(config))
    book=client.open_by_key(config["spreadsheet_id"])
    perf=_worksheet(book,f"{site_name} — Performance",max(len(analyzed)+20,100),max(len(analyzed.columns)+3,20))
    perf.update(_values(analyzed),"A1")
    ideas=_worksheet(book,f"{site_name} — Ideas",max(len(research)+20,100),max(len(research.columns)+3,25))
    ideas.update(_values(research),"A1")
    for sheet in (perf,ideas):
        sheet.freeze(rows=1)
        sheet.format("1:1", {
            "backgroundColor": {"red": 0.12, "green": 0.18, "blue": 0.30},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        })
    return book.url

def write_overview(config,rows):
    import gspread
    client=gspread.authorize(_credentials(config)); book=client.open_by_key(config["spreadsheet_id"])
    frame=pd.DataFrame(rows)
    sheet=_worksheet(book,"Overview",max(len(frame)+20,100),max(len(frame.columns)+3,15))
    sheet.update(_values(frame),"A1"); sheet.freeze(rows=1)
    sheet.format("1:1",{"textFormat":{"bold":True}})
    return book.url
