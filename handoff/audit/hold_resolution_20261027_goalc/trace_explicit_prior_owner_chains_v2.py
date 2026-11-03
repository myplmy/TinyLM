"""Reuse v1 and canonical saved table formats; retain missing historical pins."""
from pathlib import Path
import re

AUDIT = Path(__file__).resolve().parent
SOURCE = AUDIT / 'trace_explicit_prior_owner_chains_v1.py'


def normalized_entry(entry):
    cells = entry['cells']
    header = entry.get('header')
    assert len(cells) >= 5, 'saved review lacks explicit source/status/scope/output/reason fields'
    if header and len(cells) > len(header):
        cells = cells[:len(header)-1] + ['|'.join(cells[len(header)-1:])]
    columns = {label: cells[index] for index, label in enumerate(header or []) if index < len(cells)}
    labels = {'출력', '정확 출력', '산출물', '출력 TXT', '출력 (TXT basename)', '실제 새 출력'}
    outputs = [value for label, value in columns.items() if label in labels]
    assert len(outputs) <= 1, 'ambiguous explicit saved output columns'
    output = outputs[0] if outputs else entry['raw']
    status = {'EDIT_TEXT': 'REVISE_TEXT', 'ADOPT_CANDIDATE': 'ACCEPT_CANDIDATE'}.get(cells[1], cells[1])
    return dict(entry, cells=[cells[0], status, cells[2], output, cells[-1]],
                original_status=cells[1], output_scope='EXACT_OUTPUT_COLUMN' if outputs else
                'SAVED_FULL_ROW_WITH_UNIQUE_EXPLICIT_TXT')


def declared_txt_basename(cell, source_id, directory, paths, status):
    # An explicit MD sidecar is not a second TXT body. Two TXT tokens reject.
    matches = re.findall(r'/[^\s`|()<>;,]+[.]txt|(?<![A-Za-z0-9_./-])[A-Za-z0-9_.-]+[.]txt', cell)
    if len(matches) != 1:
        raise ValueError('MISSING_OR_MULTIPLE_EXPLICIT_TXT_BODY_TOKENS')
    return original_declared_txt_basename(matches[0], source_id, directory, paths, status)


code = SOURCE.read_text(encoding='utf-8')
replacements = [
    ('import declared_txt_basename', 'import declared_txt_basename as original_declared_txt_basename'),
    ("previous = read(AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json')",
     "previous = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V1.json')"),
    ('assert len(known) == 390', 'assert len(known) == 442'),
    ("scopes = {'root_join_conflict_counter_v1': 63,\n          'authored_postsignal_review_v1': 17, 'root10_quantity_recheck_v1': 1}",
     "scopes = {'root_join_conflict_counter_v1': 12, 'authored_postsignal_review_v1': 17}"),
    ("pending = [row for row in old['rows'] if row['id'] not in known and row['selected_cohort'] in scopes]",
     "pending = [row for row in old['rows'] if row['id'] not in known and row['selected_cohort'] in scopes]"),
    ('resolve, parse, parser_sha = load_parser()',
     'resolve, parse_original, parser_sha = load_parser()\nparse = lambda payload: parse_original(payload, allow_sections=True)'),
    ("entry = exact_entry(review, ident, set(source_rows), resolve, parse)",
     "entry = normalized_entry(exact_entry(review, ident, set(source_rows), resolve, parse))"),
    ("entry = exact_entry(review, ident, {row['id'] for row in integrity['records']}, resolve, parse)",
     "entry = normalized_entry(exact_entry(review, ident, {row['id'] for row in integrity['records']}, resolve, parse))"),
    ('assert len(rows) == 81', 'assert len(rows) == 29'),
    ('attempted_sources=81, prior_linked_record_scopes=390', 'attempted_sources=29, prior_linked_record_scopes=442'),
    ("target = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V1.json'", "target = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V2.json'"),
    ("pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())\nresult = dict(",
     "pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())\npins[str(SOURCE.relative_to(ROOT))] = sha(SOURCE.read_bytes())\nresult = dict("),
]
for before, after in replacements:
    assert code.count(before) == 1, 'frozen v1 shape changed'
    code = code.replace(before, after)
exec(compile(code, str(SOURCE), 'exec'), globals())
