"""Recognize recorded frame synonyms and explicit metadata-only corrections."""
from pathlib import Path
import argparse
import hashlib
import re
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
V1 = AUDIT / 'canonicalize_secondary_review_batches_v1.py'
V2 = AUDIT / 'canonicalize_secondary_review_batches_v2.py'
assert hashlib.sha256(V2.read_bytes()).hexdigest().upper() == \
    '682092EDAB1C18CD1DA64022F599F4B896A088B73DEEB4B9FEAA0D8036DB8C04'
import canonicalize_secondary_review_batches_v2 as previous


def parse_rows(text):
    # These labels record the actual returned frames in the original author
    # document. No view or completion claim is supplied by this adapter.
    text = re.sub(r'(?m)^- Reader frames(?: observed)?:', '- Views:', text)
    return previous.parse_rows(text)


raw = V1.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == \
    '69131555A3F77B6F1D113FAF73CAB3174CD88548CA74032CF6E58869FA38473F'
code = raw.decode('utf-8')
old = "                    current[ident] = row"
new = ("                    if mode == 'corrections' and ident in group.get('metadata_correction_ids', []):\n"
       "                        quarantined.discard(ident)\n" + old)
assert code.count(old) == 1
namespace = dict(__name__='versioned_metadata_canonicalizer_v3', __file__=__file__)
exec(compile(code.replace(old, new), str(V1), 'exec'), namespace)
namespace['parse_rows'] = parse_rows
old_freeze = namespace['freeze']


def freeze(path):
    text, record = old_freeze(path)
    record['canonicalizer_implementations'] = [namespace['pin'](p) for p in [V1, V2, Path(__file__)]]
    return text, record


namespace['freeze'] = freeze

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    namespace['run'](parser.parse_args().config.resolve())
