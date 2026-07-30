import math

def h2(p):
    if p<=0 or p>=1:return 0.0
    return -p*math.log2(p)-(1-p)*math.log2(1-p)

def information(a,b,c,d):
    n=a+b+c+d
    if not n:return 0,0,0
    py=(a+c)/n; hx=h2((a+b)/n); hy=h2(py)
    cond=((a+b)/n)*h2(a/(a+b) if a+b else 0)+((c+d)/n)*h2(c/(c+d) if c+d else 0)
    ig=hy-cond
    return hy,ig,ig
