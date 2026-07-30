from pathlib import Path
import sys,hashlib,shutil,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from LAB16I5.C7_LAB16I5 import run
FILES=['reconstructed_dna.csv','reconstructed_dna_components.csv','gene_roles_reconstructed.csv','family_profiles_reconstructed.csv','reconstruction_dictionary.csv','reconstruction_manifest.json']
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run(ROOT); a={f:h(ROOT/'RELATORIOS'/f) for f in FILES if f!='reconstruction_manifest.json'}
 run(ROOT); b={f:h(ROOT/'RELATORIOS'/f) for f in FILES if f!='reconstruction_manifest.json'}
 assert a==b,(a,b)
 print('TESTE_DETERMINISMO_APROVADO')
if __name__=='__main__':main()
