def classify_gene(key,plugin,cfg):
    up=str(key).upper()
    if any(up.startswith(p.upper()) for p in cfg['leakage']['prefixos_proibidos']): return 'PROIBIDO_META','Metadado documental'
    hits=[t for t in cfg['leakage']['termos_proibidos'] if t.upper() in up]
    if hits:return 'PROIBIDO_VAZAMENTO','Termo associado ao resultado/certificação: '+','.join(hits[:4])
    return 'ELEGIVEL_MEDICAO','Sem indicador direto de vazamento'
