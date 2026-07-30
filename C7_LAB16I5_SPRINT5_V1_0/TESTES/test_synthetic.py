from pathlib import Path
import sys,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from CORE.reconstruction_engine import reconstruct

def main():
 cfg={'reconstruction':{'include_pairs':True,'include_triplets':True,'score_weights':{'interaction_score':.5,'component_gene_score':.25,'coherence':.15,'parsimony':.1},'evidence_bands':{'MUITO_ALTA':80,'ALTA':70,'MODERADA':55,'BAIXA':0},'role_thresholds':{'nucleo_min_relative_score':.8}}}
 g=pd.DataFrame([{'gene_id':'G1','gene_key':'A','family':'F','source_plugin':'x','indice_candidato_0_100':90},{'gene_id':'G2','gene_key':'B','family':'F','source_plugin':'x','indice_candidato_0_100':80},{'gene_id':'G3','gene_key':'C','family':'Z','source_plugin':'x','indice_candidato_0_100':70}])
 p=pd.DataFrame([{'candidate_id':'P1','interaction_id':'I1','gene_a':'G1','gene_b':'G2','historias':10,'gain':8,'stop':2,'taxa_gain_pct':80,'taxa_gain_base_pct':50,'lift_gain':1.6,'fisher_p':.01,'bootstrap_ic_inferior_pct':60,'indice_candidato_0_100':88}])
 t=pd.DataFrame([{'candidate_id':'T1','interaction_id':'I2','gene_a':'G1','gene_b':'G2','gene_c':'G3','historias':9,'gain':7,'stop':2,'taxa_gain_pct':77.7,'taxa_gain_base_pct':50,'lift_gain':1.55,'fisher_p':.02,'bootstrap_ic_inferior_pct':55,'indice_candidato_0_100':82}])
 r,c=reconstruct(g,p,t,cfg)
 assert len(r)==2 and len(c)==5
 assert r['reconstructed_dna_id'].is_unique
 print('TESTE_SINTETICO_APROVADO')
if __name__=='__main__':main()
