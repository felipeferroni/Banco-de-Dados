from pathlib import Path
import pandas as pd, sqlite3
ROOT=Path(__file__).resolve().parents[1]; O=ROOT/'RELATORIOS'
n=pd.read_csv(O/'narratives.csv',encoding='utf-8-sig'); a=pd.read_csv(O/'dna_narrative_assignments.csv',encoding='utf-8-sig')
assert n['narrative_id'].is_unique
assert a['reconstructed_dna_id'].is_unique
assert set(a['narrative_id'])<=set(n['narrative_id'])
con=sqlite3.connect(O/'narrative_engine.sqlite'); c=con.execute('select count(*) from narratives').fetchone()[0]; con.close(); assert c==len(n)
print('INTEGRIDADE_APROVADA')
