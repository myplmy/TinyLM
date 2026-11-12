"""Return an exact in-memory prefix when a multi-source packet exceeds its cap."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
FROZEN = AUDIT/'multi_source_lossless_review_entry_v1.py'
assert not FROZEN.is_symlink() and hashlib.sha256(FROZEN.read_bytes()).hexdigest().upper() == '4F30167E8DC5F00655CE32BA8AF4BFE96C15FBEFF5CBD38AFDF655DADE1E5433'
import multi_source_lossless_review_entry_v1 as previous
BASE_RENDER = previous.render


def __getattr__(name):
    return getattr(previous, name)


def render(packets, result):
    try:
        return BASE_RENDER(packets, result)
    except ValueError as exc:
        if not str(exc).startswith('bounded output exceeded;'):
            raise
    remaining = [dict(header=p['header'], pieces=list(p['pieces'])) for p in packets]
    prepared = [p['header']['source_id'] for p in packets]
    while remaining:
        returned = [p['header']['source_id'] for p in remaining]
        current = dict(result, returned_ids=returned,
            not_returned_ids=result['requested_ids'][len(returned):],
            source_pairs_returned=len(returned), prepared_source_ids=prepared,
            prepared_but_not_returned_ids=prepared[len(returned):],
            body_bytes=sum(len(piece['text'].encode('utf-8')) for p in remaining for piece in p['pieces']))
        try:
            return BASE_RENDER(remaining, current)
        except ValueError as exc:
            if not str(exc).startswith('bounded output exceeded;'):
                raise
        if len(remaining[-1]['pieces']) > 1:
            remaining[-1]['pieces'].pop()
        else:
            remaining.pop()
    raise ValueError('one whole frame cannot fit; nothing printed; use the single-ID reader')


def cli(root, role):
    with patch.object(previous, 'render', render):
        return previous.cli(root, role)
