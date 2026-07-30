from __future__ import annotations
import math, zlib
import numpy as np, pandas as pd
from .frequency import association
from .entropy import information
from .bayes import posterior
from .fisher import significance
from .bootstrap import bootstrap_rate
from .leakage import classify_gene

def run_engine(hist,labels,dictionary,cfg):
    label_map=dict(zip(labels.trade_uid.astype(str),labels.rotulo.astype(str).str.upper()))
    rows=[]; universe=[]
    for _,r in hist.iterrows():
        uid=str(r.trade_uid); lab=label_map.get(uid)
        if lab not in (cfg['classe_positiva'],cfg['classe_negativa']):continue
        gids=set(str(r.gene_ids).split('|')) if pd.notna(r.gene_ids) else set()
        universe.append((uid,1 if lab==cfg['classe_positiva'] else 0,gids))
    total=len(universe); total_pos=sum(y for _,y,_ in universe); total_neg=total-total_pos
    lookup=dictionary.set_index('gene_id').to_dict('index')
    all_ids=sorted(dictionary.gene_id.astype(str).unique())
    for i,gid in enumerate(all_ids):
        meta=lookup[gid]; present=[y for _,y,gs in universe if gid in gs]
        a=sum(present); b=len(present)-a; c=total_pos-a; d=total_neg-b
        support,base,conf,lift,lev,conv=association(a,b,c,d)
        ent,ig,mi=information(a,b,c,d)
        post,lo,hi=posterior(a,b,cfg['prior_beta']['alpha'],cfg['prior_beta']['beta'],cfg['credibilidade'])
        odds,pf,chi2,pc,phi=significance(a,b,c,d)
        seed=(cfg['seed']+zlib.crc32(gid.encode())) & 0xffffffff
        bm,blo,bhi,bsd=bootstrap_rate(present,cfg['bootstrap_repeticoes'],seed,cfg['credibilidade'])
        status,motivo=classify_gene(meta.get('gene_key'),meta.get('source_plugin'),cfg)
        rows.append({'gene_id':gid,'gene_key':meta.get('gene_key'),'family':meta.get('family'),'source_plugin':meta.get('source_plugin'),'status_elegibilidade':status,'motivo_elegibilidade':motivo,
        'historias_total':total,'historias_com_gene':a+b,'historias_sem_gene':c+d,'gain_com_gene':a,'stop_com_gene':b,'gain_sem_gene':c,'stop_sem_gene':d,
        'cobertura_pct':100*support,'taxa_gain_gene_pct':100*conf,'taxa_gain_base_pct':100*base,'lift_gain':lift,'leverage':lev,'conviction':conv,
        'entropia_alvo':ent,'information_gain':ig,'mutual_information':mi,'odds_ratio':odds,'fisher_p':pf,'chi2':chi2,'chi2_p':pc,'phi_mcc':phi,
        'bayes_media_pct':100*post,'bayes_ic_inferior_pct':100*lo,'bayes_ic_superior_pct':100*hi,
        'bootstrap_media_pct':None if bm is None else 100*bm,'bootstrap_ic_inferior_pct':None if blo is None else 100*blo,'bootstrap_ic_superior_pct':None if bhi is None else 100*bhi,'bootstrap_desvio_pp':None if bsd is None else 100*bsd})
    return pd.DataFrame(rows).sort_values('gene_id').reset_index(drop=True),pd.DataFrame([{'trade_uid':u,'alvo_gain':y,'quantidade_genes':len(g)} for u,y,g in universe])
