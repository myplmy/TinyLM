"""Reuse the pinned page collector with two opt-in explicit heading spellings."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_review_header_alias_v2 import wrap_review_entries


def install_header_aliases(environment):
    previous_load = environment['load_reused']

    def load(path, scope):
        scope = previous_load(path, scope)
        scope['review_entries'] = wrap_review_entries(scope['review_entries'])
        for name in ('collect_exact_page_reviews_v1.py', 'exact_review_header_alias_v1.py',
                     'exact_review_header_alias_v2.py', 'collect_exact_page_reviews_v2.py'):
            pin = AUDIT / name
            scope['input_pins'][str(pin.relative_to(ROOT))] = inv.file_sha(pin)
        return scope

    environment['load_reused'] = load


if __name__ == '__main__':
    frozen = AUDIT / 'collect_exact_page_reviews_v1.py'
    code = frozen.read_text(encoding='utf-8')
    marker = "environment['ALLOWED'] = {cohort: page['sources']}"
    assert code.count(marker) == 1
    code = code.replace(marker, 'install_header_aliases(environment)' + chr(10) + marker)
    exec(compile(code, str(frozen), 'exec'), globals())
