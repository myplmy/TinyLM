"""Reuse frozen profile rows only for identical source, body and review identities."""
from pathlib import Path
import hashlib


def signature(body_sha256, reviews):
    return body_sha256, tuple(sorted((item['path'], item['sha256']) for item in reviews))


def main():
    frozen = Path(__file__).with_name('profile_authored_remaining_deltas_v1.py')
    raw = frozen.read_bytes()
    expected = 'C56614DBEC484F1A2DFF6BAD451C626F6FD1F3FFF4F8AD3BA3C9167B3D617E27'
    assert hashlib.sha256(raw).hexdigest().upper() == expected
    code = raw.decode('utf-8')
    changes = [
        ("    output=guard.inv.BASE/config['metadata_directory_name']", """    old_profile = read(ROOT/config['prior_profile']['path'], config['prior_profile']['sha256'])
    assert old_profile['input_pins'][str(FROZEN_PROFILER.relative_to(ROOT))] == FROZEN_PROFILER_SHA
    old_directory = ROOT/old_profile['metadata_directory']
    guard.inv.verify(old_directory, old_profile['metadata_manifest'])
    old_signatures = {}
    for shard in old_profile['metadata_manifest']['shards']:
        pins[str((old_directory/shard['path']).relative_to(ROOT))] = shard['sha256']
    for old_row in guard.inv.cache.rows(old_directory, old_profile['metadata_manifest']):
        key = old_row['original']['sha256']
        assert key not in old_signatures
        old_signatures[key] = SIGNATURE(old_row['body']['sha256'], old_row['all_reviews'])
    metadata_rows_reused = 0
    output=guard.inv.BASE/config['metadata_directory_name']"""),
        ("        body=dict(path=row['body'],sha256=row['clean_text_sha256'])", """        if old_signatures.get(digest) == SIGNATURE(row['clean_text_sha256'], [item['review'] for item in items]):
            metadata_rows_reused += 1
            continue
        body=dict(path=row['body'],sha256=row['clean_text_sha256'])"""),
        ("[config_path,Path(__file__),guard.CONTRACT,AUDIT/'AUTHORED_DELTA_PROFILE_SCOPE_V1.md']",
         "[config_path,Path(__file__),FROZEN_PROFILER,guard.CONTRACT,AUDIT/'AUTHORED_DELTA_PROFILE_SCOPE_V1.md',AUDIT/'INCREMENTAL_AUTHORED_PROFILE_F3_F4_V1.md']"),
        ("report=dict(status='EXISTING_AUTHORED_DELTAS_PROFILED_NOT_ADMISSION',counts=dict(counts),",
         "report=dict(status='ONLY_NEW_OR_CHANGED_AUTHORED_DELTAS_PROFILED_NOT_ADMISSION',prior_unchanged_profile_rows_reused_without_payload_opens=metadata_rows_reused,prior_profile=config['prior_profile'],counts=dict(counts),"),
    ]
    for before, after in changes:
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    exec(compile(code, str(frozen), 'exec'), dict(__name__='__main__', __file__=str(Path(__file__)),
        FROZEN_PROFILER=frozen, FROZEN_PROFILER_SHA=expected, SIGNATURE=signature))


if __name__ == '__main__':
    main()
