from __future__ import annotations
import hashlib, json
from pathlib import Path
import pandas as pd

def read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [str(c).lstrip("\ufeff") for c in df.columns]
    return df

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def stable_id(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12].upper()}"

def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")

def write_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')
