"""Flag lost stated ages/relative periods and suspicious birth-field removal."""
from collections import Counter
import re

QUANTITIES={
    'STATED_AGE_REMOVED':re.compile(r'(?<![0-9])[0-9]+(?:[,·~∼–-][0-9]+)*[ \t]*(?:여[ \t]*)?세(?![기대])'),
    'STATED_RELATIVE_PERIOD_REMOVED':re.compile(r'(?<![0-9])[0-9]+[ \t]*(?:년|개월|일)[ \t]*(?:뒤|후|전)'),
}
CATEGORY=re.compile(r'^[ \t]*([0-9]{3,4})년[ \t]*(출생|사망)[ \t]*$',re.M)


def normalize(value):
    return re.sub(r'[ \t]+','',value)


def lost_stated_quantities(original,body):
    flags=[]
    for kind,pattern in QUANTITIES.items():
        retained=Counter(normalize(m.group()) for m in pattern.finditer(body))
        for match in pattern.finditer(original):
            value=normalize(match.group())
            if retained[value]:
                retained[value]-=1
                continue
            flags.append(dict(kind=kind,value=value,original_span=list(match.span()),
                original_line=original.count(chr(10),0,match.start())+1,
                original_context=original[max(0,match.start()-100):match.end()+100]))
    return flags


def suspicious_birth_field_removal(original,body):
    births={m[1] for m in CATEGORY.finditer(original) if m[2]=='출생'}
    first=original.split(chr(10)+chr(10),1)[0]
    lead=re.search(r'[（(][^\n]{0,160}?([0-9]{3,4})년',first)
    if len(births)!=1 or lead is None or lead[1] not in births:
        return []
    year=lead[1]
    if re.search(re.escape(year)+r'년',body.split(chr(10)+chr(10),1)[0]):
        return []
    return [dict(kind='MATCHING_LEAD_AND_SOLE_BIRTH_CATEGORY_YEAR_REMOVED_REQUIRES_CONTEXT',
        year=year,original_birth_categories=sorted(births),
        original_death_categories=sorted({m[1] for m in CATEGORY.finditer(original) if m[2]=='사망'}),
        original_lead=first[:700],body_lead=body.split(chr(10)+chr(10),1)[0][:700])]
