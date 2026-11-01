"""고정 공식 archive의 명시 파일을 원 source/실제 runtime과 바이트 대조한다."""
import hashlib
from pathlib import Path, PurePosixPath
import tarfile


def verify_files(names, *, archive, source, runtime=None):
    wanted = set(names)
    if not wanted or len(wanted) != len(names):
        raise ValueError('중복 없는 명시 공식 파일 목록 필요')
    for name in wanted:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name or not name.startswith('lm_eval/'):
            raise ValueError('공식 package 안의 정규 상대경로 필요')
    found = {}
    with tarfile.open(archive, 'r:gz') as package:
        for member in package:
            parts = PurePosixPath(member.name).parts
            relative = '/'.join(parts[1:])
            if relative not in wanted:
                continue
            if not member.isfile() or member.size > 2_000_000 or relative in found or '..' in parts:
                raise ValueError('공식 archive 파일/크기/중복 계약')
            with package.extractfile(member) as stream:
                raw = stream.read(2_000_001)
            for root in [source] + ([runtime] if runtime is not None else []):
                path = Path(root) / relative
                if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or path.read_bytes() != raw:
                    raise ValueError('고정 archive와 다른 source/runtime: ' + relative)
            found[relative] = hashlib.sha256(raw).hexdigest().upper()
    if set(found) != wanted:
        raise ValueError('공식 archive의 명시 파일 누락')
    return dict(files=found, source_matches=True, runtime_matches=runtime is not None,
                scope='EXPLICIT_FILES_ONLY_NOT_WHOLE_PACKAGE_OR_DEPENDENCIES')
