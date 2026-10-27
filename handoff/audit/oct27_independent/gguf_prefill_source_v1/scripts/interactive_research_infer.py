#!/usr/bin/env python3
"""현재 연구 6종만 위한 GPU 수동 추론. --list/--help는 모델·GPU를 열지 않는다.

목록은 작은 완료 메타데이터만 확인한다. 선택 시 root가 동결한 독립 manifest와
실물 CP/header/core/route를 검증한다. 원 실험 Runtime/authority를 호출하지 않는다.
종료 성공은 정답성을 뜻하지 않는다.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
METADATA_LIMIT = 2_000_000
MANIFEST = 'handoff/audit/WIP_20261021_RESEARCH_INFER_MANIFEST.json'
MANIFEST_SCHEMA = 'TINYLM_RESEARCH_MANUAL_INFER_MANIFEST_V1'
REQUIRED_SOURCES = (
    'scripts/interactive_research_infer.py', 'research_infer.sh', 'scripts/shell/tinylm_env.sh',
    'tinylm/__init__.py', 'tinylm/paths.py', 'tinylm/config.py',
    'tinylm/model/__init__.py', 'tinylm/model/transformer.py', 'tinylm/model/modules.py',
    'tinylm/model/ternary.py', 'tinylm/model/ternary_kernel.py',
    'tinylm/infer/__init__.py', 'tinylm/infer/generate.py',
    'tinylm/data/__init__.py', 'tinylm/data/prepare.py', 'tinylm/data/loader.py', 'tinylm/data/sft.py',
    'tinylm/chat/__init__.py', 'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py', 'tinylm/chat/tokens.py',
    'scripts/p106b_weight_route.py', 'scripts/diag_p101a_sft_mtp.py', 'scripts/diag_p101a_mtp_parity.py',
)
HEADER_KEYS = frozenset(('cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage',
                         'quantization_route', 'experiment'))
EXISTING_IMPORT_DIRECTORIES = ('HF', 'HF/hub', 'data_cache', 'runs', 'runs/ckpt', 'runs/logs')


@dataclass(frozen=True)
class ModelSpec:
    name: str
    title: str
    family: str
    tag: str
    schema: str
    arm: str
    updates: int

    @property
    def checkpoint(self):
        if self.updates == 4543:
            stem = 'm100s10_ko-en_' + self.tag + '_' + self.arm + '_native.pt'
        else:
            stem = 'm100s10_ko-en_broad4_' + self.tag + '_' + self.arm + '.pt'
        return 'runs/ckpt/' + stem

    @property
    def report(self):
        return 'test_result/evidence/' + self.tag + '/train_' + self.arm + '/report.json'

    @property
    def activity(self):
        return 'test_result/evidence/' + self.tag + '/activity_train_' + self.arm + '.json'


MODELS = tuple(
    ModelSpec(prefix + '-' + suffix, title + ' ' + suffix.upper(), family, tag, schema, arm, updates)
    for prefix, title, family, tag, schema, updates in (
        ('native595', 'Native595', 'scripts.diag_p106b_native595',
         'p106b_native595_v1_s1337', 'P106B_NATIVE595_V1', 4543),
        ('old299-broad', 'Old299 + Broad704', 'scripts.diag_p106b_native_broad4_recovery',
         'p106b_native_broad4_recovery_v2_s1337', 'P106B_NATIVE_BROAD4_RECOVERY_V2', 704),
        ('new595-broad', 'New595 + Broad704', 'scripts.diag_p106b_native595_broad',
         'p106b_native595_broad_v1_s1337', 'P106B_NATIVE595_BROAD_V1', 704),
    )
    for suffix, arm in (('q', 'ternary'), ('f', 'float'))
)


def resolve_model(value):
    if not isinstance(value, str):
        raise ValueError('고정 모델의 표시 번호 또는 정확한 이름이 필요합니다.')
    value = value.strip().lower()
    if value in tuple(str(i) for i in range(1, len(MODELS) + 1)):
        return MODELS[int(value) - 1]
    for spec in MODELS:
        if value == spec.name:
            return spec
    raise ValueError('모르는 모델입니다. --list의 1~6 또는 정확한 이름을 쓰세요.')


def owned_path(relative, root=ROOT):
    relative = Path(relative)
    root = Path(root).absolute()
    if relative.is_absolute() or not relative.parts or any(p in ('.', '..') for p in relative.parts):
        raise ValueError('고정된 저장소 상대 경로만 허용합니다.')
    path = root / relative
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError('심볼릭 링크 경로는 허용하지 않습니다.')
        if ancestor == root:
            break
    return path


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def small_json(relative, root=ROOT):
    path = owned_path(relative, root)
    with path.open('rb') as stream:
        raw = stream.read(METADATA_LIMIT + 1)
    if len(raw) > METADATA_LIMIT:
        raise ValueError('작은 메타데이터 크기 한도를 넘었습니다.')
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('JSON 객체 메타데이터가 필요합니다.')
    return value, hashlib.sha256(raw).hexdigest().upper()


def is_sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9A-F]{64}', value) is not None


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest().upper()


def required_source_pins(root=ROOT):
    """Root export API: local source bytes only, no assets/model imports."""
    return {relative: file_sha(owned_path(relative, root)) for relative in REQUIRED_SOURCES}


def validate_import_environment(root=ROOT, environ=None):
    """Prevent paths.py's import-time mkdir from creating project/cache dirs.

    Only six explicit existing directories are stat'ed; no HF contents are read
    or listed. This does not claim to suppress third-party/system temp caches.
    Environment values are never silently rewritten by this guard.
    """
    root = Path(root)
    if not root.is_absolute() or '..' in root.parts:
        raise ValueError('고정 ROOT는 우회 없는 절대 경로여야 합니다.')
    environ = os.environ if environ is None else environ
    for name, expected in (('TINYLM_DIR', str(root)), ('TINYLM_HF', str(root / 'HF'))):
        if name in environ and environ[name] != expected:
            raise ValueError(name + '은 unset 또는 정확한 고정 절대 경로만 허용합니다. '
                             '환경을 덮어쓰거나 다른 위치에 디렉터리를 만들지 않습니다.')
    for relative in EXISTING_IMPORT_DIRECTORIES:
        path = root / relative
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError as exc:
            raise ValueError('import에 필요한 기존 프로젝트/cache 디렉터리가 없습니다: ' + relative) from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ValueError('기존 프로젝트/cache 경로는 실제 nonsymlink 디렉터리여야 합니다: ' + relative)


def descriptor(value, expected_path):
    if (not isinstance(value, dict) or set(value) != {'path', 'bytes', 'sha256'}
            or value.get('path') != expected_path or type(value.get('bytes')) is not int
            or value['bytes'] <= 0 or not is_sha(value.get('sha256'))):
        raise ValueError('고정 경로/bytes/SHA 파일 descriptor가 다릅니다: ' + expected_path)


def verify_descriptor(value, expected_path, root=ROOT):
    descriptor(value, expected_path)
    path = owned_path(expected_path, root)
    before = path.stat()
    if not path.is_file() or before.st_size != value['bytes'] or file_sha(path) != value['sha256']:
        raise ValueError('실물 파일 bytes/SHA가 다릅니다: ' + expected_path)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('검증 중 실물 파일이 바뀌었습니다: ' + expected_path)
    return path


def verify_manifest(root=ROOT):
    """Root recheck API: all six metadata/source bindings, no CP tensor or GPU.

    Full historical update/crop/schedule/parent readbacks belong to root export.
    Only the explicitly selected CP is byte-hashed/tensor-loaded by the loader.
    """
    manifest, _ = small_json(MANIFEST, root)
    if (manifest.get('schema') != MANIFEST_SCHEMA or manifest.get('inference_only') is not True
            or not isinstance(manifest.get('export_validation'), dict) or not manifest['export_validation']
            or not isinstance(manifest.get('source_sha256'), dict)
            or set(manifest['source_sha256']) != set(REQUIRED_SOURCES)
            or not isinstance(manifest.get('entries'), dict)
            or set(manifest['entries']) != {spec.name for spec in MODELS}):
        raise ValueError('독립 수동 manifest의 schema/전6종/소스 집합/검증 근거가 다릅니다.')
    if manifest['source_sha256'] != required_source_pins(root):
        raise ValueError('manifest에 고정된 추론 소스 SHA가 달라졌습니다.')
    descriptor(manifest.get('tokenizer'), TOKENIZER)
    if manifest['tokenizer']['sha256'] != TOKENIZER_SHA:
        raise ValueError('manifest의 tokenizer는 고정 local chat32여야 합니다.')
    for spec in MODELS:
        entry = manifest['entries'][spec.name]
        if (not isinstance(entry, dict) or entry.get('status') != 'COMPLETE'
                or entry.get('tag') != spec.tag or entry.get('arm') != spec.arm
                or type(entry.get('updates')) is not int or entry['updates'] != spec.updates
                or not is_sha(entry.get('core_sha256'))):
            raise ValueError('전6종 모두 실제 COMPLETE인 manifest만 허용합니다: ' + spec.name)
        for field, path in (('checkpoint', spec.checkpoint), ('report', spec.report), ('activity', spec.activity)):
            descriptor(entry.get(field), path)
        cp_path = owned_path(spec.checkpoint, root)
        if not cp_path.is_file() or cp_path.stat().st_size != entry['checkpoint']['bytes']:
            raise ValueError('전6종의 완료 CP 파일/bytes가 모두 존재해야 합니다: ' + spec.name)
        header = entry.get('header')
        if (not isinstance(header, dict) or set(header) != HEADER_KEYS or not isinstance(header.get('cfg'), dict)
                or not isinstance(header.get('quantization_route'), dict) or not isinstance(header.get('experiment'), dict)
                or type(header.get('step')) is not int or header['step'] != spec.updates
                or header.get('tokenizer_sha256') != TOKENIZER_SHA or header.get('tokenizer_lineage') != 'chat32'
                or header['quantization_route'].get('mode') != spec.arm
                or entry.get('header_sha256') != canonical_sha(header)
                or entry.get('cfg_sha256') != canonical_sha(header['cfg'])
                or entry.get('route_sha256') != canonical_sha(header['quantization_route'])):
            raise ValueError('정확 CP header/cfg/route SHA가 다릅니다: ' + spec.name)
        state = inspect_model(spec, root)
        if state['status'] != 'READY_METADATA_ONLY':
            raise ValueError('manifest의 완료 원형이 현재 metadata와 다릅니다: ' + spec.name)
        report = state['report']
        if (entry['report']['sha256'] != state['report_sha256']
                or entry['checkpoint']['sha256'] != report['checkpoint_sha256']
                or entry['core_sha256'] != report['final_core_sha256']
                or header['quantization_route'] != report['quantization_route']):
            raise ValueError('manifest와 실제 report의 CP/core/route 결합이 다릅니다: ' + spec.name)
        verify_descriptor(entry['report'], spec.report, root)
        verify_descriptor(entry['activity'], spec.activity, root)
    return manifest


def inspect_model(spec, root=ROOT):
    """Only the two small report/activity files; never inspect CP/data contents."""
    result = dict(name=spec.name, status='PENDING', reason='', report=None, report_sha256=None)
    try:
        report, report_sha = small_json(spec.report, root)
        activity, _ = small_json(spec.activity, root)
        if (activity.get('complete') is not True or type(activity.get('returncode')) is not int
                or activity['returncode'] != 0):
            result.update(status='INCOMPLETE', reason='닫힌 성공 activity가 없습니다.')
            return result
        expected = dict(schema=spec.schema, tag=spec.tag, arm=spec.arm)
        if (any(report.get(k) != v or activity.get(k) != v for k, v in expected.items())
                or report.get('status') != 'TRAIN_COMPLETE' or report.get('cost') is not False
                or type(report.get('updates')) is not int or report['updates'] != spec.updates
                or report.get('checkpoint') != spec.checkpoint or report.get('checkpoint_writes') != 1
                or report.get('optimizer_saved') is not False
                or not is_sha(report.get('checkpoint_sha256')) or not is_sha(report.get('final_core_sha256'))
                or activity.get('mode') != 'train' or activity.get('key') != 'train_' + spec.arm
                or activity.get('error_type') is not None or activity.get('result_sha256') != report_sha):
            raise ValueError('family/route/완료 report와 activity의 결합이 다릅니다.')
        route = report.get('quantization_route')
        if not isinstance(route, dict) or route.get('mode') != spec.arm:
            raise ValueError('명시한 Q/F route 메타데이터가 없습니다.')
        result.update(status='READY_METADATA_ONLY', reason='선택 시 strict 원형/CP 검증 필요',
                      report=report, report_sha256=report_sha)
    except FileNotFoundError:
        result['reason'] = '완료 report 또는 닫힌 activity가 아직 없습니다.'
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result.update(status='INVALID_METADATA', reason=str(exc))
    return result


def list_models(root=ROOT):
    print('연구 GPU 모델 6종: Q=삼진, F=실수. 번호는 고정이며 품질 순위가 아닙니다.')
    for index, spec in enumerate(MODELS, 1):
        state = inspect_model(spec, root)
        print(f"{index}. {spec.name} — {spec.title} [{state['status']}]")
        print('   ' + state['reason'])
    print('목록은 작은 report/activity만 확인합니다. CP tensor/model/GPU 조회 0회.')


def require_idle_gpu(run=None, pid=None):
    """NVML-backed nvidia-smi point queries; all query/parse errors fail closed."""
    run = subprocess.run if run is None else run
    pid = os.getpid() if pid is None else pid

    def query(fields, kind):
        try:
            reply = run(['nvidia-smi', '--query-' + kind + '=' + fields,
                         '--format=csv,noheader,nounits'],
                        capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError('NVML GPU 점조회 실패: 모델을 열지 않습니다.') from exc
        if reply.returncode != 0 or reply.stderr.strip():
            raise RuntimeError('NVML GPU 점조회 오류: 모델을 열지 않습니다.')
        return [row.strip() for row in reply.stdout.splitlines() if row.strip()]

    devices = query('uuid', 'gpu')
    if len(devices) != 1 or re.fullmatch(r'GPU-[0-9A-Fa-f-]+', devices[0]) is None:
        raise RuntimeError('이 유틸은 조회 가능한 단일 CUDA GPU만 지원합니다.')
    others = []
    for row in query('pid,gpu_uuid', 'compute-apps'):
        fields = [field.strip() for field in row.split(',')]
        if (len(fields) != 2 or not fields[0].isdigit() or int(fields[0]) < 1
                or fields[1] != devices[0]):
            raise RuntimeError('NVML compute PID 결과가 불명확해 모델을 열지 않습니다.')
        if int(fields[0]) != pid:
            others.append(int(fields[0]))
    if others:
        raise RuntimeError('다른 GPU compute PID가 있습니다: ' + ', '.join(map(str, sorted(set(others)))))
    return dict(scope='NVML_POINT_QUERY_ONLY_NOT_CONTINUOUS_OR_OOM_GUARANTEE',
                gpu_uuid=devices[0], competing_compute_pids=[])


def state_fingerprint(base):
    """Exactly diag_p101a_sft_mtp.state_fingerprint's core definition; no import."""
    sha = hashlib.sha256()
    for name, value in sorted(base.state_dict().items()):
        if name in ('mtp_up2', 'mtp_up3', 'mtp_up4'):
            continue
        value = value.detach().cpu().contiguous()
        sha.update((name + str(value.shape) + str(value.dtype)).encode())
        sha.update(value.view(-1).view(__import__('torch').uint8).numpy().tobytes())
    return sha.hexdigest().upper()


