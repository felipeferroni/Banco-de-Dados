from scipy.stats import beta

def posterior(a,b,alpha=1,beta0=1,cred=0.95):
    aa=a+alpha; bb=b+beta0; q=(1-cred)/2
    return aa/(aa+bb),float(beta.ppf(q,aa,bb)),float(beta.ppf(1-q,aa,bb))
