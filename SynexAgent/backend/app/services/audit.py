import json,os,sqlite3
from datetime import datetime,timezone
from pathlib import Path

DEFAULT=Path(__file__).resolve().parents[2]/'data'/'audit.sqlite3'
class AuditStore:
    def __init__(self,path=None):
        self.path=str(path or os.getenv('SYNEX_AUDIT_PATH',DEFAULT))
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, timestamp TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_events_patient_id_id ON events(patient_id,id)')
            db.execute('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, payload TEXT NOT NULL)')
    def connect(self):return sqlite3.connect(self.path,timeout=15)
    def record(self,pid,event,detail):
        with self.connect() as db:
            db.execute('INSERT INTO events(patient_id,timestamp,event,detail) VALUES(?,?,?,?)',(pid,datetime.now(timezone.utc).isoformat(),event,json.dumps(detail,ensure_ascii=False)))
    def save_analysis(self,payload):
        with self.connect() as db:
            db.execute('INSERT INTO analyses VALUES(?,?,?)',(payload['analysis_id'],payload['patient_id'],json.dumps(payload,ensure_ascii=False)))
    def get_analysis(self,aid):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM analyses WHERE id=?',(aid,)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self,pid):
        with self.connect() as db:
            rows=db.execute('SELECT id,timestamp,event,detail FROM events WHERE patient_id=? ORDER BY id DESC LIMIT 200',(pid,)).fetchall()
        return [{'id':r[0],'timestamp':r[1],'event':r[2],'detail':json.loads(r[3])} for r in rows]