def inference_modules(root=ROOT):
    """Import only model/config and the instance-local route; no experiment runtime."""
    validate_import_environment(root)
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts import p106b_weight_route
    return torch, TMTConfig, TiedMLPTransformer, p106b_weight_route


def local_tokenizer(manifest, root=ROOT):
    path = verify_descriptor(manifest['tokenizer'], TOKENIZER, root)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(path))
    if (tok.get_vocab_size() != 32768 or tok.token_to_id('<|im_start|>') != 3
            or tok.token_to_id('<|im_end|>') != 4 or tok.token_to_id('<eos>') != 2):
        raise ValueError('고정 local chat32의 실제 어휘/경계 토큰이 다릅니다.')
    return tok


def read_selected_payload(torch, spec, entry, root=ROOT):
    """Hash and tensor-load the SAME read-only file handle, on CPU only."""
    path = owned_path(spec.checkpoint, root)
    descriptor(entry['checkpoint'], spec.checkpoint)
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if before.st_size != entry['checkpoint']['bytes']:
            raise ValueError('선택 CP bytes가 manifest와 다릅니다.')
        sha = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            sha.update(chunk)
        if sha.hexdigest().upper() != entry['checkpoint']['sha256']:
            raise ValueError('선택 CP SHA가 manifest와 다릅니다.')
        stream.seek(0)
        payload = torch.load(stream, map_location='cpu', weights_only=True)
        after = os.fstat(stream.fileno())
        current = path.stat()
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if stamp(before) != stamp(after) or stamp(after) != stamp(current):
            raise ValueError('읽는 동안 선택 CP가 바뀌었습니다.')
    if not isinstance(payload, dict) or set(payload) != HEADER_KEYS | {'model'}:
        raise ValueError('선택 CP의 정확한 weight-only header/model keys가 다릅니다.')
    header = {key: payload[key] for key in HEADER_KEYS}
    if canonical_sha(header) != entry['header_sha256']:
        raise ValueError('실제 CP header가 동결 manifest와 다릅니다.')
    return payload


