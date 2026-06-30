import io
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DEFAULT_DB = Path("data/content_intelligence.db")

def _connect(path=DEFAULT_DB):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(path)
    connection.execute("""CREATE TABLE IF NOT EXISTS gsc_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        label TEXT NOT NULL,
        short_json TEXT,
        long_json TEXT,
        analyzed_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL
    )""")
    return connection

def _dump_frame(frame):
    return "" if frame is None else frame.to_json(orient="records",force_ascii=False,date_format="iso")

def _load_frame(value):
    return None if not value else pd.read_json(io.StringIO(value),orient="records")

def save_snapshot(analyzed,short_df=None,long_df=None,label="Import GSC",metadata=None,path=DEFAULT_DB):
    created=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect(path)) as connection:
        cursor=connection.execute("INSERT INTO gsc_snapshots(created_at,label,short_json,long_json,analyzed_json,metadata_json) VALUES(?,?,?,?,?,?)",
            (created,label,_dump_frame(short_df),_dump_frame(long_df),_dump_frame(analyzed),json.dumps(metadata or {},ensure_ascii=False,default=str)))
        connection.commit()
        return cursor.lastrowid

def list_snapshots(path=DEFAULT_DB):
    with closing(_connect(path)) as connection:
        rows=connection.execute("SELECT id,created_at,label,metadata_json FROM gsc_snapshots ORDER BY id DESC").fetchall()
    return [{"id":r[0],"created_at":r[1],"label":r[2],"metadata":json.loads(r[3] or "{}")} for r in rows]

def load_snapshot(snapshot_id=None,path=DEFAULT_DB):
    with closing(_connect(path)) as connection:
        if snapshot_id is None:
            row=connection.execute("SELECT id,created_at,label,short_json,long_json,analyzed_json,metadata_json FROM gsc_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        else:
            row=connection.execute("SELECT id,created_at,label,short_json,long_json,analyzed_json,metadata_json FROM gsc_snapshots WHERE id=?",(int(snapshot_id),)).fetchone()
    if not row: return None
    return {"id":row[0],"created_at":row[1],"label":row[2],"short_df":_load_frame(row[3]),"long_df":_load_frame(row[4]),"analyzed":_load_frame(row[5]),"metadata":json.loads(row[6] or "{}")}
