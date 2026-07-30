from __future__ import annotations
from pathlib import Path
import csv, hashlib, json
import pandas as pd

def read_csv_auto(path: Path, **kwargs) -> pd.DataFrame:
    with path.open('r',encoding='utf-8-sig',errors='replace') as f: sample=f.read(8192)
    try: sep=csv.Sniffer().sniff(sample,delimiters=';,\t').delimiter
    except csv.Error: sep=';'
    return pd.read_csv(path,sep=sep,encoding='utf-8-sig',**kwargs)

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def write_csv(df: pd.DataFrame,path: Path):
    df.to_csv(path,sep=';',index=False,encoding='utf-8-sig',float_format='%.12g')

def write_json(obj,path: Path): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
