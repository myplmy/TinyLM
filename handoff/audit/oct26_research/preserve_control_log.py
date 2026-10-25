"""One-shot, byte-preserving migration of a historical diagnostic log view."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.check_control_chars import BAD, display_text, first_bad_control

SOURCE = ROOT / "test_result/101_log_20261023_P106B_Stage9aW_scoped_static_audit.txt"
BASE = Path(__file__).resolve().parent
RAW = BASE / "raw" / (SOURCE.name + ".bin")
RECEIPT = BASE / "control_log_view_receipt.json"
EXPECTED = "311FC8EF42DB7D5F2A49047BF7CFB96D501F79F0A59AC4C1C7F3273C7D8A2CE3"
MARKER = b"@RAW_JSON "


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def physical_lines(raw):
    parts = raw.split(bytes((10,)))
    return [x + bytes((10,)) for x in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def render(raw):
    output, converted = [], []
    for number, line in enumerate(physical_lines(raw), 1):
        if first_bad_control(line) is None:
            output.append(line)
        else:
            quoted = display_text(line.decode("utf-8", "strict")).encode("utf-8")
            output.append(MARKER + quoted + bytes((10,)))
            converted.append(number)
    return b"".join(output), converted


def restore(body, converted):
    lines = physical_lines(body)
    for number in converted:
        line = lines[number - 1]
        if not line.startswith(MARKER):
            raise ValueError("missing declared JSON line marker")
        lines[number - 1] = json.loads(line[len(MARKER):].decode("utf-8")).encode("utf-8")
    return b"".join(lines)


def exclusive(path, raw):
    if len(raw) >= 20_000_000:
        raise ValueError("below20MB file bound")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    # The actual historical source is checked only after independent in-memory
    # round-trip cases. Literal escape text must not become a control byte.
    cases = ["plain" + chr(10), "literal " + chr(92) + "u0002" + chr(10),
             "first" + chr(2) + chr(10) + "second" + chr(8) + chr(11) + chr(13) + chr(10)]
    for case in cases:
        raw_case = case.encode("utf-8")
        body, converted = render(raw_case)
        assert restore(body, converted) == raw_case and first_bad_control(body) is None
    if SOURCE.is_symlink() or not SOURCE.is_file() or RECEIPT.exists():
        raise ValueError("explicit original and exclusive new receipt required")
    raw = SOURCE.read_bytes()
    assert sha(raw) == EXPECTED and len(raw) == 32444 and raw.count(bytes((10,))) == 285
    raw.decode("utf-8", "strict")
    findings = [dict(offset=i, byte=f"0x{value:02X}", line=raw[:i].count(bytes((10,))) + 1)
                for i, value in enumerate(raw) if value in BAD]
    assert Counter(x["byte"] for x in findings) == {"0x02": 2, "0x08": 1, "0x0B": 1}
    body, converted = render(raw)
    assert converted == [190, 192, 271] and restore(body, converted) == raw
    header = ["[TINYLM_PRESERVED_LOG_VIEW_V1]",
        "이 파일은 과거 진단 출력의 읽기용 표시본이며 새로운 실행 로그가 아닙니다.",
        "원형 경로: " + RAW.relative_to(ROOT).as_posix(),
        "원형 SHA-256: " + EXPECTED + " / 32444바이트 / LF 285개",
        "변환: 원 LF줄190·192·271만 @RAW_JSON 뒤의 JSON 문자열로 표시합니다. 나머지 줄은 원문 그대로입니다.",
        "복원: 연결 영수증의 변환 줄을 JSON 해독한 뒤 원형 바이트와 대조합니다. 금지4바이트와 과거 실패는 보존됩니다.",
        "연결 영수증: " + RECEIPT.relative_to(ROOT).as_posix(),
        "[ORIGINAL_TEXT_BEGIN]"]
    prefix = (chr(10).join(header) + chr(10)).encode("utf-8")
    rendered = prefix + body
    assert first_bad_control(rendered) is None
    RAW.parent.mkdir(exist_ok=False)
    exclusive(RAW, raw)
    assert RAW.read_bytes() == raw and SOURCE.read_bytes() == raw
    pending = BASE / "control_log_view.pending.txt"
    exclusive(pending, rendered)
    os.chmod(pending, stat.S_IMODE(SOURCE.stat().st_mode))
    if sha(SOURCE.read_bytes()) != EXPECTED:
        raise ValueError("original changed before atomic view installation")
    os.replace(pending, SOURCE)
    stored = SOURCE.read_bytes()
    recovered = restore(stored[len(prefix):], converted)
    assert stored == rendered and recovered == RAW.read_bytes() == raw
    assert sha(recovered) == EXPECTED and first_bad_control(stored) is None
    record = dict(schema="TINYLM_PRESERVED_LOG_VIEW_V1", utc=datetime.now(timezone.utc).isoformat(),
        authority="2026-10-26 user requested static-error remediation, smoke and local commit",
        historical_input_path=SOURCE.relative_to(ROOT).as_posix(), historical_input_sha256=EXPECTED,
        raw=dict(path=RAW.relative_to(ROOT).as_posix(), sha256=sha(raw), bytes=len(raw), lf=285),
        display=dict(path=SOURCE.relative_to(ROOT).as_posix(), sha256=sha(stored), bytes=len(stored),
                     header_bytes=len(prefix), original_lf_line_numbers=converted),
        format="ONLY_DECLARED_CONTROL_BEARING_LF_LINES_USE_AT_RAW_JSON_AND_DISPLAY_TEXT",
        original_control_findings=findings, original_control_count=4,
        reconstruction_bytes_equal=True, original_archive_bytes_equal=True, display_first_bad_control=None,
        historical_failure_preserved=True, historical_static_failure_count=6, historical_exit_code=1,
        old_audit_pins_rewritten=0, scanner_rule_changes=0, raw_is_outside_text_scan=True,
        text_pass_scope="CURRENT_AUTHORED_TEXT_AND_DECLARED_DISPLAY; NOT_CLEAN_HISTORICAL_RAW",
        original_newline_conversion=0, source_replacement="DECLARED_REVERSIBLE_VIEW_WITH_VERIFIED_ORIGINAL_ARCHIVE",
        model_calls=0, gpu_calls=0)
    exclusive(RECEIPT, (json.dumps(record, ensure_ascii=False, indent=2) + chr(10)).encode("utf-8"))
    print(json.dumps(dict(receipt=RECEIPT.relative_to(ROOT).as_posix(), raw_sha256=EXPECTED,
        original_controls=4, transformed_lines=converted, roundtrip_exact=True,
        display_sha256=record["display"]["sha256"], scanner_rule_changes=0), ensure_ascii=False))


if __name__ == "__main__":
    main()
