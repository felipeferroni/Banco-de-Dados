from pathlib import Path
import hashlib, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
FILES=['narratives.csv','dna_narrative_assignments.csv','narrative_relationships.csv','temporal_transition_readiness.csv','narrative_dictionary.csv','narrative_engine.sqlite']
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.check_call([sys.executable,str(ROOT/'LAB17/EXECUTAR_TUDO.py')]); a={f:h(ROOT/'RELATORIOS'/f) for f in FILES}
subprocess.check_call([sys.executable,str(ROOT/'LAB17/EXECUTAR_TUDO.py')]); b={f:h(ROOT/'RELATORIOS'/f) for f in FILES}
assert a==b,(a,b)
print('DETERMINISMO_APROVADO')
