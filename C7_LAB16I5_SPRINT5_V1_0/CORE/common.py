from __future__ import annotations
from pathlib import Path
import hashlib, json, pandas as pd

def read_csv(path: Path) -> pd.DataFrame:
    df=pd.read_csv(path,sep=None,engine='python',encoding='utf-8-sig')
    df.columns=[str(c).lstrip('\ufeff') for c in df.columns]
    return df

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def stable_id(prefix: str, *parts: str) -> str:
    raw='|'.join(map(str,parts)).encode('utf-8')
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:12].upper()}"

def write_csv(df: pd.DataFrame,path: Path):
    df.to_csv(path,index=False,encoding='utf-8-sig',float_format='%.12g',lineterminator='\n')

def dump_json(obj,path: Path):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
