from __future__ import annotations
import math
import pandas as pd
from .common import stable_id

def _num(x,default=0.0):
    try:
        v=float(x)
        return default if math.isnan(v) else v
    except Exception: return default

def evidence_band(score, bands):
    if score>=bands['MUITO_ALTA']: return 'EVIDENCIA_MUITO_ALTA'
    if score>=bands['ALTA']: return 'EVIDENCIA_ALTA'
    if score>=bands['MODERADA']: return 'EVIDENCIA_MODERADA'
    return 'EVIDENCIA_BAIXA'

def reconstruct(genes:pd.DataFrame,pairs:pd.DataFrame,triplets:pd.DataFrame,cfg:dict):
    gmap=genes.set_index('gene_id').to_dict('index')
    rows=[]; comps=[]
    weights=cfg['reconstruction']['score_weights']; bands=cfg['reconstruction']['evidence_bands']
    sources=[]
    if cfg['reconstruction']['include_pairs']:
        for _,r in pairs.iterrows(): sources.append(('PAIR',r,[r['gene_a'],r['gene_b']]))
    if cfg['reconstruction']['include_triplets']:
        for _,r in triplets.iterrows(): sources.append(('TRIPLET',r,[r['gene_a'],r['gene_b'],r['gene_c']]))
    for kind,r,gids in sources:
        gids=sorted(map(str,gids))
        dna_id=stable_id('RDNA',kind,*gids)
        interaction=_num(r.get('indice_candidato_0_100'))
        g_scores=[_num(gmap.get(g,{}).get('indice_candidato_0_100')) for g in gids]
        present=sum(1 for g in gids if g in gmap)
        comp_mean=sum(g_scores)/len(g_scores) if g_scores else 0
        fams=[str(gmap.get(g,{}).get('family','DESCONHECIDA')) for g in gids]
        unique_fams=len(set(fams)); coherence=100*(1-(unique_fams-1)/max(1,len(gids)-1)) if len(gids)>1 else 100
        parsimony=100 if len(gids)==2 else 80
        score=(weights['interaction_score']*interaction + weights['component_gene_score']*comp_mean + weights['coherence']*coherence + weights['parsimony']*parsimony)
        histories=int(_num(r.get('historias'))); gain=int(_num(r.get('gain'))); stop=int(_num(r.get('stop')))
        signature=' + '.join(str(gmap.get(g,{}).get('gene_key',g)) for g in gids)
        rows.append({
          'reconstructed_dna_id':dna_id,'source_type':kind,'source_candidate_id':r.get('candidate_id',''),
          'source_interaction_id':r.get('interaction_id',''),'component_count':len(gids),'components_present_in_candidates':present,
          'gene_ids':'|'.join(gids),'gene_signature':signature,'families':'|'.join(fams),'distinct_families':unique_fams,
          'historias':histories,'gain':gain,'stop':stop,'taxa_gain_pct':_num(r.get('taxa_gain_pct')),
          'taxa_gain_base_pct':_num(r.get('taxa_gain_base_pct')),'lift_gain':_num(r.get('lift_gain')),
          'fisher_p':_num(r.get('fisher_p'),1.0),'bootstrap_ic_inferior_pct':_num(r.get('bootstrap_ic_inferior_pct')),
          'interaction_score_0_100':interaction,'component_score_mean_0_100':comp_mean,'coherence_score_0_100':coherence,
          'parsimony_score_0_100':parsimony,'reconstruction_score_0_100':score,'evidence_band':evidence_band(score,bands),
          'scientific_status':'DNA_RECONSTRUIDO_CANDIDATO','operational_status':'NAO_OPERACIONAL'
        })
        maxg=max(g_scores) if g_scores else 0
        for i,g in enumerate(gids,1):
            gs=g_scores[i-1]
            role='NUCLEO' if maxg and gs>=cfg['reconstruction']['role_thresholds']['nucleo_min_relative_score']*maxg else 'SUPORTE'
            comps.append({'reconstructed_dna_id':dna_id,'component_order':i,'gene_id':g,
              'gene_key':gmap.get(g,{}).get('gene_key',g),'family':gmap.get(g,{}).get('family','DESCONHECIDA'),
              'source_plugin':gmap.get(g,{}).get('source_plugin',''),'gene_candidate_score_0_100':gs,
              'component_role':role,'component_required_in_signature':True})
    out=pd.DataFrame(rows).sort_values(['reconstruction_score_0_100','historias','reconstructed_dna_id'],ascending=[False,False,True],kind='mergesort').reset_index(drop=True)
    out.insert(1,'rank_reconstruction',range(1,len(out)+1))
    comp=pd.DataFrame(comps).sort_values(['reconstructed_dna_id','component_order'],kind='mergesort').reset_index(drop=True)
    return out,comp

def build_gene_roles(recon,components):
    if components.empty: return pd.DataFrame()
    agg=components.groupby(['gene_id','gene_key','family','source_plugin'],as_index=False).agg(
      dna_count=('reconstructed_dna_id','nunique'),nucleus_count=('component_role',lambda s:(s=='NUCLEO').sum()),
      mean_gene_score=('gene_candidate_score_0_100','mean'))
    top=recon[['reconstructed_dna_id','reconstruction_score_0_100']].merge(components[['reconstructed_dna_id','gene_id']],on='reconstructed_dna_id')
    rs=top.groupby('gene_id',as_index=False).agg(mean_reconstruction_score=('reconstruction_score_0_100','mean'),max_reconstruction_score=('reconstruction_score_0_100','max'))
    agg=agg.merge(rs,on='gene_id',how='left')
    agg['nucleus_ratio']=agg['nucleus_count']/agg['dna_count'].clip(lower=1)
    agg['global_role']=agg['nucleus_ratio'].map(lambda x:'GENE_NUCLEO_RECORRENTE' if x>=.7 else ('GENE_MISTO' if x>=.3 else 'GENE_SUPORTE_RECORRENTE'))
    return agg.sort_values(['mean_reconstruction_score','dna_count','gene_id'],ascending=[False,False,True],kind='mergesort').reset_index(drop=True)

def build_family_profiles(recon,components):
    if components.empty:return pd.DataFrame()
    x=components.merge(recon[['reconstructed_dna_id','reconstruction_score_0_100','source_type']],on='reconstructed_dna_id')
    a=x.groupby('family',as_index=False).agg(dna_count=('reconstructed_dna_id','nunique'),component_occurrences=('gene_id','size'),unique_genes=('gene_id','nunique'),mean_reconstruction_score=('reconstruction_score_0_100','mean'),max_reconstruction_score=('reconstruction_score_0_100','max'))
    a['family_profile_id']=a['family'].map(lambda v:stable_id('FPROF',v))
    return a[['family_profile_id','family','dna_count','component_occurrences','unique_genes','mean_reconstruction_score','max_reconstruction_score']].sort_values(['mean_reconstruction_score','dna_count'],ascending=[False,False],kind='mergesort').reset_index(drop=True)
