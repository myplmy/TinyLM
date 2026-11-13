"""Fresh English-only source fork; reuse the published producer and V3 replay."""
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import diag_p106b_supported_production8h as supported
from scripts.diag_p106b_nov05_supported_ready import sha, snapshot
from scripts.p106b_shards import verify
from scripts.p108_readback import write_small

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'GEMMA_ENGLISH_VISIBLE_SOURCE_V4'
TAG = 'p106b_english_visible_v4_20261105'
PARENT = supported.OUTPUT
OUTPUT = ROOT / 'HF/sft_ready' / TAG
AUDIT = ROOT / 'handoff/audit/nov05_teacher_resume/english_v4'
READY = ROOT / 'handoff/audit/nov05_teacher_resume/PREFLIGHT_v1.json'
ORIGINAL_SCOPE = supported.scope
ORIGINAL_REQUIRE = supported.require_pilot
EXAMPLE = ('Example:\nQUESTION:\n<learner question>\nANSWER:\n<answer content>'
           '\nNOTE:\n<optional note>')
SESSION_REFERENCES = []


def write(path, value):
    write_small(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + chr(10))


def without_example(payload):
    content = payload['messages'][0]['content']
    if content.count(EXAMPLE) != 1:
        raise ValueError('exact producer example suffix changed')
    replacement = (
        'Write the actual source-supported question and answer under the three headers. '
        'Do not copy illustrative placeholders. ')
    payload['messages'][0]['content'] = content.replace(EXAMPLE, replacement, 1)
    return payload


def english_rows(spec, inner, allowed):
    if spec['path'] not in allowed:
        return
    for source in inner(spec):
        if source['meta']['language'] != 'en':
            raise ValueError('English source identity differs')
        yield source


def check_parent():
    ready = json.loads(READY.read_text(encoding='utf-8'))
    if (ready['status'] != 'TECHNICAL_INPUTS_READY_NOT_SEMANTIC_APPROVAL'
            or snapshot(PARENT) != ready['original_files']):
        raise ValueError('published V3 parent changed')
    if len(list(PARENT.glob('batch_*'))) != ready['original_batches']:
        raise ValueError('published V3 parent batch count changed')
    return ready


def replay_new(control, tok, base, destination, info):
    state, _, parent_count = supported.replay(
        control, tok, base, PARENT, info['ancestor_cursor'])
    if parent_count != info['prior_visible_batch_count']:
        raise ValueError('prior V3 batch count differs')
    cursor, count = (-1, -1), 0
    for directory, report in supported.batches(control, destination):
        if report.get('input') != info:
            raise ValueError('new fork input contract differs')
        if 'raw_manifest' in report:
            verify(directory, report['raw_manifest'])
        if 'candidate_manifest' in report:
            for row in control.rows(directory, report['candidate_manifest']):
                meta = row['meta']
                if (meta.get('english_source_contract') != VERSION
                        or meta.get('language') != 'en'
                        or meta.get('original_source_language') != 'en'
                        or meta.get('source_sha256') not in set(info['english_sources'].values())):
                    raise ValueError('new candidate source/target contract differs')
                if state.admit(row) is None:
                    raise ValueError('new candidate cannot replay')
        current = state.report()
        for field in ('nonpadding_tokens', 'assistant_targets'):
            if current[field] != report[field]:
                raise ValueError('new fork replay counters differ: ' + field)
        cursor, count = tuple(report['cursor']), count + 1
    return state, cursor, count


@contextmanager
def scope(destination, stop_file=None, groups_limit=None):
    ready = check_parent()
    with ORIGINAL_SCOPE(destination, stop_file, groups_limit) as (producer, old_info):
        base = producer.control.base_report()
        allowed = {s['path']: s['sha256'] for s in base['sources']
                   if s['family'] == 'aya_collection_en'}
        if len(allowed) != 7:
            raise ValueError('exact seven pinned English source files required')
        for name, digest in allowed.items():
            if ready['public_source_sha256'].get(name) != digest:
                raise ValueError('new English source outside existing approved inputs')
        old_rows = sum(r.get('accepted_groups', 0)
                       for _, r in supported.batches(producer.control, PARENT))
        info = dict(old_info, english_source_contract=VERSION,
            prior_visible_input_sha256=sha(PARENT / 'inputs.json'),
            prior_visible_last_report_sha256=sha(PARENT / 'batch_000006/report.json'),
            prior_visible_batch_count=7, prior_visible_candidate_rows=old_rows,
            english_sources=allowed, output_languages=['en'],
            source_filter='exact original source indices and original iterator ordinals; no reindexing',
            new_cursor_initial=[-1, -1], runtime_addendum_sha256=sha(Path(__file__)),
            removed_management_example=True, completeness_cue_adopted=False)
        original_rows, original_payload = producer.english_rows, producer.tasks.payload
        original_group, quota_type = producer.produce_group, producer.control.Quotas
        original_session = producer.teacher.GemmaSession

        def session_factory(flag):
            session = original_session(flag)
            SESSION_REFERENCES.append(session)
            return session

        def payload(*args, **kwargs):
            return without_example(original_payload(*args, **kwargs))

        def group(session, source, language, *args, **kwargs):
            if language != 'en' or source['meta']['language'] != 'en':
                raise ValueError('English-only fork cannot produce another target language')
            row = original_group(session, source, language, *args, **kwargs)
            if row is not None:
                row['meta'].update(english_source_contract=VERSION,
                    original_source_language='en', source_transform='teacher_qa_from_english_visible_source')
            return row

        class EnglishQuota(quota_type):
            def report(self):
                return dict(super().report(), english_source_contract=VERSION,
                    prior_visible_candidate_rows_admitted=old_rows,
                    output_languages=['en'], korean_new_tokens=0,
                    teacher_production_fork=VERSION)

        with ExitStack() as stack:
            for module, name, value in (
                (producer, 'require_pilots', lambda: info),
                (producer, 'english_rows', lambda spec: english_rows(spec, original_rows, allowed)),
                (producer.tasks, 'payload', payload), (producer, 'produce_group', group),
                (producer.teacher, 'GemmaSession', session_factory),
                (producer.control, 'Quotas', EnglishQuota),
                (producer, 'state_from_saved', lambda tok, base: replay_new(
                    producer.control, tok, base, destination, info)),
                (producer.control, 'TAG', TAG)):
                stack.enter_context(patch.object(module, name, value))
            yield producer, info


