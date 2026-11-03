"""Freeze the verified journal prefix so later appends cannot invalidate evidence."""
from pathlib import Path


def archive_event_prefixes(root, target, live_pins, guard):
    directory = target / 'event_archive'
    directory.mkdir()
    archives = []
    for original in live_pins:
        guard.require(isinstance(original['bytes'], int) and
                      0 < original['bytes'] <= guard.MAX_SHARD_BYTES, 'invalid event prefix size')
        path = guard.secure_path(root, original['path'])
        with path.open('rb') as stream:
            prefix = stream.read(original['bytes'])
        guard.require(len(prefix) == original['bytes'] and
                      guard.sha(prefix) == original['sha256'], 'journal prefix changed after verification')
        archive = directory / (original['sha256'] + '.jsonl')
        if archive.exists():
            guard.require(not archive.is_symlink() and archive.read_bytes() == prefix,
                          'existing archive differs')
        else:
            with archive.open('xb') as stream:
                stream.write(prefix)
        archives.append(dict(path=str(archive.relative_to(root)), sha256=original['sha256'],
                              bytes=len(prefix), source_journal_prefix=dict(original)))
    return archives
