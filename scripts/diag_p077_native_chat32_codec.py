"""Test installed Linux ICU and the existing compact mmap BPE on ChatML 32K."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import struct
import subprocess

from scripts import diag_p077_g4_context4096 as reference


TAG = "p077_native_chat32_codec_cpu_v1_20261121"
OUT = reference.OUT.with_name(TAG)
trial, mapped = reference.trial, reference.mapped
SCRIPTS = trial.ROOT / "scripts"
ASSET = mapped.compact.OUT / "chat32_input.bin"
WINDOWS_CORE = SCRIPTS / "p109_win64_qbpe.hpp"
SCANNER = SCRIPTS / "p077_linux_icu_scan.hpp"
DRIVER = SCRIPTS / "p077_native_qbpe_fixtures.cpp"
ICU = Path("/lib/x86_64-linux-gnu/libicui18n.so.74")
HEADER = struct.Struct("<8s5I")
INT = struct.Struct("<I")
BYTE_LEVEL = r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"


def contract():
    with ASSET.open("rb") as stream:
        magic, count, ordinary, rules, preprocessor, pieces = HEADER.unpack(stream.read(HEADER.size))
        position = HEADER.size + (count + 1) * 4 + rules * 16
        stream.seek(position)
        spec = json.loads(stream.read(preprocessor))
    if (magic != b"TLQBPE1\x00" or (count, ordinary) != (32768, 32768)
            or ASSET.stat().st_size != position + preprocessor + pieces
            or spec["normalizer"] is not None
            or spec["pre_tokenizer"] != dict(type="ByteLevel", add_prefix_space=False, trim_offsets=True, use_regex=True)
            or spec["decoder"]["type"] != "ByteLevel"):
        raise ValueError("unknown compact ChatML vocabulary contract")
    added = sorted(spec["added_tokens"], key=lambda row: row["id"])
    if (not added or len({row["id"] for row in added}) != len(added)
            or any(not row["content"].isascii() or not row["special"] or not 0 <= row["id"] < count
                   or any(row[name] for name in ("lstrip","rstrip","normalized","single_word")) for row in added)):
        raise ValueError("unsupported ChatML reserved tokens")
    literal = set(range(33,127)) | set(range(161,173)) | set(range(174,256))
    rest = iter(range(256,512))
    points = [byte if byte in literal else next(rest) for byte in range(256)]
    inverse = [-1] * (max(points) + 1)
    for byte, point in enumerate(points):
        inverse[point] = byte
    ids = [spec["model"]["vocab"][chr(point)] for point in points]
    if len(set(ids)) != 256 or any(not 0 <= token < count for token in ids):
        raise ValueError("unexpected byte-level IDs")
    constants = {"Assigned":count, "Ordinary":ordinary, "Rules":rules, "PreprocessorBytes":preprocessor,
                 "PieceBytes":pieces}
    lines = [f"inline constexpr uint32_t {name} = {value};" for name, value in constants.items()]
    lines.append(f"inline constexpr char16_t RegexPattern[] = u{json.dumps(BYTE_LEVEL)};")
    for name, proto, entries in (("ByteToId", "uint32_t", ids), ("PointToByte", "int16_t", inverse)):
        lines.append(f"inline constexpr std::array<{proto}, {len(entries)}> {name} = {{")
        for i in range(0,len(entries),16):
            lines.append("    " + ", ".join(str(n) for n in entries[i:i+16]) + ",")
        lines.append("};")
    lines.append("inline constexpr AddedToken Added[] = {")
    lines.extend(f'    {{{json.dumps(row["content"])}, {row["id"]}, true}},' for row in added)
    lines.append("};")
    return "\n".join(lines), [row["content"] for row in added]


def generated(constants):
    original = WINDOWS_CORE.read_text(encoding="utf-8")
    core = original[original.index("class Archive {"):]
    marker = "if (skip_special && id >= Ordinary && Added[id - Ordinary].special) continue;"
    if core.count(marker) != 1:
        raise ValueError("the mmap decoder archive no longer matches the reuse contract")
    core = core.replace(marker, "if (skip_special && special_id(id)) continue;")
    return f'''#pragma once
#include "p077_linux_icu_scan.hpp"
#include <array>
#include <cstring>
#include <functional>
#include <queue>
#include <tuple>
#include <vector>

namespace win_qbpe {{
struct AddedToken {{
    std::string_view text;
    uint32_t id;
    bool special;
}};
{constants}

inline void check(bool ok, const char* message) {{ p077_icu::require(ok, message); }}
inline bool special_id(uint32_t id) {{
    for (const auto& token : Added) if (token.id == id) return token.special;
    return false;
}}
class Scaffold : public p077_icu::Scanner {{
public:
    Scaffold() : p077_icu::Scanner(RegexPattern) {{}}
}};

{core}'''


def fixtures(tokenizer, texts, markers):
    fragments = (" 토큰","한\u1100\u1161","#127","é","e\u0301","😺","good!"," \r\n","\t","a  b","가","  ","b’c")
    rng = Random(302901)
    inputs = [("real", text) for text in texts]
    inputs.extend(("mixed", "".join(rng.choices(fragments,k=(i%15)+1))) for i in range(512))
    inputs.extend(("special", f"{left}{marker}{right}") for marker in markers
                  for left,right in (("",""),("abc","끝"),(" \n","\t  ")))
    sequences = [[rng.randrange(32768) for _ in range(i%8+1)] for i in range(1024)]
    inputs.extend(("decoded", item) for item in tokenizer.decode_batch(sequences, skip_special_tokens=False))
    for scalar in (0x85, 0x2007, 0x2028, 0x202F, 0x11380, 0x1e5d0, 0x1f1f0):
        symbol = chr(scalar)
        inputs.extend(("unicode_boundary", form.format(symbol)) for form in ("a{}b", " 가{} 나", "{} 123", "foo{}🙂"))
    inputs.append(("empty", ""))
    return inputs


def prepare():
    long_plan, (tok, long_rows, _, _, _) = reference.prepare()
    if trial.file_sha(ASSET) != long_plan["native"]["input_sha256"] or not ICU.is_file():
        raise ValueError("requires the validated ChatML input and current installed ICU")
    constants, markers = contract()
    _, (_, _, short, _, _, _, _) = mapped.prepare()
    samples = fixtures(tok, [r["text"] for r in (*short,*long_rows)], markers)
    source = generated(constants).encode("utf-8")
    plan = dict(tag=TAG, sources={p.name:trial.file_sha(p) for p in (Path(__file__),SCANNER,DRIVER,WINDOWS_CORE)},
                packed=trial.file_sha(ASSET), icu=trial.file_sha(ICU), generate=sha256(source).hexdigest(),
                fixtures=reference.native.training.data.authored.digest(samples), count=len(samples))
    return plan, (tok, source, samples)


def run(plan, deadline):
    if OUT.exists() or not deadline.tzinfo or deadline > mapped.compact.AUTHORIZATION_END:
        raise ValueError("requires a new authorized CPU tokenizer run")
    if (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 150:
        raise TimeoutError("too little time for the tokenizer comparison")
    current, (tok, source, samples) = prepare()
    if current != plan:
        raise ValueError("the native tokenizer artifacts changed")
    OUT.mkdir()
    (OUT / "p077_qbpe_generated.hpp").write_bytes(source)
    binary = OUT / "codec_fixture"
    cmd = ["/usr/bin/g++","-std=c++17","-O3","-Wall","-Wextra","-Werror","-I",str(OUT),"-I",str(SCRIPTS),
           str(DRIVER),"-ldl","-o",str(binary)]
    subprocess.run(cmd, check=True, timeout=60)
    raw = []
    for _,sample in samples:
        payload = sample.encode("utf-8")
        raw.extend((INT.pack(len(payload)), payload))
    direct = subprocess.check_output([binary,ASSET], input=b"".join(raw), timeout=60)
    mismatches = []
    expected_stream = sha256()
    count = 0
    seen = 0
    for kind,sample in samples:
        expected = tok.encode(sample, add_special_tokens=False).ids
        decoded = tok.decode(expected, skip_special_tokens=False).encode("utf-8")
        expected_stream.update(struct.pack(f"<{len(expected)+1}I",len(expected),*expected))
        expected_stream.update(INT.pack(len(decoded)) + decoded)
        found, = INT.unpack_from(direct, seen)
        ids = struct.unpack_from(f"<{found}I", direct, seen + INT.size)
        seen += (found + 1) * INT.size
        size, = INT.unpack_from(direct, seen)
        seen += INT.size
        text = direct[seen:seen+size]
        seen += size
        if ids != tuple(expected) or text != decoded:
            if len(mismatches) < 20:
                mismatches.append(dict(kind=kind, sample=sample[:100], expected=expected[:24], actual=list(ids[:24]),
                                       text_equal=text == decoded))
            count += 1
    if seen != len(direct):
        raise ValueError("partial or excess native tokenizer results")
    trial.publish(OUT/"report.json", dict(plan=plan, command=cmd, binary_sha256=trial.file_sha(binary),
                                          cases=len(samples), mismatch_count=count, mismatches=mismatches,
                                          native_sha256=sha256(direct).hexdigest(),
                                          expected_sha256=expected_stream.hexdigest()))
    print(json.dumps(dict(cases=len(samples), mismatches=count), ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires sealed Unicode cases and an authorized cutoff")
    run(plan, args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