def validate_cfg(cfg, header):
    if (canonical_sha(asdict(cfg)) != canonical_sha(header['cfg'])
            or cfg.vocab_size != 32768 or cfg.max_seq_len != 1024 or cfg.mtp_aux
            or cfg.n_layers != 14 or cfg.dim != 768 or cfg.tie_mlp):
        raise ValueError('실제 연구 dense14/chat32/1024/MTPoff cfg가 다릅니다.')


@contextmanager
def selected_runtime(spec, *, root=ROOT):
    """Independent strict manual loader. No historical family/authority calls."""
    if spec not in MODELS:
        raise ValueError('고정된 연구6종만 선택할 수 있습니다.')
    try:
        manifest = verify_manifest(root)
    except FileNotFoundError as exc:
        raise ValueError('MANUAL_MANIFEST_NOT_READY: 독립 수동 manifest/완료6종 원형이 '
                         '없습니다. 모델/GPU를 열지 않았습니다.') from exc
    manifest_sha = canonical_sha(manifest)
    entry = manifest['entries'][spec.name]
    # No model imports until every closed metadata/source binding is validated.
    validate_import_environment(root)
    tok = local_tokenizer(manifest, root)
    torch, config_type, model_type, method = inference_modules(root)
    active = payload = model = cpu_route = route = None
    gpu_attempted = False
    try:
        payload = read_selected_payload(torch, spec, entry, root)
        method.validate_route_metadata(payload['quantization_route'], spec.arm)
        cfg = config_type(**payload['cfg'])
        validate_cfg(cfg, entry['header'])
        with torch.device('cpu'):
            model = model_type(cfg)
        # Validate route support, every state key/shape/dtype/layout/alias and
        # actual full core on CPU before the model can move to CUDA.
        with method.weight_route(model, spec.arm) as cpu_route:
            cpu_route.assert_active()
            method.load_routed_state(model, payload, spec.arm)
            if state_fingerprint(model) != entry['core_sha256']:
                raise ValueError('선택 CP의 실제 CPU core SHA가 다릅니다.')
        cpu_route = payload = None
        if canonical_sha(verify_manifest(root)) != manifest_sha:
            raise ValueError('CPU 검증 중 수동 manifest가 바뀌었습니다.')
        point = require_idle_gpu()
        if not torch.cuda.is_available():
            raise RuntimeError('이 연구 loader는 CUDA GPU 전용입니다. CPU fallback은 없습니다.')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        gpu_attempted = True
        model = model.cuda()
        with method.weight_route(model, spec.arm) as route:
            before = None
            try:
                model.clear_quant(); model.eval(); model.set_anneal(1.)
                with torch.no_grad():
                    model.freeze_quant()
                route.assert_active()
                if route.metadata != entry['header']['quantization_route']:
                    raise ValueError('실제로 설치한 Q/F route가 manifest와 다릅니다.')
                before = state_fingerprint(model)
                if before != entry['core_sha256']:
                    raise ValueError('실제 GPU 본체 core가 CPU/manifest와 다릅니다.')
                active = dict(torch=torch, model=model, cfg=cfg, tokenizer=tok, route=route,
                    checkpoint=spec.checkpoint, checkpoint_sha256=entry['checkpoint']['sha256'],
                    core_sha256=before, report_sha256=entry['report']['sha256'],
                    manifest_sha256=manifest_sha, tokenizer_sha256=TOKENIZER_SHA,
                    quantization_route=route.metadata, name=spec.name, gpu_point_query=point,
                    project_cache_directories='EXISTING_ONLY_NO_NEW_PROJECT_CACHE_DIRECTORIES',
                    root=str(root),
                    precision='FP32_MATH', body_check_scope='CPU_LOAD_GPU_LOAD_AND_SESSION_EXIT')
                print('[MODEL] ' + json.dumps({k: v for k, v in active.items()
                      if k not in ('torch', 'model', 'cfg', 'tokenizer', 'route')}, ensure_ascii=False), flush=True)
                yield active
            finally:
                try:
                    if before is not None:
                        route.assert_active()
                        after = state_fingerprint(model)
                        if before != after:
                            raise RuntimeError('수동 추론 세션 중 본체가 바뀌었습니다.')
                        if canonical_sha(verify_manifest(root)) != manifest_sha:
                            raise RuntimeError('수동 추론 중 manifest/원형/소스 바인딩이 바뀌었습니다.')
                        print('[BODY_UNCHANGED] ' + after + ' (CPU/GPU load + session exit)', flush=True)
                finally:
                    model.clear_quant()
    finally:
        try:
            if model is not None:
                model.clear_quant()
        finally:
            if active is not None:
                active.clear()
            active = payload = model = cpu_route = route = None
            gc.collect()
            if gpu_attempted:
                torch.cuda.empty_cache()


