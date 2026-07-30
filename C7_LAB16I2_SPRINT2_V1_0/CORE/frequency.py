def association(a,b,c,d):
    n=a+b+c+d; support=(a+b)/n if n else 0; base=(a+c)/n if n else 0
    confidence=a/(a+b) if a+b else 0; lift=confidence/base if base else None
    leverage=(a/n-support*base) if n else 0
    conviction=((1-base)/(1-confidence)) if confidence<1 else float('inf')
    return support,base,confidence,lift,leverage,conviction
