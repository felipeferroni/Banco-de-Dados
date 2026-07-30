from __future__ import annotations
import sys
from pathlib import Path
ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path: sys.path.insert(0, str(ROOT_PATH))
import argparse, json, math, sqlite3
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from CORE.common import read_csv, sha256_file, stable_id, write_csv, write_json

def select_k(X, min_k, max_k, seed, min_size):
    best=None
    upper=min(max_k, max(min_k, len(X)//min_size))
    for k in range(min_k, upper+1):
        km=KMeans(n_clusters=k, random_state=seed, n_init=20, algorithm='lloyd')
        labels=km.fit_predict(X)
        counts=np.bincount(labels)
        if counts.min() < min_size: continue
        score=float(silhouette_score(X, labels, sample_size=min(2000,len(X)), random_state=seed))
        cand=(score,-k,k,km,labels)
        if best is None or cand[:2] > best[:2]: best=cand
    if best is None:
        k=min_k
        km=KMeans(n_clusters=k, random_state=seed, n_init=20, algorithm='lloyd')
        labels=km.fit_predict(X)
        return k, km, labels, float('nan')
    return best[2],best[3],best[4],best[0]

def top_tokens(series, n=5):
    toks=[]
    for v in series.fillna(''):
        toks += [x.strip() for x in str(v).split('|') if x.strip()]
    if not toks: return ''
    vc=pd.Series(toks).value_counts()
    return '|'.join(vc.head(n).index.astype(str))

def main(root: Path):
    cfg=json.loads((root/'CONFIG/config.json').read_text(encoding='utf-8'))
    inp=root/'INPUT'; out=root/'RELATORIOS'; out.mkdir(exist_ok=True)
    dna=read_csv(inp/'reconstructed_dna.csv')
    comps=read_csv(inp/'reconstructed_dna_components.csv')
    roles=read_csv(inp/'gene_roles_reconstructed.csv')
    famprof=read_csv(inp/'family_profiles_reconstructed.csv')
    numeric=[c for c in cfg['features']['numeric'] if c in dna.columns]
    categorical=[c for c in cfg['features']['categorical'] if c in dna.columns]
    model_df=dna[numeric+categorical].copy()
    for c in numeric: model_df[c]=pd.to_numeric(model_df[c],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(model_df[c].median())
    for c in categorical: model_df[c]=model_df[c].fillna('DESCONHECIDO').astype(str)
    pre=ColumnTransformer([('num',StandardScaler(),numeric),('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),categorical)], remainder='drop')
    X=pre.fit_transform(model_df)
    k, km, labels, sil=select_k(X,cfg['cluster_search']['min_k'],cfg['cluster_search']['max_k'],cfg['seed'],cfg['cluster_search']['minimum_cluster_size'])
    dna=dna.copy(); dna['_cluster']=labels
    # canonical deterministic cluster ordering by descending mean reconstruction score, then cluster id
    order=(dna.groupby('_cluster')['reconstruction_score_0_100'].mean().sort_values(ascending=False).index.tolist())
    cmap={old:i+1 for i,old in enumerate(order)}
    dna['narrative_number']=dna['_cluster'].map(cmap)
    dna['narrative_id']=dna['narrative_number'].map(lambda n:f'NARRATIVA_{n:03d}')
    # narrative profiles
    rows=[]
    base_gain=float(pd.to_numeric(dna['taxa_gain_base_pct'],errors='coerce').median()) if 'taxa_gain_base_pct' in dna else np.nan
    for n,g in dna.groupby('narrative_number',sort=True):
        nid=f'NARRATIVA_{n:03d}'
        ids=set(g['reconstructed_dna_id'].astype(str))
        cg=comps[comps['reconstructed_dna_id'].astype(str).isin(ids)]
        top_genes='|'.join(cg['gene_key'].value_counts().head(8).index.astype(str)) if len(cg) else ''
        top_fams=top_tokens(g['families'],5)
        gain=float(pd.to_numeric(g['taxa_gain_pct'],errors='coerce').mean())
        lift=float(pd.to_numeric(g['lift_gain'],errors='coerce').mean())
        score=float(pd.to_numeric(g['reconstruction_score_0_100'],errors='coerce').mean())
        coherence=float(pd.to_numeric(g['coherence_score_0_100'],errors='coerce').mean())
        direction='ASSOCIACAO_GAIN' if gain>base_gain+3 else ('ASSOCIACAO_STOP' if gain<base_gain-3 else 'NEUTRA')
        descriptor=f"{direction}; familias={top_fams or 'DESCONHECIDA'}; fonte={g['source_type'].mode().iloc[0]}"
        rows.append({'narrative_id':nid,'narrative_rank':n,'dna_count':len(g),'coverage_pct':100*len(g)/len(dna),
            'mean_gain_pct':gain,'base_gain_pct':base_gain,'mean_lift_gain':lift,'mean_reconstruction_score':score,
            'mean_coherence_score':coherence,'dominant_source_type':g['source_type'].mode().iloc[0],
            'dominant_evidence_band':g['evidence_band'].mode().iloc[0], 'dominant_families':top_fams,
            'dominant_genes':top_genes,'outcome_association':direction,'emergent_descriptor':descriptor,
            'scientific_status':'NARRATIVA_LATENTE_CANDIDATA','operational_status':'NAO_OPERACIONAL'})
    narratives=pd.DataFrame(rows)
    assignments=dna[['reconstructed_dna_id','rank_reconstruction','source_type','source_candidate_id','gene_signature','families','taxa_gain_pct','lift_gain','reconstruction_score_0_100','narrative_id']].copy()
    assignments['assignment_method']='KMEANS_DETERMINISTICO'
    assignments['operational_status']='NAO_OPERACIONAL'
    # structural relationships between narrative centroids, not temporal transitions
    centers={cmap[old]:km.cluster_centers_[old] for old in order}
    rel=[]
    for a in sorted(centers):
      for b in sorted(centers):
        if a>=b: continue
        va,vb=centers[a],centers[b]
        sim=float(np.dot(va,vb)/(np.linalg.norm(va)*np.linalg.norm(vb)+1e-12))
        rel.append({'narrative_a':f'NARRATIVA_{a:03d}','narrative_b':f'NARRATIVA_{b:03d}','cosine_similarity':sim,'structural_distance':float(np.linalg.norm(va-vb)),'relationship_type':'SIMILARIDADE_ESTRUTURAL_NAO_TEMPORAL'})
    relationships=pd.DataFrame(rel)
    readiness=pd.DataFrame([{'temporal_transitions_inferred':False,'reason':'Entradas LAB16I5 nao contem eixo temporal por historia; transicoes temporais nao foram fabricadas.','required_future_input':'sequencia cronologica de narrativas por trade/data_hora','classification':'LIMITACAO_CIENTIFICA_DOCUMENTADA'}])
    write_csv(narratives,out/'narratives.csv'); write_csv(assignments,out/'dna_narrative_assignments.csv'); write_csv(relationships,out/'narrative_relationships.csv'); write_csv(readiness,out/'temporal_transition_readiness.csv')
    # enriched dictionary
    dct=read_csv(inp/'reconstruction_dictionary.csv')
    gene_narr=(comps.merge(assignments[['reconstructed_dna_id','narrative_id']],on='reconstructed_dna_id').groupby('gene_id')['narrative_id'].agg(lambda s:'|'.join(sorted(set(s)))).reset_index(name='narratives_present'))
    dct=dct.merge(gene_narr,on='gene_id',how='left'); dct['status_lab17']=np.where(dct['narratives_present'].notna(),'PARTICIPA_NARRATIVA','NAO_PARTICIPA_NARRATIVA')
    write_csv(dct,out/'narrative_dictionary.csv')
    # sqlite
    db=out/'narrative_engine.sqlite'
    if db.exists(): db.unlink()
    con=sqlite3.connect(db)
    for name,df in [('narratives',narratives),('dna_narrative_assignments',assignments),('narrative_relationships',relationships),('temporal_transition_readiness',readiness),('narrative_dictionary',dct)]: df.to_sql(name,con,index=False)
    con.close()
    outputs=['narratives.csv','dna_narrative_assignments.csv','narrative_relationships.csv','temporal_transition_readiness.csv','narrative_dictionary.csv','narrative_engine.sqlite']
    inputs=['reconstructed_dna.csv','reconstructed_dna_components.csv','gene_roles_reconstructed.csv','family_profiles_reconstructed.csv','reconstruction_dictionary.csv','dna_reconstruction.sqlite','reconstruction_manifest.json']
    manifest={'project':'C7','laboratory':'LAB17','version':'1.0.0','status':'EXECUTADO','architecture_frozen':True,
      'scope':'Descoberta científica de estados narrativos latentes; sem decisão operacional','narrative_is_operational':False,
      'scientific_hypothesis':'DNAs reconstruídos se organizam em estados latentes recorrentes que podem ser descritos como narrativas emergentes.',
      'counts':{'dna_input':len(dna),'narratives':len(narratives),'assignments':len(assignments),'relationships':len(relationships)},
      'model':{'algorithm':'KMeans','selected_k':k,'silhouette':None if math.isnan(sil) else sil,'seed':cfg['seed'],'cluster_order':'mean_reconstruction_score_desc'},
      'temporal_inference':{'performed':False,'reason':'ausencia_de_eixo_temporal_nas_entradas_oficiais'},
      'inputs_sha256':{f:sha256_file(inp/f) for f in inputs if (inp/f).exists()}, 'outputs_sha256':{f:sha256_file(out/f) for f in outputs}}
    write_json(manifest,out/'narrative_manifest.json')
    print(json.dumps(manifest['counts'],ensure_ascii=False)); print('selected_k',k,'silhouette',sil)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args(); main(Path(a.root))