def prompt_messages(question, history=()):
    if not isinstance(question, str) or not question.strip():
        raise ValueError('빈 질문은 허용하지 않습니다.')
    messages = []
    if len(history) % 2:
        raise ValueError('완료된 실제 user/assistant 이력만 허용합니다.')
    for index, message in enumerate(history):
        if (not isinstance(message, dict) or set(message) != {'role', 'content'}
                or message['role'] != ('user' if index % 2 == 0 else 'assistant')
                or not isinstance(message['content'], str)):
            raise ValueError('완료된 실제 user/assistant 이력만 허용합니다.')
        messages.append(dict(message))
    messages.append(dict(role='user', content=question))
    return messages


def precision_types(root=ROOT):
    """Reuse the two pinned class bodies without importing the experiment driver."""
    path = owned_path('scripts/diag_p101a_mtp_parity.py', root)
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = ('CaptureTokens', 'PrecisionForward')
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in names]
    if tuple(node.name for node in classes) != names or any(node.bases or node.decorator_list for node in classes):
        raise ValueError('고정 precision helper의 두 독립 클래스 계약이 다릅니다.')
    namespace = dict(nullcontext=nullcontext, __name__='_tinylm_research_precision_only')
    exec(compile(ast.Module(body=classes, type_ignores=[]), str(path), 'exec'), namespace)
    return tuple(namespace[name] for name in names)


