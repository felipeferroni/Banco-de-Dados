import sqlite3, json
from pathlib import Path

def write_database(path:Path,tables:dict,metadata:dict):
    if path.exists(): path.unlink()
    con=sqlite3.connect(path)
    try:
      for name,df in tables.items(): df.to_sql(name,con,index=False,if_exists='replace')
      con.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
      con.executemany('INSERT INTO metadata(key,value) VALUES (?,?)',[(k,json.dumps(v,ensure_ascii=False,sort_keys=True)) for k,v in sorted(metadata.items())])
      con.commit()
    finally: con.close()
