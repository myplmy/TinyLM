"""원 계획번호 판정 함수를 유지하고 참조/면제 대상 읽기만 명시 목록으로 제한한다."""
import hashlib
from pathlib import PurePosixPath
import re


def reference_map(original, names, reader):
    refs = {}
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('명시 상대경로만 허용')
        if (path.suffix not in ('.md','.bat','.py','.tsv') or name in original.SKIP_FILES
                or any(part in original.SKIP_DIRS for part in path.parts)
                or any(name.startswith(prefix) for prefix in original.SKIP_REF)):
            continue
        try:
            text = reader(name)
        except (OSError, UnicodeError):
            continue
        for match in original.NUM.finditer(text):
            refs.setdefault('P'+match.group(1),set()).add(name)
    return refs


def registry_subset(text, names):
    """공유 registry의 metadata만 읽는다. 제외한 파일 본문은 열지 않는다."""
    allowed = set(names)
    lines = text.splitlines()
    if not lines:
        return text,dict(included=0,excluded=0)
    kept, included, excluded = [lines[0]],0,0
    for line in lines[1:]:
        cells = line.split(chr(9))
        if len(cells)!=3 or not all(cell.strip() for cell in cells):
            kept.append(line)  # 원 판정기가 잘못된 metadata를 계속 거부한다.
            continue
        plan, name, _ = (c.strip() for c in cells)
        name = name.replace(chr(92),'/')
        if (not re.fullmatch('P'+chr(92)+'d{3}',plan) or name.startswith('/')
                or '..' in PurePosixPath(name).parts or name.startswith('datasets/')):
            kept.append(line)
        elif name in allowed:
            kept.append(line); included+=1
        else:
            excluded+=1
    value=chr(10).join(kept)+chr(10)
    return value,dict(included=included,excluded=excluded,
        source_sha256=hashlib.sha256(text.encode()).hexdigest().upper(),
        subset_sha256=hashlib.sha256(value.encode()).hexdigest().upper())


class RegistryView:
    def __init__(self,text):self.text=text
    def is_file(self):return True
    def read_text(self,**kwargs):return self.text


def install(original, root, names):
    refs=reference_map(original,names,lambda name:(root/name).read_text(encoding='utf-8'))
    raw=original.DIAGNOSTIC_REFS.read_text(encoding='utf-8')
    subset,metadata=registry_subset(raw,names)
    load=original.load_diagnostic_refs
    original.scan_refs=lambda:refs
    original.load_diagnostic_refs=lambda:load(RegistryView(subset))
    return dict(reference_files=len(set().union(*refs.values())) if refs else 0,
        references={name:sorted(files) for name,files in refs.items()},diagnostic_registry=metadata,
        original_number_regex=original.NUM.pattern,
        whole_repository_reference_coverage=False,
        canonical_plan_names_and_index='ORIGINAL_GLOBAL_METADATA_CHECKS_UNCHANGED')
