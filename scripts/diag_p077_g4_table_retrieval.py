"""Compare automatic two-table selection with recent and known-evidence controls."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
from inspect import getsource
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_evidence_window as window


TAG = "p077_g4_table_retrieval_cpu_v1_20261121"
OUT = window.OUT.with_name(TAG)
native, mapped, trial, full = window.native, window.mapped, window.trial, window.full
ARMS = ("automatic", "recent", "oracle")
TITLES = {
    "ko": (("항만지원반", "선적 현장 담당자"), ("품질검사반", "결함을 점검하는 담당자")),
    "en": (("Dock Services", "the staff who load ships"), ("Inspection Office", "the staff who check for defects")),
}


def select_request(raw, mode, oracle, tail_chars):
    import re

    text = raw.decode("utf-8")
    lead, rest = text.split("<SECTION>\n", 1)
    first, rest = rest.split("\n<BACKGROUND>\n", 1)
    background, rest = rest.split("\n<SECTION>\n", 1)
    second, ask = rest.split("\n<REQUEST>\n", 1)
    hint, question = ask.split("\n", 1)
    titles, tables = zip(*(section.split("\n", 1) for section in (first, second)), strict=True)
    # Normalize titles without interpreting any of the table values.
    compact_hint = "".join(re.findall(r"\w+", hint.casefold()))
    compact_titles = ["".join(re.findall(r"\w+", title.casefold())) for title in titles]
    scores = [int(title in compact_hint) for title in compact_titles]
    if mode == "oracle":
        chosen = oracle
    elif mode == "automatic" and sum(scores) == 1:
        chosen = scores.index(1)
    else:
        chosen = 1
    rendered = lead + background[-tail_chars:] + "\n" + tables[chosen] + question
    return rendered.encode("utf-8"), chosen


def raw_panels(tok, table_rows, roots):
    output = []
    for language, root in roots.items():
        row = table_rows[root]
        pieces = [native.wide.parts(tok, row, side) for side in (0,1)]
        lead = tok.decode(pieces[0][0], skip_special_tokens=False)
        tables = [tok.decode(part[1], skip_special_tokens=False) for part in pieces]
        head0 = lead + "<SECTION>\n" + TITLES[language][0][0] + "\n" + tables[0] + "\n<BACKGROUND>\n"
        head1 = "\n<SECTION>\n" + TITLES[language][1][0] + "\n" + tables[1] + "\n<REQUEST>\n"
        fillers = native.training.controls.diverse_filler(tok, language, 3900)
        filler = tok.decode(fillers, skip_special_tokens=False)
        if "\ufffd" in filler:
            for shave in range(1, 12):
                filler = tok.decode(fillers[:-shave], skip_special_tokens=False)
                if "\ufffd" not in filler:
                    break
            else:
                raise ValueError("the filler must remain valid UTF-8")
        for target, question_parts in enumerate(pieces):
            q = tok.decode(question_parts[2], skip_special_tokens=False)
            for style, title in enumerate(TITLES[language][target]):
                question = f"{title} 기록을 사용하세요." if language == "ko" else f"Use the record for {title}."
                text = head0 + filler + head1 + question + "\n" + q
                raw = text.encode("utf-8")
                count = len(tok.encode(text, add_special_tokens=False).ids)
                if not 4000 <= count <= 4096:
                    raise ValueError(f"expected a new long input near the 4,096 boundary, found {count}")
                offsets = tok.encode(filler, add_special_tokens=False).offsets
                tail = len(filler) - offsets[-1940][0]
                checked = {}
                for arm in ARMS:
                    oracle = target if arm == "oracle" else None
                    visible, selected = select_request(raw, arm, oracle, tail)
                    ids = tok.encode(visible.decode("utf-8"), add_special_tokens=False).ids
                    if len(ids) > 2048 - native.GEN + 1 or not visible.startswith(lead.encode("utf-8")):
                        raise ValueError("the selected view violated the bounded input contract")
                    checked[arm] = dict(ids=ids, selected=selected)
                output.append(dict(language=language, target=target, phrasing=("explicit", "reworded")[style],
                                   raw=text, input_tokens=count, tail_chars=tail, gold=row["gold"][target],
                                   choices=checked))
    if len(output) != 8 or len({row["raw"] for row in output}) != 8:
        raise ValueError("the two languages and two distinct table targets must all be present")
    return output


def prepare():
    long_plan, (tok, long_rows, model, decoder, encoder) = full.prepare()
    source_result = window.OUT / "report.json"
    prior = trial.read_json(source_result)
    if prior["plan"]["proof"] != long_plan or len(prior["results"]) != 8:
        raise ValueError("requires the short known-evidence comparison")
    _, (_, _, tables, _, _) = native.prepare(rope=True)
    roots = {row["language"]:row["root"] for row in long_rows}
    rows = raw_panels(tok, {row["root"]:row for row in tables}, roots)
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), proof=long_plan,
                prior=trial.file_sha(source_result), prompts=full.native.training.data.authored.digest(rows), count=len(rows))
    return plan, (tok, rows, model, decoder, encoder)


def render_wrapper(path, base, prompt, arm):
    source = base.read_bytes()
    marker = b"def snapshot():"
    source = native.port.replace_once(source, marker, getsource(select_request).encode("utf-8") + b"\n\n" + marker)
    line = b'    assert 0 < len(raw) <= 65536, "invalid UTF-8 request length"\n'
    oracle = prompt["target"] if arm == "oracle" else None
    addition = f'    raw, _ = select_request(raw, {arm!r}, {oracle!r}, {prompt["tail_chars"]})\n'.encode("ascii")
    path.write_bytes(native.port.replace_once(source, line, line + addition))
    return path


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 360):
        raise ValueError("requires a new bounded CPU experiment")
    checked, (tok, prompts, model, decoder, encoder) = prepare()
    if checked != plan:
        raise ValueError("the sealed source changed")
    cpu = min(set(model["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    with patch.object(window, "OUT", OUT):
        binary = window.get_binary(plan)
    source, parts = native.text_codec(OUT)
    mapped.request.render_decoder(source, decoder)
    mapped_source = OUT / "mapped_request.py"
    mapped.render_input(mapped_source, source, encoder)
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            state = plan["proof"]["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack, state, model)
        assets = [image]
        for index, part in enumerate(parts):
            fd = native.base.memfile(f"p077-table-retrieval-{index}")
            stack.callback(os.close, fd)
            native.bounded.text.store(fd, part)
            full.seal(fd)
            assets.append(fd)
        results = []
        for i, prompt in enumerate(prompts):
            known = {}
            for arm in ARMS:
                if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 75:
                    raise TimeoutError("the retrieval panel reached its boundary")
                choice = prompt["choices"][arm]
                ids = choice["ids"]
                key = tuple(ids)
                if key not in known:
                    wrapper = render_wrapper(OUT / f"case_{i}_{arm}.py", mapped_source, prompt, arm)
                    path = OUT / f"case_{i}_{arm}.json"
                    expected = dict(encoding=dict(ids=ids), native=dict(model_bytes=os.fstat(image).st_size,
                                    kv_bytes=full.cache_size(len(ids)+native.GEN-1, full.ARMS["k4v3"])))
                    stats = native.port.request(binary, assets, prompt["raw"].encode("utf-8"),
                                                path, expected, wrapper=wrapper)
                    raw = trial.read_json(path)
                    answer = native.decoded(tok, raw["native"], prompt["gold"], plan["proof"]["stop"])
                    known[key] = (arm, answer, dict(peak_rss=stats["peak_rss"], seconds=stats["seconds"],
                                                    first_token=raw["native"]["seconds"][0]))
                origin, answer, measurement = known[key]
                row = dict(case=i, arm=arm, reused_from=origin if origin != arm else None,
                           language=prompt["language"], phrasing=prompt["phrasing"],
                           input_tokens=prompt["input_tokens"], visible_tokens=len(ids), selected=choice["selected"],
                           correct_source=choice["selected"] == prompt["target"],
                           gold=prompt["gold"], **answer, **(measurement if origin == arm else {}))
                results.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    trial.publish(OUT/"report.json", dict(plan=plan, cpu=cpu, results=results))


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
        parser.error("requires sealed exact inputs and deadline")
    run(plan, args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
