"""Evidence completeness, never a probability of personal safety."""
KEYS=('cctv','guard','access_control','lighting')
def evidence(property):
    facts=property.get('security_facts') or {}
    documented=[k for k in KEYS if isinstance(facts.get(k),bool)]
    return {'score':round(len(documented)/len(KEYS)*100) if documented else None,
            'documented':documented,'features':{k:facts[k] for k in documented},
            'label':'Safety evidence','meaning':'Percentage of four building-security checks with documented answers: CCTV, guard, controlled entry and lighting. Completeness only, not a safety guarantee. False answers also count as documented.',
            'source':property.get('security_source') or ('Fictional example' if property.get('is_demo') else 'Listing information')}