def generation_tools(root=ROOT):
    validate_import_environment(root)
    from tinylm.infer.generate import sample
    capture, forward = precision_types(root)
    return sample, capture, forward


def answer_from_tokens(tok, prefix, decoded_ids, metadata, max_new):
    """Remove only the authenticated final EOT/EOS; retain all other body IDs."""
    if (not isinstance(decoded_ids, list) or any(type(v) is not int or v < 0 for v in decoded_ids)
            or decoded_ids[:len(prefix)] != prefix
            or type(metadata.get('generated_tokens')) is not int
            or len(decoded_ids) - len(prefix) != metadata['generated_tokens']
            or not 1 <= metadata['generated_tokens'] <= max_new):
        raise ValueError('실제 prefix/생성 ID/토큰 수 영수증이 다릅니다.')
    generated = decoded_ids[len(prefix):]
    reason, terminal = metadata.get('finish_reason'), []
    if reason == 'STOP_SEQUENCE':
        terminal = [4]
        if metadata.get('matched_stop_sequence') != terminal:
            raise ValueError('EOT 종료 영수증이 다릅니다.')
    elif reason == 'EOS':
        terminal = [2]
        if metadata.get('matched_stop_sequence') is not None:
            raise ValueError('EOS 종료 영수증이 다릅니다.')
    elif reason != 'MAX_NEW' or len(generated) != max_new or metadata.get('matched_stop_sequence') is not None:
        raise ValueError('정의된 EOT/EOS/MAX_NEW 종료가 아닙니다.')
    if terminal and generated[-1:] != terminal:
        raise ValueError('실제 마지막 토큰이 종료 영수증과 다릅니다.')
    content = generated[:-1] if terminal else generated
    if any(token in (2, 4) for token in content):
        raise ValueError('답변 본문 안에 종료 토큰이 남아 있습니다.')
    return tok.decode(content, skip_special_tokens=False), dict(metadata,
        prompt_tokens=len(prefix), generated_ids=generated, content_tokens=len(content),
        terminal_ids=terminal, terminal_only_removed=True)


