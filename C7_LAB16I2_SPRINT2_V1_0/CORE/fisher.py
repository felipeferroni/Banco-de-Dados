import math
from scipy.stats import fisher_exact, chi2_contingency

def significance(a,b,c,d):
    table=[[a,b],[c,d]]
    odds,pf=fisher_exact(table,alternative='two-sided')
    try: chi2,pc,_,_=chi2_contingency(table,correction=False)
    except ValueError: chi2,pc=0.0,1.0
    den=math.sqrt((a+b)*(c+d)*(a+c)*(b+d))
    phi=((a*d-b*c)/den) if den else 0.0
    return float(odds),float(pf),float(chi2),float(pc),float(phi)