def require_pilot(info):
    report = ORIGINAL_REQUIRE(info, destination=OUTPUT)
    approval = json.loads((AUDIT / 'ROOT_PILOT_REVIEW_v1.json').read_text(encoding='utf-8'))
    if (approval.get('decision') != 'ALLOW_BOUNDED_ENGLISH_CANDIDATE_GENERATION'
            or approval.get('pilot_report_sha256') != sha(OUTPUT / 'batch_000000/report.json')):
        raise ValueError('root reading of the exact four pilot sources/answers required')
    return report


def prepare():
    from tokenizers import Tokenizer
    from scripts.p106b_mixed_scale import TOKENIZER, TOK_SHA
    from tinylm.data.sft import conversation_split_key
    with scope(OUTPUT) as (producer, info):
        base = producer.control.base_report()
        if sha(TOKENIZER) != TOK_SHA:
            raise ValueError('student tokenizer changed')
        for name, expected in info['english_sources'].items():
            if sha(ROOT / name) != expected:
                raise ValueError('pinned English source changed')
        tok = Tokenizer.from_file(str(TOKENIZER))
        state, cursor, count = producer.state_from_saved(tok, base)
        if count or cursor != (-1, -1):
            raise ValueError('fresh fork preparation only; no silent reset')
        examples = []
        for source_index, spec in enumerate(base['sources']):
            for ordinal, source in enumerate(producer.english_rows(spec)):
                key = conversation_split_key(source).hex().upper()
                family = producer.control.capability.engine.family_bucket(source['meta']['source_family'])
                split = state.source_split(key)
                task = state.profile(split, 'en', family, key)
                if task is not None and len(tok.encode(supported.visible_source(source, 'en')).ids) <= 768:
                    request = producer.tasks.payload(source, 'en', task, 1337)
                    if EXAMPLE in request['messages'][0]['content']:
                        raise ValueError('producer example not removed')
                    examples.append(dict(source_index=source_index, ordinal=ordinal,
                        family=family, task=task, source=source))
                if len(examples) >= 8:
                    break
            if len(examples) >= 8:
                break
        if len(examples) != 8:
            raise ValueError('eight eligible English source examples not found')
        value = dict(schema='P106B_ENGLISH_FORK_READY_V1', status='TECHNICAL_READY',
            input=info, source_code_sha256=sha(Path(__file__)), cursor=list(cursor),
            quotas=state.report(), examples=examples, model_loading=False,
            original_files_unchanged=check_parent()['original_files'] == ready_files())
        write(AUDIT / 'PREPARE_v1.json', value)
        print('[ENGLISH_READY] ' + json.dumps(dict(examples=len(examples),
            source_code_sha256=value['source_code_sha256'], new_tokens=0, model_loading=False)), flush=True)


def ready_files():
    return json.loads(READY.read_text(encoding='utf-8'))['original_files']


def execute(args):
    prepared = json.loads((AUDIT / 'PREPARE_v1.json').read_text(encoding='utf-8'))
    if sha(Path(__file__)) != prepared['source_code_sha256']:
        raise ValueError('prepared fork source changed')
    before = check_parent()['original_files']
    supported.limit_window(args.max_wall_sec, args.deadline_utc)
    with scope(OUTPUT) as (producer, info):
        if info != prepared['input']:
            raise ValueError('prepared fork inputs changed')
    # Original execute owns bounded SIGTERM, fresh memory, teacher and batch closure.
    with ExitStack() as stack:
        for name, value in (('scope', scope), ('OUTPUT', OUTPUT), ('PILOT', OUTPUT),
                            ('require_pilot', require_pilot)):
            stack.enter_context(patch.object(supported, name, value))
        rc = supported.execute(args)
    after = check_parent()['original_files']
    closed = all(obj.session is None or obj.session.process is None
                 or obj.session.process.poll() is not None for obj in SESSION_REFERENCES)
    if not closed:
        raise RuntimeError('owned teacher server is still live after the production context')
    directory = AUDIT / 'windows'
    number = len(list(directory.glob('window_*.json'))) if directory.exists() else 0
    write(directory / ('window_' + str(number).zfill(6) + '.json'),
          dict(returncode=rc, mode=args.mode, parent_files_unchanged=before == after,
               new_batch_reports=len(list(OUTPUT.glob('batch_*/report.json'))),
               max_wall_sec=args.max_wall_sec, deadline_utc=args.deadline_utc,
               stop_file=str(args.stop_file) if args.stop_file else None,
               owned_teacher_processes=len(SESSION_REFERENCES), owned_teacher_closed=closed,
               semantic_quality='NOT_REVIEWED', student_training=False))
    return rc


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'pilot', 'resume'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    parser.add_argument('--deadline-utc', default='2026-11-05T06:30:00+00:00')
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare()
        return 0
    return execute(args)


if __name__ == '__main__':
    raise SystemExit(main())
