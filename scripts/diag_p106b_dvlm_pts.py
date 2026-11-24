"""TRAIN128 PTS admission, original CE preservation and fixed native-case selection."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import unittest

import tinylm
from scripts import p106b_dvlm_pts as pts
from scripts.p106b_alm_bytes import student_piece_bytes
from scripts.p106b_shards import ShardWriter, verify as verify_shards

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p106b_dvlm_pts_v1_20261117'
PARENT = ROOT / 'test_result/evidence/p106b_actd_top128_v1_20261113'
PROFILE = BASE / 'profile.json'
PLAN = ROOT / 'test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md'
STUDENT_TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
TEACHER_TOKENIZER = 'HF/models--Qwen3-0.6B-Base/tokenizer.json'
DEADLINE = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 11, 17, 7, 40, tzinfo=timezone.utc)
SOURCES = ('scripts/p106b_dvlm_pts.py', 'scripts/test_p106b_dvlm_pts.py',
           'scripts/diag_p106b_dvlm_pts.py', 'scripts/test_diag_p106b_dvlm_pts.py',
           'scripts/p106b_alm_bytes.py', 'scripts/p106b_shards.py')


class AdmissionWriter(ShardWriter):
    """Flush owned partial evidence without declaring an incomplete corpus complete."""

    def preserve_partial(self):
        self._finish()
        return dict(stem=self.stem, complete_manifest=self.manifest_path.exists(),
                    shards=list(self.shards), rows=self._total_rows, bytes=self._total_bytes)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(data) >= 20_000_000:
        raise ValueError('split metadata below20MB')
    with Path(path).open('xb') as stream:
        stream.write(data)


def guard(start=None):
    if datetime.now(timezone.utc) >= CUTOFF:
        raise TimeoutError('current158 new-work cutoff reached')
    if start is not None and time.monotonic() - start > 600:
        raise TimeoutError('PTS CPU admission600sec cap reached')
    if (BASE / 'STOP').exists():
        raise TimeoutError('owned PTS STOP present')
    if shutil.disk_usage(BASE if BASE.exists() else BASE.parent).free < 1_000_000_000:
        raise OSError('PTS admission requires1GB free disk reserve')


def bytelevel_metadata(path):
    raw = read(path)
    if raw.get('model', {}).get('type') != 'BPE' or raw.get('decoder', {}).get('type') != 'ByteLevel':
        raise pts.AdmissionHold('explicit native BPE/ByteLevel metadata required')
    ordinary = {token_id: spelling for spelling, token_id in raw['model']['vocab'].items()}
    added = {row['id']: row['content'] for row in raw.get('added_tokens', [])}
    if len(ordinary) != len(raw['model']['vocab']) or any(type(i) is not int for i in (*ordinary, *added)):
        raise ValueError('native tokenizer IDs are not unique integers')
    return ordinary, added


def native_pieces(ids, ordinary, added):
    pieces = []
    for token_id in ids:
        if token_id in added:
            pieces.append(added[token_id].encode('utf-8', errors='strict'))
        elif token_id in ordinary:
            pieces.append(student_piece_bytes(ordinary[token_id]))
        else:
            raise pts.AdmissionHold('encoded undeclared native token ID')
    return tuple(pieces)


def parent_rows():
    parent = read(PARENT / 'profile.json')
    manifest = parent['prepared_manifest']
    if (parent['corpus_admitted'] is not False or manifest['rows'] != 128
            or manifest['lineage']['split'] != 'TRAIN_ONLY'
            or parent['counts']['ce_targets'] != 772 or parent['counts']['actual_x_tokens'] != 32216):
        raise ValueError('exact original unadmitted TRAIN128/CE772/x32216 required')
    verify_shards(PARENT, manifest)
    rows = []
    for shard in manifest['shards']:
        rows.extend(json.loads(line) for line in (PARENT / shard['path']).read_text(encoding='utf-8').splitlines())
    if len(rows) != 128 or len({row['row_id'] for row in rows}) != 128:
        raise ValueError('complete unique TRAIN128 required')
    return parent, rows


def prepare():
    guard()
    if BASE.exists():
        raise FileExistsError('preserve PTS admission namespace')
    import tokenizers
    parent, rows = parent_rows()
    if digest(ROOT / STUDENT_TOKENIZER) != parent['references'][STUDENT_TOKENIZER]:
        raise ValueError('same original student tokenizer required')
    for name in (STUDENT_TOKENIZER, TEACHER_TOKENIZER):
        resolved = (ROOT / name).resolve(strict=True)
        allowed = (ROOT / ('HF' if name.startswith('HF/') else 'data_cache')).resolve()
        if not resolved.is_relative_to(allowed):
            raise ValueError('tokenizer resolves outside exact owned asset root')
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in
        ('scripts.test_p106b_dvlm_pts', 'scripts.test_diag_p106b_dvlm_pts'))
    for name in (STUDENT_TOKENIZER, TEACHER_TOKENIZER):
        bytelevel_metadata(ROOT / name)
    checked = unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun != 21:
        raise RuntimeError('all21 meaningful PTS/admission contracts required')
    guard()
    BASE.mkdir()
    with (BASE / 'initial_plan.md').open('xb') as stream:
        stream.write(PLAN.read_bytes())
    inputs = {str((PARENT / 'profile.json').relative_to(ROOT)): digest(PARENT / 'profile.json')}
    for shard in parent['prepared_manifest']['shards']:
        inputs[str((PARENT / shard['path']).relative_to(ROOT))] = shard['sha256']
    for name in (STUDENT_TOKENIZER, TEACHER_TOKENIZER):
        inputs[name] = digest(ROOT / name)
    p = dict(schema='P106B_DVLM_PTS_ADMISSION_V1', authority_directive=158, authority_end=DEADLINE.isoformat(),
        new_work_cutoff=CUTOFF.isoformat(), sources={name: digest(ROOT / name) for name in SOURCES},
        inputs=inputs, initial_plan_sha256=digest(BASE / 'initial_plan.md'), original_rows=len(rows),
        original_x_tokens=32216, original_ce_targets=772, original_languages={'ko':64,'en':64},
        student_tokenizer=STUDENT_TOKENIZER, teacher_tokenizer=TEACHER_TOKENIZER,
        max_complete_PTS_length=1024, whole_sample_hold_policy=True, independent_UTF8_student_required=True,
        native_case_selection='FIRST_FOUR_ADMITTED_PER_LANGUAGE_IN_ORIGINAL_ORDER;NO_MODEL_OR_OUTPUT_SELECTION',
        native_expected_max_cases=8, CPU_contracts=checked.testsRun, model_loads=0, CUDA_initializations=0,
        runtime=dict(python=sys.version, executable=sys.executable, tokenizers=tokenizers.__version__),
        max_wall_seconds=600, max_output_bytes=100_000_000, minimum_free_bytes=1_000_000_000,
        training=False, corpus_admitted=False, quality_claim=False, libraries_installed=0, downloads=0)
    write_new(PROFILE, p)
    print('[DVLM_PTS_PREPARED]exact frozen128;byte/PTS/next-target admission;no model/GPU', flush=True)


def verify():
    guard()
    p = read(PROFILE)
    if (p['schema'] != 'P106B_DVLM_PTS_ADMISSION_V1' or p['authority_directive'] != 158
            or p['authority_end'] != DEADLINE.isoformat() or p['new_work_cutoff'] != CUTOFF.isoformat()
            or p['initial_plan_sha256'] != digest(BASE / 'initial_plan.md')):
        raise ValueError('exact current authority and original plan required')
    for name, expected in {**p['sources'], **p['inputs']}.items():
        if digest(ROOT / name) != expected:
            raise ValueError('frozen PTS source/input changed: ' + name)
    return p


def _admit(p, out, writers, start):
    from tokenizers import Tokenizer
    student = Tokenizer.from_file(str(ROOT / p['student_tokenizer']))
    teacher = Tokenizer.from_file(str(ROOT / p['teacher_tokenizer']))
    sv, sa = bytelevel_metadata(ROOT / p['student_tokenizer'])
    tv, ta = bytelevel_metadata(ROOT / p['teacher_tokenizer'])
    parent, rows = parent_rows()
    all_writer = AdmissionWriter(out, 'admission', limit=3_000_000)
    layout_writer = AdmissionWriter(out, 'layouts', limit=3_000_000)
    writers.extend((all_writer, layout_writer))
    selected, accepted, held = [], Counter(), Counter()
    original_x = original_ce = accepted_ce = 0
    decode_student = lambda ids: student.decode(list(ids), skip_special_tokens=False)
    decode_teacher = lambda ids: teacher.decode(list(ids), skip_special_tokens=False)
    encode_teacher = lambda text: teacher.encode(text, add_special_tokens=False).ids
    for row in rows:
        guard(start)
        if sum(writer._total_bytes for writer in writers) >= p['max_output_bytes']:
            raise OSError('PTS owned output byte cap reached; partial evidence retained')
        saved = row['packed']['student']; text = row['packed']['text']
        ids, labels, mask = saved['ids'], saved['labels'], saved['supervised']
        if (student.encode(text, add_special_tokens=False).ids != ids
                or len(ids) != len(labels) or labels != [i if keep else -100 for i, keep in zip(ids, mask)]
                or sum(i != -100 for i in labels[1:]) != row['ce_targets']):
            raise ValueError('unchanged original student IDs/full-label shift required')
        original_x += len(ids) - 1; original_ce += row['ce_targets']
        receipt = dict(row_id=row['row_id'], language=row['language'], original_ce_targets=row['ce_targets'],
            original_x_tokens=len(ids)-1, source_row_sha256=row['source_row_sha256'],
            original_text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest().upper(), original_labels_unchanged=True)
        try:
            teacher_ids = encode_teacher(text)
            layout = pts.prepare_layout(ids, teacher_ids, native_pieces(ids, sv, sa), native_pieces(teacher_ids, tv, ta),
                decode_student=decode_student, encode_teacher=encode_teacher, decode_teacher=decode_teacher,
                max_length=p['max_complete_PTS_length'])
            targets = layout.head_targets(mask)
            if tuple(labels[1:] + [-100]) != targets or sum(t != -100 for t in targets) != row['ce_targets']:
                raise ValueError('exactly once next-student shift changed original CE')
            language = row['language']; accepted[language] += 1; accepted_ce += row['ce_targets']
            receipt.update(status='ADMITTED_TECHNICAL_LAYOUT_ONLY', physical_PTS_tokens=len(layout.input_ids),
                native_teacher_tokens=len(teacher_ids), original_student_tokens=len(ids), alignment_groups=len(layout.groups),
                multi_student_groups=sum(len(g.student)>1 for g in layout.groups))
            layout_writer.append(dict(**receipt, layout=asdict(layout), head_targets=targets,
                next_target_turn_ids=saved['turn_ids'][1:] + [-1], original_student_labels=labels))
            if sum(item['language'] == language for item in selected) < 4:
                selected.append(dict(row_id=row['row_id'],language=language,physical_PTS_tokens=len(layout.input_ids),alignment_groups=len(layout.groups)))
        except pts.AdmissionHold as error:
            held[str(error)] += 1
            receipt.update(status='WHOLE_SAMPLE_HOLD', reason=str(error), original_ce_preserved_in_source=True)
        all_writer.append(receipt)
    if original_x != p['original_x_tokens'] or original_ce != p['original_ce_targets'] or sum(accepted.values()) + sum(held.values()) != 128:
        raise ValueError('full original128/x32216/CE772 accounting differs')
    lineage = dict(profile_sha256=digest(PROFILE), original_parent_sha256=digest(PARENT/'profile.json'), corpus_admitted=False)
    manifests = dict(admission=all_writer.close(lineage=lineage))
    manifests['layouts'] = layout_writer.close(lineage=lineage) if sum(accepted.values()) else None
    for manifest in manifests.values():
        if manifest is not None:
            verify_shards(out, manifest)
    report = dict(schema=p['schema'], status='PTS_CPU_ADMISSION_COMPLETE_NOT_MODEL_OR_QUALITY',
        profile_sha256=digest(PROFILE), original_rows=128, original_x_tokens=original_x, original_ce_targets=original_ce,
        accepted_rows_by_language=dict(accepted), held_rows_by_reason=dict(held), accepted_ce_targets=accepted_ce,
        held_ce_targets=original_ce-accepted_ce, original_source_unchanged=True,
        manifests=manifests, selected_native_cases=selected, model_loads=0, CUDA_initializations=0,
        training=False, optimizer_updates=0, checkpoint_writes=0, corpus_admitted=False, quality_claim=False,
        wall_seconds=time.monotonic()-start, returncode=0)
    verify()
    return report


def actual():
    p = verify()
    start = time.monotonic()
    out = BASE / 'cpu'
    out.mkdir()
    writers = []
    try:
        report = _admit(p, out, writers, start)
        write_new(out / 'report.json', report)
    except BaseException as error:
        partial, closure_errors = [], []
        for writer in writers:
            try:
                partial.append(writer.preserve_partial())
            except Exception as closure:
                closure_errors.append(dict(type=type(closure).__name__, message=str(closure)))
        failure = dict(schema=p['schema'], status='PTS_CPU_ADMISSION_INCOMPLETE', returncode=9,
            profile_sha256=digest(PROFILE), wall_seconds=time.monotonic()-start,
            error=dict(type=type(error).__name__, message=str(error)), partial_writers=partial,
            closure_errors=closure_errors, model_loads=0, CUDA_initializations=0,
            corpus_admitted=False, quality_claim=False, training=False,
            traceback=traceback.format_exc())
        try:
            write_new(out / 'failure.json', failure)
        except Exception as closure:
            print('[DVLM_PTS_REPORT_CLOSURE_FAILURE]' + repr(closure), file=sys.stderr, flush=True)
        raise
    print('[DVLM_PTS_CPU_COMPLETE]'+json.dumps(dict(
        accepted=sum(report['accepted_rows_by_language'].values()),
        held=sum(report['held_rows_by_reason'].values()),
        native_cases=len(report['selected_native_cases']), CE_preserved=report['original_ce_targets'])), flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','check','actual'))
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='check':verify();print('[DVLM_PTS_CHECK]exact current source/input;model/GPU0')
    else:actual()


if __name__=='__main__':
    main()
