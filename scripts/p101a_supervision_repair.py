#!/usr/bin/env python3
"""Prepare a write-once V4 supervision candidate; never train or load a model.

Only two pinned PUBLIC conversations gain meta.supervised_assistant_turns=[2].
All messages, input tokens, row order and splits stay identical to frozen V3.
Preparation is NOT training admission or an exhaustive semantic quality review.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.diag_p101a_clean_bilingual import digest, masked_record
from scripts.p106b_shards import ShardWriter, verify
from scripts import p106b_source_cleanup as cleanup

SCHEMA = 'P101A_SUPERVISION_REPAIR_PREPARATION_V4'
TAG = 'p101a_sft_mtp_supervision_v4_s1337'
SOURCE_TAG = 'p101a_sft_mtp_cleanbilingual_v3_s1337'
SOURCE = 'HF/sft_ready/' + SOURCE_TAG + '/corpus'
PUBLIC = 'HF/sft_ready/p090_public_v3_train.canonical.jsonl'
TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
DEFAULT_OUTPUT = 'HF/sft_ready/' + TAG + '/corpus'
CANDIDATE_OUTPUT = 'data_cache/' + TAG + '/corpus'
OUTPUTS = (DEFAULT_OUTPUT, CANDIDATE_OUTPUT)
SOURCE_REPORT_SHA = '7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20'
PUBLIC_SHA = '96A3507344FEFCA5072887AB4664DBB9BEDBD37BCD0D01A564220C1008D4F836'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
SOURCE_COUNTS = dict(train=dict(rows=22528, x_tokens=5405444, assistant_targets=552609),
                     val=dict(rows=512, x_tokens=127921, assistant_targets=2977))
UPDATES = 704
SOURCE_CONTROLLER = 'scripts/diag_p101a_clean_bilingual.py'
CODE = ('scripts/p101a_supervision_repair.py', 'scripts/test_p101a_supervision_repair.py',
        SOURCE_CONTROLLER, 'scripts/p106b_shards.py', 'scripts/p106b_source_cleanup.py',
        'tinylm/train/mtp_sft.py', 'tinylm/data/sft.py', 'tinylm/chat/serialize.py', 'tinylm/chat/canonical.py')
REPAIRS = (
    dict(source_index=192, source_id='012069b9-79e2-45ad-8b56-dcf1d1caa854',
         canonical_line_sha256='116F1545E0C92EBCB3ED5AB31868A8E8DCE119326AA108E10474DE5B43AB6C24',
         expected_first_targets=91, expected_second_targets=52,
         reason='CONFIRMED_DEFINITION_FORMULA_CONTRADICTION',
         review='첫 답의 분산 정의가 제곱 없는 편차 합이라고 쓰여 같은 답의 식과 모순된다. 첫 답 전체만 감독에서 제외한다.'),
    dict(source_index=198, source_id='019ad050-0b9e-4494-b27c-9e1d5169411c',
         canonical_line_sha256='D7D6E600CD9EABF3F799CFDA117C5DA16F383BD41D5257BD567A677D0258FBA7',
         expected_first_targets=365, expected_second_targets=404,
         reason='CONFIRMED_FOLLOWUP_INTENT_MISUNDERSTANDING',
         review='후속 사용자가 OpenAI 회사가 아니라 open-source 모델을 뜻했다고 명시한다. 첫 답 전체가 사실 오류라는 판정은 아니다.'),
)
REMOVAL_SCOPE = ('Entire first assistant responses in two reviewed error/intent-misunderstanding cases; '
                 'removed target count is NOT a count of factually incorrect tokens.')


def path(relative):
    item = Path(relative)
    if item.is_absolute() or not item.parts or '..' in item.parts or '\\' in str(relative):
        raise ValueError('explicit non-protected repository-relative path required')
    return cleanup.safe(ROOT / item)


def hashes(names):
    return {name: digest(path(name)) for name in names}


def read_json(relative):
    raw = path(relative).read_bytes()
    if len(raw) >= 20_000_000:
        raise ValueError('small JSON metadata required')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('JSON metadata object required')
    return value


def write_json(relative, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= 20_000_000:
        raise ValueError('small output metadata required')
    with path(relative).open('xb') as stream:
        stream.write(raw)


def stream(directory, manifest):
    index = 0
    for shard in manifest['shards']:
        with path(directory + '/' + shard['path']).open('rb') as source:
            for line_number, raw in enumerate(source, 1):
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise ValueError('canonical row object required')
                yield index, row, raw, shard['path'], line_number
                index += 1


def load_inputs():
    if digest(path(SOURCE + '/report.json')) != SOURCE_REPORT_SHA:
        raise ValueError('exact frozen V3 report required')
    report = read_json(SOURCE + '/report.json')
    if (report.get('schema') != 'P101A_SFT_MTP_CORPUS_V1'
            or report.get('preparation_schema') != 'P101A_CLEAN_BILINGUAL_PREPARATION_V3'
            or report.get('status') != 'CORPUS_READY' or report.get('family') != 'mtp'
            or report.get('tag') != SOURCE_TAG or report.get('epochs') != 4
            or report.get('learning_updates') != UPDATES or report.get('counts') != SOURCE_COUNTS
            or set(report.get('manifests', {})) != {'train', 'val'}
            or report.get('tokenizer_sha256') != TOKENIZER_SHA
            or report.get('actual_unique_train_x_tokens') != SOURCE_COUNTS['train']['x_tokens']
            or report.get('target_processed_x_tokens') != 4 * SOURCE_COUNTS['train']['x_tokens']
            or report.get('sources', {}).get('public_train_sha256') != PUBLIC_SHA
            or report.get('code_sha256', {}).get(SOURCE_CONTROLLER) != digest(path(SOURCE_CONTROLLER))):
        raise ValueError('frozen V3 producer/counts/epochs/tokenizer contract differs')
    names = [SOURCE + '/report.json', PUBLIC, TOKENIZER]
    for split, manifest in report['manifests'].items():
        name = SOURCE + '/' + split + '_shards_manifest.json'
        if read_json(name) != manifest or manifest['rows'] != SOURCE_COUNTS[split]['rows']:
            raise ValueError('original split manifest differs')
        verify(path(SOURCE), manifest)
        names.append(name)
        names.extend(SOURCE + '/' + shard['path'] for shard in manifest['shards'])
    snapshot = hashes(names)
    if snapshot[PUBLIC] != PUBLIC_SHA or snapshot[TOKENIZER] != TOKENIZER_SHA:
        raise ValueError('pinned original canonical/tokenizer required')
    canonical = {}
    wanted = {spec['source_index']: spec for spec in REPAIRS}
    with path(PUBLIC).open('rb') as source:
        for index, raw in enumerate(source):
            if index not in wanted:
                continue
            spec = wanted[index]; row = json.loads(raw)
            if (hashlib.sha256(raw).hexdigest().upper() != spec['canonical_line_sha256']
                    or row.get('meta', {}).get('source_id') != spec['source_id']
                    or row['meta'].get('source') != 'oasst'
                    or 'supervised_assistant_turns' in row['meta']
                    or [m['role'] for m in row['messages']] != ['user', 'assistant', 'user', 'assistant']):
                raise ValueError('reviewed canonical line/source/turn structure differs')
            canonical[spec['source_id']] = row
    if len(canonical) != len(REPAIRS):
        raise ValueError('both pinned reviewed sources required')
    return report, snapshot, canonical


def repaired_row(row, split, canonical):
    ident = row.get('meta', {}).get('source_id')
    if ident not in canonical:
        return row, None
    if split != 'train' or row != canonical[ident] or row['messages'] != canonical[ident]['messages']:
        raise ValueError('repair must match the exact original TRAIN canonical messages/metadata')
    result = copy.deepcopy(row)
    result['meta']['supervised_assistant_turns'] = [2]
    return result, next(spec for spec in REPAIRS if spec['source_id'] == ident)


def source_family(row):
    meta = row.get('meta', {})
    if (meta.get('source'), meta.get('kind')) == ('explicit_public_context_qa', 'night_natural_qa'):
        return 'natural_context_qa'
    if meta.get('kind') == 'role_bridge' and meta.get('source') == 'project_authored_role_bridge':
        return 'role_replay'
    if meta.get('source') in ('oasst', 'aya'):
        return 'public_general:' + meta['source']
    known = {
        ('project_authored_query_specific_evidence', 'evidence_recovery'): 'evidence_recovery',
        ('code_graph_factory', 'fictional_relation_fields'): 'fictional_relation_fields',
        ('p106b_context_code_fixture', 'arithmetic'): 'code_replay:arithmetic',
        ('p106b_context_code_fixture', 'boolean'): 'code_replay:boolean',
        ('p106b_context_code_fixture', 'json'): 'code_replay:json',
        ('p106b_context_code_fixture', 'update'): 'code_replay:update',
        ('PROJECT_AUTHORED_CODE', 'binding_color'): 'code_replay:binding_color',
        ('PROJECT_AUTHORED_CODE', 'binding_department'): 'code_replay:binding_department',
    }
    key = (meta.get('source'), meta.get('kind'))
    if key in known:
        return known[key]
    raise ValueError('unknown source family cannot be silently counted as reviewed PUBLIC')


def new_mass():
    return dict(total=Counter(), by_language=defaultdict(Counter),
                by_source_family=defaultdict(Counter), by_language_and_source_family=defaultdict(Counter))


def add_mass(mass, row, record):
    values = dict(rows=1, x_tokens=record.x_tokens, assistant_targets=record.targets)
    language = row.get('meta', {}).get('language', 'UNKNOWN')
    family = source_family(row)
    mass['total'].update(values)
    mass['by_language'][language].update(values)
    mass['by_source_family'][family].update(values)
    mass['by_language_and_source_family'][language + '/' + family].update(values)


def plain_mass(mass):
    return dict(total=dict(mass['total']), **{name: {key: dict(value) for key, value in sorted(mass[name].items())}
        for name in ('by_language', 'by_source_family', 'by_language_and_source_family')})


def turn_audit(record):
    from tinylm.train.mtp_sft import Record, count_record
    if len(record.x) != len(record.y) or len(record.y) != len(record.segments):
        raise ValueError('aligned encoded record required')
    if any((y == -100) != (owner == 0) for y, owner in zip(record.y, record.segments)):
        raise ValueError('masked targets must have owner zero')
    result = {}
    for owner in sorted({s for s in record.segments if s > 0}):
        chosen = Record(record.x, [y if s == owner else -100 for y, s in zip(record.y, record.segments)],
                        [s if s == owner else 0 for s in record.segments])
        result[str(owner)] = {str(h): n for h, n in count_record(chosen).items()}
    return result


def audit_repair(before, after, spec):
    a, b = turn_audit(before), turn_audit(after)
    if (before.x != after.x or set(a) != {'1', '2'} or set(b) != {'2'}
            or a['1']['1'] != spec['expected_first_targets']
            or a['2']['1'] != spec['expected_second_targets'] or b['2'] != a['2']
            or before.targets - after.targets != spec['expected_first_targets']):
        raise ValueError('exact first-turn-only supervision removal/token counts required')
    for y0, owner0, y1, owner1 in zip(before.y, before.segments, after.y, after.segments):
        if owner0 == 1:
            if y1 != -100 or owner1 != 0:
                raise ValueError('first assistant labels/EOT must all be ignored')
        elif (y0, owner0) != (y1, owner1):
            raise ValueError('all other labels/owners must remain identical')
    return dict(before_turn_h1_to_h4=a, after_turn_h1_to_h4=b,
                removed_first_response_targets=before.targets - after.targets,
                removal_interpretation=REMOVAL_SCOPE)


def verify_copy(output, manifests, source_report, canonical):
    counts = Counter(); changed = Counter()
    for split in ('train', 'val'):
        verify(path(output), manifests[split])
        for old, new in zip_longest(stream(SOURCE, source_report['manifests'][split]), stream(output, manifests[split])):
            if old is None or new is None:
                raise ValueError('original/new split lengths differ')
            index, before, raw_before, _, _ = old
            new_index, after, raw_after, _, _ = new
            expected, spec = repaired_row(before, split, canonical)
            if index != new_index or after != expected or after['messages'] != before['messages']:
                raise ValueError('full source copy/order/messages or exact metadata-only difference violated')
            if spec is None:
                if raw_after != raw_before:
                    raise ValueError('unrepaired original JSONL bytes must remain identical')
            else:
                changed[spec['source_id']] += 1
            counts[split] += 1
    if changed != Counter({s['source_id']: 1 for s in REPAIRS}):
        raise ValueError('exactly one original TRAIN row per reviewed source required')
    return dict(compared_rows_by_split=dict(counts), metadata_changed_rows=sum(changed.values()),
                only_changed_field='meta.supervised_assistant_turns', messages_changed=0,
                unchanged_row_bytes='IDENTICAL', row_order_and_split='IDENTICAL',
                x_identity='ALL_UNCHANGED_ROWS_IDENTICAL; BOTH_REPAIRED_RECORD_X_LISTS_COMPARED')


def load_tokenizer():
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(path(TOKENIZER)))


def prepare(output=DEFAULT_OUTPUT):
    if output not in OUTPUTS:
        raise ValueError('only the explicit V4/candidate namespace is writable')
    destination = path(output)
    if destination.exists():
        raise FileExistsError('write-once candidate exists; preserve it, do not retry in place')
    report, inputs_before, canonical = load_inputs()
    code_before = hashes(CODE)
    tok = load_tokenizer()
    before_mass, after_mass, manifests, repairs = {}, {}, {}, []
    seen = Counter()
    destination.mkdir(parents=True, exist_ok=False)
    # On failure, partial new artifacts are preserved without a completion
    # report. Never delete/retry/repair either the source or this directory.
    for split in ('train', 'val'):
        old_mass, new_values = new_mass(), new_mass()
        writer = ShardWriter(destination, split, limit=report['manifests'][split]['limit_bytes'])
        for index, original, raw, shard, line_number in stream(SOURCE, report['manifests'][split]):
            candidate, spec = repaired_row(original, split, canonical)
            old_record = masked_record(original, tok)
            new_record = old_record if spec is None else masked_record(candidate, tok)
            add_mass(old_mass, original, old_record); add_mass(new_values, candidate, new_record)
            if spec is not None:
                seen[spec['source_id']] += 1
                repairs.append(dict(**spec, split=split, source_global_index=index,
                    source_shard=shard, source_line_number=line_number,
                    canonical_path=PUBLIC, canonical_line_number=spec['source_index'] + 1,
                    canonical_line_hash_unit='RAW_UTF8_JSONL_LINE_INCLUDING_LF',
                    source_row_sha256=hashlib.sha256(raw).hexdigest().upper(),
                    original_provenance=copy.deepcopy(original['meta']),
                    messages_sha256=hashlib.sha256(json.dumps(original['messages'], ensure_ascii=False,
                        sort_keys=True, separators=(',', ':')).encode()).hexdigest().upper(),
                    **audit_repair(old_record, new_record, spec)))
            writer.append(candidate)
        manifests[split] = writer.close(lineage=dict(preparation_schema=SCHEMA,
            original_report_sha256=SOURCE_REPORT_SHA, supervision_review_scope='TWO_PINNED_PUBLIC_SOURCES_ONLY'))
        before_mass[split], after_mass[split] = plain_mass(old_mass), plain_mass(new_values)
        if before_mass[split]['total'] != SOURCE_COUNTS[split]:
            raise ValueError('actual frozen V3 token/row counts differ')
        if (after_mass[split]['total']['rows'] != SOURCE_COUNTS[split]['rows']
                or after_mass[split]['total']['x_tokens'] != SOURCE_COUNTS[split]['x_tokens']):
            raise ValueError('row/input-token exposure must remain unchanged')
    expected_seen = Counter({s['source_id']: 1 for s in REPAIRS})
    removed = sum(s['expected_first_targets'] for s in REPAIRS)
    if (seen != expected_seen or before_mass['train']['total']['assistant_targets']
            - after_mass['train']['total']['assistant_targets'] != removed
            or after_mass['val'] != before_mass['val']):
        raise ValueError('two first-response removals only; VAL supervision unchanged')
    actual_updates = 4 * ((after_mass['train']['total']['rows'] + 127) // 128)
    if actual_updates != UPDATES:
        raise ValueError('complete four-pass/update schedule must remain unchanged')
    equivalence = verify_copy(output, manifests, report, canonical)
    if hashes(inputs_before) != inputs_before or hashes(CODE) != code_before:
        raise ValueError('original corpus/canonical/tokenizer or repair code changed during preparation')
    audit = dict(schema=SCHEMA, repairs=sorted(repairs, key=lambda r: r['source_index']),
        before_mass=before_mass, after_mass=after_mass, equivalence=equivalence,
        input_sha256=inputs_before, code_sha256=code_before,
        review_scope='Two PUBLIC sources explicitly repaired; all remaining rows not exhaustively reviewed.',
        removal_interpretation=REMOVAL_SCOPE,
        balance_scope='Language row ratios do NOT establish x-token or supervised-target balance.')
    write_json(output + '/supervision_audit.json', audit)
    counts = {split: after_mass[split]['total'] for split in ('train', 'val')}
    result = dict(schema='P101A_SFT_MTP_CORPUS_V1', preparation_schema=SCHEMA,
        status='SUPERVISION_REPAIR_PREPARED_NOT_ADMITTED', family='mtp', tag=TAG,
        manifests=manifests, counts=counts, tokenizer_sha256=TOKENIZER_SHA, epochs=4,
        actual_unique_train_x_tokens=counts['train']['x_tokens'],
        target_processed_x_tokens=4 * counts['train']['x_tokens'], learning_updates=UPDATES,
        language_rows={split: {lang: values['rows'] for lang, values in after_mass[split]['by_language'].items()}
            for split in ('train', 'val')},
        before_mass=before_mass, after_mass=after_mass,
        sources=dict(original_v3_report=SOURCE + '/report.json', original_v3_report_sha256=SOURCE_REPORT_SHA,
            original_sources=copy.deepcopy(report['sources']), public_train_sha256=PUBLIC_SHA),
        supervision_review_scope=dict(reviewed_public_sources=len(REPAIRS),
            reviewed_source_indices=[s['source_index'] for s in REPAIRS],
            total_train_rows=counts['train']['rows'],
            removal_interpretation=REMOVAL_SCOPE,
            other_rows='NOT_EXHAUSTIVELY_REVIEWED; accuracy not established by this repair'),
        semantic_quality='TWO_SOURCE_SUPERVISION_REPAIR_ONLY; REST_NOT_EXHAUSTIVELY_REVIEWED',
        formal_train_ready=False, training_admission='NOT_ADMITTED',
        versioned_consumer_integration='NOT_IMPLEMENTED; existing V3 controller/PINS not changed',
        public_benchmark_contamination='NOT_AUDITED_ALL_PRETRAINING_OR_PARAPHRASES',
        original_writes=0, model_constructions=0, checkpoint_loads=0, gpu_calls=0,
        equivalence_audit=equivalence, code_sha256=code_before,
        supervision_audit=dict(path='supervision_audit.json', sha256=digest(path(output + '/supervision_audit.json'))))
    write_json(output + '/report.json', result)
    print('[SUPERVISION_REPAIR_PREPARED_NOT_ADMITTED] ' + json.dumps(dict(
        output=output, counts=counts, learning_updates=UPDATES, removed_first_response_targets=removed,
        versioned_consumer_integration='NOT_IMPLEMENTED', training_admission='NOT_ADMITTED'), ensure_ascii=False), flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true'); action.add_argument('--check-only', action='store_true')
    parser.add_argument('--output', choices=OUTPUTS, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.check_only:
            print('[STATIC_ONLY] ' + json.dumps(dict(schema=SCHEMA, tag=TAG, output=args.output,
                code_sha256=hashes(CODE), source_report_sha256=SOURCE_REPORT_SHA,
                reviewed_source_indices=[s['source_index'] for s in REPAIRS],
                asset_reads=0, original_writes=0, model_constructions=0, gpu_calls=0,
                training_admission='NOT_ADMITTED', versioned_consumer_integration='NOT_IMPLEMENTED')), flush=True)
            return 0
        prepare(args.output)
        return 0
    except (FileExistsError, FileNotFoundError) as exc:
        print('[HOLD] ' + str(exc), file=sys.stderr, flush=True)
        return 8
    except Exception as exc:
        print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True)
        return 9


if __name__ == '__main__':
    raise SystemExit(main())
