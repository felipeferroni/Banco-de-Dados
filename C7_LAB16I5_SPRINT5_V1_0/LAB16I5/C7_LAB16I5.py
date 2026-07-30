from __future__ import annotations
from pathlib import Path
import sys,time,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from CORE.common import read_csv,write_csv,dump_json,sha256_file
from CORE.reconstruction_engine import reconstruct,build_gene_roles,build_family_profiles
from CORE.sqlite_manager import write_database

def run(root:Path=ROOT):
    t=time.time(); cfg=json.loads((root/'CONFIG/config.json').read_text(encoding='utf-8'))
    inp=root/'INPUT'; out=root/'RELATORIOS'; out.mkdir(exist_ok=True)
    genes=read_csv(inp/'candidate_genes.csv'); pairs=read_csv(inp/'candidate_pairs.csv'); trips=read_csv(inp/'candidate_triplets.csv')
    fam=read_csv(inp/'candidate_families.csv'); dic=read_csv(inp/'candidate_dictionary.csv')
    recon,components=reconstruct(genes,pairs,trips,cfg)
    roles=build_gene_roles(recon,components); profiles=build_family_profiles(recon,components)
    dictionary=dic.merge(roles[['gene_id','dna_count','nucleus_count','mean_reconstruction_score','max_reconstruction_score','global_role']],on='gene_id',how='left')
    dictionary['status_lab16i5']=dictionary['dna_count'].notna().map({True:'PARTICIPA_RECONSTRUCAO',False:'NAO_PARTICIPA_RECONSTRUCAO'})
    files={'reconstructed_dna.csv':recon,'reconstructed_dna_components.csv':components,'gene_roles_reconstructed.csv':roles,'family_profiles_reconstructed.csv':profiles,'reconstruction_dictionary.csv':dictionary}
    for n,df in files.items(): write_csv(df,out/n)
    db=out/'dna_reconstruction.sqlite'
    metadata={'project':'C7','laboratory':'LAB16I5','version':'1.0.0','architecture_frozen':True,'operational':False}
    write_database(db,{'reconstructed_dna':recon,'reconstructed_dna_components':components,'gene_roles_reconstructed':roles,'family_profiles_reconstructed':profiles,'reconstruction_dictionary':dictionary,'candidate_families_input':fam},metadata)
    inputs_sha={n:sha256_file(inp/n) for n in cfg['inputs'] if (inp/n).exists()}
    output_names=list(files)+['dna_reconstruction.sqlite']
    outputs_sha={n:sha256_file(out/n) for n in output_names}
    manifest={'project':'C7','laboratory':'LAB16I5','version':'1.0.0','status':'EXECUTADO','architecture_frozen':True,
      'scope':cfg['scope'],'reconstruction_is_operational':False,'scientific_hypothesis':'Um DNA candidato pode ser reconstruído como assinatura explicável de genes e interações selecionadas.',
      'scientific_note':'As estruturas são reconstruções científicas relativas às entradas do LAB16I4. Não representam entradas, setups ou promessa de desempenho.',
      'configuration':cfg,'counts':{'candidate_genes_input':len(genes),'candidate_pairs_input':len(pairs),'candidate_triplets_input':len(trips),'reconstructed_dna':len(recon),'components':len(components),'genes_with_roles':len(roles),'family_profiles':len(profiles)},
      'inputs_sha256':inputs_sha,'outputs_sha256':outputs_sha,'elapsed_seconds':round(time.time()-t,3)}
    dump_json(manifest,out/'reconstruction_manifest.json')
    print(json.dumps(manifest['counts'],ensure_ascii=False,indent=2)); return manifest
if __name__=='__main__': run()
