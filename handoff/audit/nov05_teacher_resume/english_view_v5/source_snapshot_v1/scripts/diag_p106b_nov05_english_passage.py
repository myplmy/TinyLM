"""Typed article view over the English fork; preserve original source identity."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import diag_p106b_nov05_english_production as base
from scripts import diag_p106b_nov05_english_readback as reader
from scripts import diag_p106b_supported_production8h as supported

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'GEMMA_ENGLISH_TYPED_PASSAGE_V5'
VIEW = 'GEMMA_ENGLISH_ARTICLE_VIEW_V1'
V3 = supported.VERSION
TAG = 'p106b_english_passage_v5_20261105'
OUTPUT = ROOT / 'HF/sft_ready' / TAG
AUDIT = ROOT / 'handoff/audit/nov05_teacher_resume/english_view_v5'
BASE_SCOPE = base.scope
BASE_REPLAY = supported.replay
BASE_REQUIRE = base.ORIGINAL_REQUIRE
MARKERS = ('What are the answers to this following set of questions:',
           'Based on the article and the following list of answers, write a list of questions.')


def article(source):
    messages = source['messages']
    if len(messages) != 2 or [m['role'] for m in messages] != ['user', 'assistant']:
        raise ValueError('typed two-message source required')
    text = supported.message_text(messages[0])
    found = [(text.find(marker), marker) for marker in MARKERS if marker in text]
    if len(found) != 1 or text.count(found[0][1]) != 1:
        raise ValueError('one exact source management boundary required')
    end = found[0][0]
    if end == 0 or text[end - 1] != '\n':
        raise ValueError('source boundary must start on a new line')
    prefix = text[:end]
    passage = prefix.strip()
    if not passage:
        raise ValueError('nonempty complete article required')
    start_char = len(prefix) - len(prefix.lstrip())
    end_char = len(prefix.rstrip())
    trace = dict(schema=VIEW, source_user_sha256=hashlib.sha256(text.encode()).hexdigest().upper(),
        start_byte=len(text[:start_char].encode()), end_byte=len(text[:end_char].encode()),
        passage_sha256=hashlib.sha256(passage.encode()).hexdigest().upper(),
        boundary=found[0][1], original_source_messages_preserved_in_raw=True)
    return passage, trace


def require_typed_pilot(info, destination=OUTPUT):
    with patch.object(supported, 'VERSION', VIEW):
        return BASE_REQUIRE(info, destination=destination)


def replay_typed(control, tok, source_base, destination, info):
    def parent_only(*args, **kwargs):
        with patch.object(supported, 'VERSION', V3):
            return BASE_REPLAY(*args, **kwargs)
    with patch.object(supported, 'VERSION', VIEW), patch.object(supported, 'replay', parent_only):
        return base.replay_new(control, tok, source_base, destination, info)


@contextmanager
def scope(destination, stop_file=None, groups_limit=None):
    with BASE_SCOPE(destination, stop_file, groups_limit) as (producer, old_info):
        info = dict(old_info, visible_source_contract=VIEW, teacher_evidence_view=VIEW,
            teacher_view_code_sha256=base.sha(Path(__file__)),
            student_support='complete typed article passage; full original messages retained in raw',
            source_family_gate='Flan-Coqa with one exact known management boundary',
            no_semantic_output_filter=True)
        original_rows, original_payload = producer.english_rows, producer.tasks.payload
        original_group, quota_type = producer.produce_group, producer.control.Quotas
        current = {}

        def source_rows(spec):
            for source in original_rows(spec):
                key = producer.conversation_split_key(source).hex().upper()
                family = producer.control.capability.engine.family_bucket(source['meta']['source_family'])
                valid = family == 'Flan-Coqa'
                if valid:
                    try:
                        article(source)
                    except ValueError:
                        valid = False
                current.clear()
                current.update(key=key, valid=valid)
                yield source

        def visible(source, language):
            if language != 'en':
                raise ValueError('typed English view only')
            return 'user:\n' + article(source)[0]

        def payload(*args, **kwargs):
            result = original_payload(*args, **kwargs)
            source = args[0]
            passage, _ = article(source)
            body = json.loads(result['messages'][1]['content'])
            body['source']['public_context'] = [dict(role='user', content=passage)]
            result['messages'][1]['content'] = json.dumps(body, ensure_ascii=False)
            result['messages'][0]['content'] += (
                ' The only evidence for this request is the single supplied article passage. '
                'Use its explicit facts and the declared task; do not fill missing quantities. ')
            return result

        def group(session, source, language, *args, **kwargs):
            row = original_group(session, source, language, *args, **kwargs)
            if row is not None:
                _, trace = article(source)
                row['meta'].update(visible_source_contract=VIEW,
                    teacher_evidence_view=VIEW, source_view_trace=trace,
                    source_transform='teacher_qa_from_typed_english_article',
                    source_question_lists_not_in_teacher_or_student=True)
            return row

        class ViewQuota(quota_type):
            def profile(self, split, language, family, key):
                task = super().profile(split, language, family, key)
                return task if current.get('key') == key and current.get('valid') else None

            def report(self):
                return dict(super().report(), teacher_evidence_view=VIEW,
                            english_source_contract=VERSION)

        with ExitStack() as stack:
            for module, name, value in (
                (producer, 'require_pilots', lambda: info), (producer, 'english_rows', source_rows),
                (producer.tasks, 'payload', payload), (producer, 'produce_group', group),
                (producer.control, 'Quotas', ViewQuota),
                (producer, 'state_from_saved', lambda tok, original: replay_typed(
                    producer.control, tok, original, destination, info)),
                (supported, 'visible_source', visible)):
                stack.enter_context(patch.object(module, name, value))
            yield producer, info


@contextmanager
def variant():
    with ExitStack() as stack:
        for name, value in (('VERSION', VERSION), ('TAG', TAG), ('OUTPUT', OUTPUT),
                            ('AUDIT', AUDIT), ('scope', scope), ('ORIGINAL_REQUIRE', require_typed_pilot)):
            stack.enter_context(patch.object(base, name, value))
        yield


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'pilot', 'resume', 'read-pilot', 'read-window'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    parser.add_argument('--deadline-utc', default='2026-11-05T06:30:00+00:00')
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args()
    with variant():
        if args.mode == 'prepare':
            base.prepare()
            return 0
        if args.mode.startswith('read-'):
            with patch.object(sys, 'argv', [sys.argv[0], args.mode[5:]]):
                reader.main()
            return 0
        supported.limit_window(args.max_wall_sec, args.deadline_utc)
        if args.stop_file is None:
            raise ValueError('an exact fresh stop-file path is required')
        return base.execute(args)


if __name__ == '__main__':
    raise SystemExit(main())
