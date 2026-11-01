"""Preserve an empty diagnostic match result without creating an empty corpus."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'compare_verified_v21_v25_and_actual_cache_v1.py').read_text(encoding='utf-8')
changes = [
    ('verified_v21_v25_actual_cache_comparison_v1', 'verified_v21_v25_actual_cache_comparison_v2'),
    ('    baseline_match_manifest=matches.close(lineage=pins),',
     '''    baseline_match_manifest=(matches.close(lineage=pins) if raw_matched_keys or candidate_matched_keys
        else dict(status="NO_PENDING_RAW_OR_DIAGNOSTIC_CANDIDATE_HASH_MATCHES_TO_BASELINE", rows=0, shards=[])),
    previous_incomplete_producer=dict(path=str((AUDIT / "compare_verified_v21_v25_and_actual_cache_v1.log").relative_to(ROOT)),
        sha256=inv.file_sha(AUDIT / "compare_verified_v21_v25_and_actual_cache_v1.log"),
        process_exit_code=1, cause="EMPTY_DIAGNOSTIC_MATCH_COLLECTION_WAS_INCORRECTLY_CLOSED_AS_A_NONEMPTY_CORPUS"),''')
]
for before, after in changes:
    assert source.count(before) == 1
    source = source.replace(before, after)
output = AUDIT / 'compare_verified_v21_v25_and_actual_cache_v2.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared comparison2; zero diagnostic matches have an explicit zero-result record.')
