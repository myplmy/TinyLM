"""Add exact narrative review rows to the frozen table-only canonicalizer.

This parses author metadata only. It never fills an absent judgment or hash
from the corpus, and a malformed row remains quarantined by the v1 writer.
"""
from pathlib import Path
import argparse
import hashlib
import re
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
FROZEN = AUDIT / 'canonicalize_secondary_review_batches_v1.py'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest().upper() == \
    '69131555A3F77B6F1D113FAF73CAB3174CD88548CA74032CF6E58869FA38473F'
import canonicalize_secondary_review_batches_v1 as prior

TABLE_ROWS = prior.parse_rows
DECISION = r'(APPROVE_EXISTING_BODY|NEEDS_ROOT_CONTEXT|BODY_NEEDS_REPAIR)'
HEADING = re.compile(r'^#{2,4}\s+(.+)$', re.M)
SHA = re.compile(r'^- Body SHA(?:-256)?:\s*`?([A-Fa-f0-9]+)`?', re.M)
VIEWS = re.compile(r'^- Views:\s*(.+)$', re.M)


def section_id(heading):
    explicit = re.search(r'\b(?:expanded_train|validation):[0-9]+\b', heading)
    if explicit:
        return explicit.group()
    bare = re.match(r'`?([0-9]+)`?(?:\s|$)', heading)
    return 'expanded_train:' + bare.group(1) if bare else None


def parse_rows(text):
    rows, invalid = TABLE_ROWS(text)
    headings = list(HEADING.finditer(text))
    global_status = re.search(r'^- Status:\s*`?' + DECISION + r'`?', text, re.M)
    for i, match in enumerate(headings):
        ident = section_id(match.group(1))
        if not ident:
            continue
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[match.end():end]
        sha, views = SHA.search(section), VIEWS.search(section)
        decision = re.search(DECISION, match.group(1))
        # A document-wide correction applies only to sections that explicitly
        # identify the prior disposition they supersede.
        if decision is None and global_status and re.search(r'^- Supersedes:', section, re.M):
            decision = global_status
        if not sha or not views or decision is None:
            invalid.append(dict(id=ident, line=text[:match.start()].count(chr(10)) + 1,
                                reason='NARRATIVE_ROW_MISSING_EXPLICIT_HASH_VIEWS_OR_DECISION'))
            continue
        body_sha = sha.group(1).upper()
        if not re.fullmatch(r'[A-F0-9]{64}', body_sha):
            invalid.append(dict(id=ident, line=text[:match.start()].count(chr(10)) + 1,
                                reason='NARRATIVE_ROW_INVALID_HASH'))
            continue
        reason = ' / '.join(line.strip() for line in section.splitlines()
                            if line.strip() and not SHA.match(line) and not VIEWS.match(line))
        if not reason:
            invalid.append(dict(id=ident, line=text[:match.start()].count(chr(10)) + 1,
                                reason='NARRATIVE_ROW_MISSING_REASON'))
            continue
        rows.append(dict(id=ident, body_sha256=body_sha, decision=decision.group(1),
                         actual_views=views.group(1).strip(), reason=reason))
    # One explicit correction document has no case heading. It identifies the
    # body and reuses the earlier actual views after ROOT reconciled its delta.
    if not headings and re.search(r'^- Corrected judgment:', text, re.M):
        ident = re.search(r'ID\s+`((?:expanded_train|validation):[0-9]+)`', text)
        sha = SHA.search(text)
        decision = re.search(r'^- Corrected judgment:\s*`?' + DECISION, text, re.M)
        if ident and sha and decision and 'No source/body reread was performed' in text:
            body_sha = sha.group(1).upper()
            if re.fullmatch(r'[A-F0-9]{64}', body_sha):
                rows.append(dict(id=ident.group(1), body_sha256=body_sha,
                    decision=decision.group(1),
                    actual_views='Earlier actual views reused; no source/body reread after ROOT reconciliation',
                    reason=' / '.join(line.strip() for line in text.splitlines() if line.strip())))
            else:
                invalid.append(dict(id=ident.group(1), line=1, reason='NARRATIVE_ROW_INVALID_HASH'))
    return rows, invalid


prior.parse_rows = parse_rows
old_freeze = prior.freeze


def freeze(path):
    result = old_freeze(path)
    result[1]['canonicalizer_implementation'] = prior.pin(FROZEN)
    return result


prior.freeze = freeze
prior.__file__ = __file__

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    prior.run(parser.parse_args().config.resolve())
