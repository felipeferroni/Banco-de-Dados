import numpy as np

def bootstrap_rate(y_present,reps,seed,cred=.95):
    y=np.asarray(y_present,dtype=float); n=len(y)
    if n==0:return None,None,None,None
    rng=np.random.default_rng(seed)
    # Para variável Bernoulli, reamostrar n observações equivale a Binomial(n, p_amostral).
    means=rng.binomial(n,float(y.mean()),size=reps)/n
    q=(1-cred)/2
    return float(means.mean()),float(np.quantile(means,q)),float(np.quantile(means,1-q)),float(means.std(ddof=1))