def emit(active, question, max_new=128, history=()):
    if type(max_new) is not int or not 1 <= max_new <= 1024:
        raise ValueError('max-new는 1~1024 정수여야 합니다.')
    root = Path(active.get('root', ROOT))
    validate_import_environment(root)
    from tinylm.chat.serialize import serialize
    messages = prompt_messages(question, history)
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    tok, cfg = active['tokenizer'], active['cfg']
    prefix = tok.encode(prompt).ids
    if len(prefix) + max_new > cfg.max_seq_len:
        raise ValueError(f'입력 {len(prefix)} + 생성 {max_new} > 문맥 {cfg.max_seq_len}; '
                         '자동 절단하지 않습니다. :reset 또는 짧은 질문을 쓰세요.')
    active['route'].assert_active()
    sample, capture_type, forward_type = generation_tools(root)
    capture = capture_type(tok)
    with active['torch'].no_grad():
        _, metadata = sample(forward_type(active['model'], 'fp32_math'), cfg, capture, prompt,
            max_new=max_new, temperature=0., top_k=1, device='cuda', use_cache=True,
            logits_last_only=True, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
    active['route'].assert_active()
    answer, result = answer_from_tokens(tok, prefix, capture.decoded_ids, metadata, max_new)
    result.update(precision='FP32_MATH', tf32=False, use_cache=True, mtp=False,
                  temperature=0., top_k=1, actual_history=bool(history),
                  prompt_sha256=hashlib.sha256(prompt.encode('utf-8')).hexdigest().upper())
    return answer, result


def print_answer(answer, metadata):
    print('답변:', answer, flush=True)
    print('[GENERATION] ' + json.dumps(metadata, ensure_ascii=False), flush=True)
    print('종료 표시는 정답 판정이 아닙니다.', flush=True)


def run_prompts(active, args):
    if args.prompt is not None:
        print_answer(*emit(active, args.prompt, args.max_new))
        return
    history = []
    print('GPU 수동 추론. :reset=이력 초기화, :quit=종료. '
          + ('자신의 실제 답만 이력에 보존합니다.' if args.history else '매 질문은 독립입니다.'))
    while True:
        try:
            question = input('질문> ')
        except EOFError:
            return
        if question.strip() in (':quit', ':q'):
            return
        if question.strip() == ':reset':
            history.clear()
            print('이력을 초기화했습니다.')
            continue
        try:
            answer, metadata = emit(active, question, args.max_new, history)
        except ValueError as exc:
            print('[입력/생성 거부]', exc, flush=True)
            continue
        print_answer(answer, metadata)
        if args.history:
            history.extend((dict(role='user', content=question), dict(role='assistant', content=answer)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='작은 완료 메타데이터만 표시; 모델/GPU 0')
    parser.add_argument('--model', help='고정 번호 1~6 또는 --list의 정확한 이름')
    parser.add_argument('--prompt', help='비대화 1회 질문; nonTTY에서는 --model과 함께 필수')
    parser.add_argument('--history', action='store_true', help='TTY에서 자신의 실제 응답만 이력으로 사용')
    parser.add_argument('--max-new', type=int, default=128, help='생성 예산, 기본128; 문맥 자동 절단 없음')
    args = parser.parse_args(argv)
    if not 1 <= args.max_new <= 1024:
        parser.error('--max-new는 1~1024여야 합니다.')
    if args.history and args.prompt is not None:
        parser.error('--history는 TTY 대화 전용입니다. 1회 --prompt와 함께 쓰지 않습니다.')
    if args.list:
        if args.model is not None or args.prompt is not None:
            parser.error('--list는 --model/--prompt와 함께 쓰지 않습니다.')
        list_models()
        return 0
    if not sys.stdin.isatty() and (args.model is None or args.prompt is None):
        parser.error('nonTTY에서는 --model NAME --prompt TEXT가 모두 필요합니다. 모델을 열지 않았습니다.')
    if args.prompt is not None and not args.prompt.strip():
        parser.error('빈 --prompt는 허용하지 않습니다.')
    try:
        if args.model is None:
            list_models()
            choice = input('모델 번호/정확한 이름 (:quit=종료)> ').strip()
            if choice in (':quit', ':q'):
                return 0
            spec = resolve_model(choice)
        else:
            spec = resolve_model(args.model)
        print('GPU 전용·단일 모델 수동 추론. FP32_MATH/TF32off/KVon/MTPoff/greedy. '
              '다른 모델 선택은 이 프로세스를 종료한 뒤 재실행하세요.', flush=True)
        print('실험 산출물/CP/로그 저장0·추가 프로젝트/cache 디렉터리 생성0. '
              'third-party/시스템 임시캐시까지 전무하다는 뜻은 아닙니다.', flush=True)
        with selected_runtime(spec) as active:
            run_prompts(active, args)
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\n[종료] 수동 입력이 끝났습니다.', flush=True)
        return 130
    except Exception as exc:
        print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
