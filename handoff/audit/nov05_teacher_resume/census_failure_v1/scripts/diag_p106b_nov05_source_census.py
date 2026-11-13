"""CPU-only remaining-source census; no teacher, quality filter or admission."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from scripts import diag_p106b_nov05_english_passage as view
from scripts import diag_p106b_nov05_english_resume as resume
from scripts import diag_p106b_nov05_english_production as base
from scripts import p106b_gemma_deficit as control
from scripts.p106b_public_refill import english_rows
from scripts.p106b_shards import ShardWriter, verify

OUTPUT = view.AUDIT / 'source_census_v1'
NATIVE_PROFILE = control.Quotas.profile
DEADLINE = datetime(2026, 11, 5, 6, 30, tzinfo=timezone.utc)


def after_cursor(source_index, ordinal, cursor):
    if (type(source_index) is not int or type(ordinal) is not int
            or len(cursor) != 2 or any(type(v) is not int for v in cursor)):
        raise ValueError('explicit original source index and iterator ordinal required')
    return (source_index, ordinal) > tuple(cursor)


def bounded(started, maximum, stop):
    if stop.exists():
        raise TimeoutError('explicit CPU census stop')
    if time.perf_counter()-started >= maximum or (DEADLINE-datetime.now(timezone.utc)).total_seconds() < 120:
        raise TimeoutError('CPU census budget reached; partial immutable index retained')


def retain_occurrence(writer, row, counts, prospective, articles):
    key = row['original_concept_id']
    duplicate = key in prospective
    row = dict(row, duplicate_exact_original_concept=duplicate)
    if duplicate:
        counts['duplicate_exact_original_concept'] += 1
    else:
        prospective.add(key)
        articles.add(row['source_view_trace']['passage_sha256'])
        counts['unique_original_concept_rows'] += 1
        counts['distinct_concept_article_tokens'] += row['article_tokens']
        counts['eligible_'+row['split']+'_concept_rows'] += 1
    writer.append(row)
    counts['retained_original_occurrences'] += 1
    counts['all_index_article_tokens'] += row['article_tokens']
    return not duplicate


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    parser.add_argument('--stop-file', type=Path, required=True)
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 7200 or args.stop_file.exists():
        raise ValueError('fresh stop path and60..7200-second CPU budget required')
    if OUTPUT.exists():
        raise FileExistsError('census namespace already exists; no silent replacement')
    started = time.perf_counter()
    counts, families, per_file = Counter(), Counter(), {}
    prospective, articles = set(), set()
    writer = None
    report = dict(schema='P106B_V5_SOURCE_CENSUS_V1', teacher_started=False,
        gpu=False, model_loading=False, candidate_admission=False, source_modified=False,
        full_source_exhaustion=False, semantic_quality='NOT_REVIEWED',
        source_code_sha256=base.sha(Path(__file__)), original_v5_source_sha256=base.sha(Path(view.__file__)))
    status, rc = 'STARTED', 9
    last = None
    quota_unchanged = None
    try:
        from tokenizers import Tokenizer
        with resume.runtime(), view.variant(), view.scope(view.OUTPUT) as (producer, info):
            original = producer.control.base_report()
            tok = Tokenizer.from_file(str(producer.TOKENIZER))
            state, cursor, closed = producer.state_from_saved(tok, original)
            before = state.report()
            if closed != 2:
                raise ValueError('exact V5 pilot plus first closed production window required')
            report.update(input_sha256=base.sha(view.OUTPUT/'inputs.json'),
                pilot_sha256=base.sha(view.OUTPUT/'batch_000000/report.json'),
                last_batch_sha256=base.sha(view.OUTPUT/'batch_000001/report.json'),
                original_cursor=list(cursor), original_closed_batches=closed,
                initial_quantities=before, english_source_sha256=info['english_sources'])
            writer = ShardWriter(OUTPUT, 'eligible_sources')
            for source_index, spec in enumerate(original['sources']):
                if spec['path'] not in info['english_sources']:
                    continue
                file_counts = Counter()
                per_file[str(source_index)] = file_counts
                for ordinal, source in enumerate(english_rows(spec)):
                    bounded(started, args.max_wall_sec, args.stop_file)
                    last = [source_index, ordinal]
                    counts['canonical_rows'] += 1
                    file_counts['canonical_rows'] += 1
                    family = producer.control.capability.engine.family_bucket(source['meta']['source_family'])
                    families[family] += 1
                    if not after_cursor(source_index, ordinal, cursor):
                        counts['consumed_cursor_rows'] += 1
                        continue
                    counts['remaining_rows'] += 1
                    if family != 'Flan-Coqa':
                        counts['unsupported_family'] += 1
                        continue
                    try:
                        article, trace = view.article(source)
                    except ValueError:
                        counts['unsupported_article_boundary'] += 1
                        continue
                    counts['typed_article_rows'] += 1
                    key = producer.conversation_split_key(source).hex().upper()
                    split = state.source_split(key)
                    # The same original quota function; typed eligibility is
                    # explicit here instead of depending on a live generator.
                    task = NATIVE_PROFILE(state, split, 'en', family, key)
                    if task is None:
                        counts['original_quota_or_seen_or_probe_excluded'] += 1
                        continue
                    mass = len(tok.encode('user:'+chr(10)+article).ids)
                    if mass > 768:
                        counts['reserved_article_budget_exceeded'] += 1
                        continue
                    counts['eligible_occurrences'] += 1
                    unique = retain_occurrence(writer, dict(source_index=source_index, original_ordinal=ordinal,
                        original_concept_id=key, split=split, suggested_task_at_frozen_quota=task,
                        article_tokens=mass, source_view_trace=trace, source=source),
                        counts, prospective, articles)
                    file_counts['eligible_original_concepts'] += int(unique)
                    if counts['canonical_rows'] % 1000000 == 0:
                        print('[CENSUS_PROGRESS] '+json.dumps(dict(cursor=last,counts=dict(counts))),flush=True)
                print('[CENSUS_FILE] '+json.dumps(dict(source_index=source_index,counts=dict(file_counts))),flush=True)
            quota_unchanged = state.report() == before
            if not quota_unchanged:
                raise RuntimeError('read-only quota census mutated original quantities')
            base.check_parent()
            report['parent_files_unchanged'] = True
            report['full_source_exhaustion'] = True
            status, rc = 'CENSUS_COMPLETE_NOT_GENERATION', 0
    except TimeoutError as exc:
        status, rc = 'CENSUS_PARTIAL_PRESERVED', 8
        report.update(error_type=type(exc).__name__, error=str(exc))
    except BaseException as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        status, rc = 'CENSUS_ERROR_PRESERVED', 9
    if writer is not None:
        manifest = writer.close(lineage=dict(schema=report['schema'],
            source='ORIGINAL_ENGLISH_ROWS_NO_REINDEXING_NO_MODEL',
            meaning='Eligibility upper bound only, not generated training quantity or semantic approval'))
        verify(OUTPUT, manifest)
        report['eligible_manifest'] = manifest
    report.update(status=status,returncode=rc,counts=dict(counts),
        family_canonical_rows=dict(families),per_file={k:dict(v) for k,v in per_file.items()},
        distinct_exact_article_bodies=len(articles),last_scanned_cursor=last,
        wall_seconds=time.perf_counter()-started,
        original_iterator_reused=True,quota_mutations=(None if quota_unchanged is None else not quota_unchanged),
        resumption='Index consumer not implemented. Never feed this sparse index through ordinary enumerate and claim original ordinals.')
    base.write(OUTPUT/'report.json',report)
    print('[CENSUS_FINAL] '+json.dumps({k:report[k] for k in
        ['status','returncode','full_source_exhaustion','counts','distinct_exact_article_bodies',
         'last_scanned_cursor','wall_seconds']}),flush=True)
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
