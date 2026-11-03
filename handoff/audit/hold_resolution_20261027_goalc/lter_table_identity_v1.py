"""Prove every named coordinate row survives an intentionally held R script."""
import re

START = 'sites=read.delim(textConnection("'
END = '"),header=F,strip.white=T)'
FIELDS = 'names(sites)=c("sites","lat","long")'
ROW = re.compile(r'\s*([^0-9]+?\([A-Z]{3}\))\s+(-?[0-9]+\.[0-9]+)\s+(-?[0-9]+\.[0-9]+)')


def prove_table(original, cleaned):
    if original.count(START) != 1 or original.count(END) != 1 or original.count(FIELDS) != 1:
        raise ValueError('exact source data and typed fields required')
    begin = original.index(START) + len(START)
    end = original.index(END, begin)
    data = original[begin:end]
    dummy = re.match(r'\s*0\s+0\s+', data)
    if not dummy:
        raise ValueError('unexpected unnamed initial source fragment')
    position = dummy.end()
    expected, spans = [], []
    while data[position:].strip():
        match = ROW.match(data, position)
        if not match:
            raise ValueError('source coordinate row boundary is ambiguous')
        expected.append(tuple(x.strip() for x in match.groups()))
        spans.append([begin + match.start(), begin + match.end()])
        position = match.end()
    prefix = ''.join(original.splitlines(keepends=True)[:2])
    if not cleaned.startswith(prefix):
        raise ValueError('independent source introduction changed')
    lines = [line.strip() for line in cleaned[len(prefix):].splitlines() if line.strip()]
    if lines[:2] != ['LTER sites', '| sites | lat | long |']:
        raise ValueError('unexpected body heading or field names')
    if len(lines) < 3 or not re.fullmatch(r'[|:\- ]+', lines[2]):
        raise ValueError('table separator differs')
    actual = []
    for line in lines[3:]:
        if not line.startswith('|') or not line.endswith('|'):
            raise ValueError('unreviewed prose or code outside table')
        cells = tuple(cell.strip() for cell in line.split('|')[1:-1])
        if len(cells) != 3:
            raise ValueError('table row field count differs')
        actual.append(cells)
    if actual != expected:
        raise ValueError('site names, numeric spelling, signs, fields, order or multiplicity changed')
    return dict(rows=[dict(sites=row[0], lat=row[1], long=row[2], original_character_span=span)
        for row, span in zip(expected, spans)], rows_checked=len(expected),
        unchanged_independent_intro=True, exact_all_names_and_coordinate_strings=True,
        original_field_names=['sites', 'lat', 'long'], script_reconstructed=False,
        r_executed=False, geographic_fact_validation=False)
