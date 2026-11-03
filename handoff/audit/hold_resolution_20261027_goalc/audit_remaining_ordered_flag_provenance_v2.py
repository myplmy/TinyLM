"""Reuse the frozen audit and canonical parser; retain unresolved ownership proofs."""
from pathlib import Path
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN

resolve_entry_id, parse_entries, parser_sha = load_parser()
frozen = AUDIT / 'audit_remaining_ordered_flag_provenance_v1.py'
code = frozen.read_text(encoding='utf-8')
anchor = '''        matches = [line for line in review.splitlines() if line.startswith('|') and
                   line.split('|')[1].strip().strip('`') == ident]
        assert len(matches) == 1, 'exact full-ID review row is not uniquely bound' '''.rstrip()
assert code.count(anchor) == 1
code = code.replace(anchor, '''        entry = exact_entry(review.encode('utf-8'), ident, set(manifests[cohort]),
                            resolve_entry_id, parse_entries)
        matches = [entry['raw']]''')
anchor = '                assert role_from_review(source[\'review\']) == previous'
assert code.count(anchor) == 1
code = code.replace(anchor, '''                assert role_from_review(source['review']) == previous, 'prior review path does not identify the declared previous role' ''')
anchor = 'rows, successful = [], set()'
assert code.count(anchor) == 1
code = code.replace(anchor, anchor + chr(10) +
    "pins[str(FROZEN.relative_to(ROOT))] = parser_sha" + chr(10) +
    "pins[str(frozen.relative_to(ROOT))] = sha(frozen.read_bytes())" + chr(10) +
    "binding_helper = AUDIT / 'exact_manifest_review_row_binding_v1.py'" + chr(10) +
    "pins[str(binding_helper.relative_to(ROOT))] = sha(binding_helper.read_bytes())")
anchor = "target = AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V1.json'"
assert code.count(anchor) == 1
code = code.replace(anchor, "target = AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json'")
exec(compile(code, str(frozen), 'exec'), globals())
