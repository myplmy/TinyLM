"""One pinned legacy filename may retain its historical decision rows."""
from pathlib import Path
import hashlib


def install_rank_aliases(root, records, normal_rank, parse_ids):
    root = Path(root)
    aliases = {}

    def checked(record):
        old = root / record['path']
        new = root / record['canonical_review']
        assert record['root_approved'] is True
        assert old.resolve().is_relative_to(root.resolve()) and old.parent == new.parent
        assert not old.is_symlink() and not new.is_symlink()
        old_bytes, new_bytes = old.read_bytes(), new.read_bytes()
        assert hashlib.sha256(old_bytes).hexdigest().upper() == record['sha256']
        assert hashlib.sha256(new_bytes).hexdigest().upper() == record['canonical_review_sha256']
        expected = set(record['ids'])
        assert expected and parse_ids(old_bytes) == expected == parse_ids(new_bytes)
        rank = tuple(record['legacy_rank'])
        canonical = normal_rank(new)
        assert len(rank) == 3 and rank[:2] == canonical[:2] and rank[2] < canonical[2]
        try:
            normal_rank(old)
        except ValueError:
            pass
        else:
            raise ValueError('a valid filename must use its normal rank')
        return rank

    for record in records:
        assert record['path'] not in aliases
        checked(record)
        aliases[record['path']] = record

    def rank(path):
        relative = str(Path(path).relative_to(root))
        record = aliases.get(relative)
        return checked(record) if record else normal_rank(path)

    return rank
