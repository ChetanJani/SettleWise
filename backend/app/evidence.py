"""Evidence completeness, never a probability of personal safety."""
KEYS=('cctv','guard','access_control','lighting')
import re

def review_safety(reviews):
    """Transparent English text signals, never a crime-risk or personal-safety probability."""
    positive=re.compile(r'\b(?:safe|secure|well[- ]lit|good security|excellent security|security is good|helpful guards?)\b',re.I)
    negative=re.compile(r'\b(?:unsafe|insecure|not (?:very |at all )?(?:safe|secure)|no (?:security|guards?|cctv)|poor (?:security|lighting)|security (?:issues?|problems?)|theft|stolen|harass(?:ment|ed)|break[- ]in|dark (?:street|road|lane)|felt scared)\b',re.I)
    relevant=re.compile(r'\b(?:safe|safety|unsafe|secure|security|guards?|cctv|lighting|well[- ]lit|theft|stolen|harass\w*|break[- ]in|dark (?:street|road|lane)|felt scared)\b',re.I)
    signals=[];seen=set()
    for row in reviews:
        text=str(row.get('text') or '').strip();key=' '.join(text.lower().split())
        if not text or key in seen:continue
        seen.add(key)
        if not relevant.search(text):continue
        neg=bool(negative.search(text));clean=negative.sub('',text)
        pos=bool(positive.search(clean))
        # Negation is deliberately conservative: ambiguous language is not scored.
        if re.search(r'\b(?:never|hardly|not)\b.{0,24}\b(?:safe|secure|good security)\b',text,re.I):neg=True;pos=False
        sentiment='mixed' if pos and neg else 'negative' if neg else 'positive' if pos else 'unclear'
        signals.append({'sentiment':sentiment,'text':text[:450],'date':row.get('date'),'url':row.get('url'),
                        'women_mentioned':bool(re.search(r'\b(?:women|woman|girls?|female|ladies)\b',text,re.I))})
    counts={key:sum(s['sentiment']==key for s in signals) for key in ('positive','negative','mixed','unclear')}
    classified=counts['positive']+counts['negative']+counts['mixed']
    score=round(counts['positive']/classified*100) if classified>=3 else None
    reason=(f"{counts['positive']} positive, {counts['negative']} negative, {counts['mixed']} mixed safety reviews" if score is not None else f"Only {classified} clear safety reviews; at least 3 needed")
    return {'score':score,'label':'Review safety sentiment','reason':reason,'counts':counts,'sample_size':len(seen),
            'relevant_reviews':len(signals),'classified_reviews':classified,'signals':signals,
            'method':'Positive / (positive + negative + mixed) safety-related English review texts. Star ratings and unclear text are excluded.',
            'meaning':'Sampled reviewer sentiment, not a safety probability or verified security inspection. News is shown separately and does not change this percentage.'}
def evidence(property):
    facts=property.get('security_facts') or {}
    documented=[k for k in KEYS if isinstance(facts.get(k),bool)]
    return {'score':round(len(documented)/len(KEYS)*100) if documented else None,
            'documented':documented,'features':{k:facts[k] for k in documented},
            'label':'Safety evidence','meaning':'Percentage of four building-security checks with documented answers: CCTV, guard, controlled entry and lighting. Completeness only, not a safety guarantee. False answers also count as documented.',
            'source':property.get('security_source') or ('Fictional example' if property.get('is_demo') else 'Listing information')}
