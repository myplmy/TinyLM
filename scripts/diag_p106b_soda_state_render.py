"""Render and recount format-only SODA turns from reviewed archived first answers."""

import hashlib
import json
import os
from pathlib import Path

from scripts import diag_p106b_soda_exact_teacher as exact
from scripts.p106b_soda_candidate_wire import student_candidate


SOURCE = exact.MTP_OUT
OUT = SOURCE.with_name("p106b_soda_state_render_cpu_v1_20261120")
REVIEWED = (45, 112, 180, 247)
ACK = {"en": "Understood. I will use that JSON format.", "ko": "알겠습니다. 앞으로 그 JSON 형식으로 답하겠습니다."}


def records(kind):
    path = SOURCE / f"{kind}_shards_manifest.json"
    manifest = exact.previous.fixture.load(path)
    exact.previous.verify(SOURCE, manifest)
    return [json.loads(line) for shard in manifest["shards"]
            for line in (SOURCE / shard["path"]).read_bytes().splitlines()]


def text(row, index):
    return row["messages"][index]["content"][0]["text"]


def answer_json(answer):
    return json.dumps({"answer": answer}, ensure_ascii=False, separators=(",", ":"))


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("the archived-state render is CPU only")
    profile = exact.previous.fixture.load(SOURCE / "profile.json")
    report = exact.previous.fixture.load(SOURCE / "report.json")
    if (not profile["mtp"] or not report["complete"]
            or exact.io.digest(SOURCE / "profile.json") != report["profile_sha256"]):
        raise ValueError("the reviewed first-answer receipt differs")
    rows = {row["meta"]["source_raw_sha256"]: row for row in records("candidate")}
    raw = records("raw")
    source = exact.open_source()
    tokenizer = exact.previous.fixture.tokenize()
    output = []
    proofs = []
    for index in REVIEWED:
        case = next(case for case in profile["cases"] if case["row"] == index)
        group = next(group for group in report["groups"] if group["row"] == index)
        root = source.read_next(case["cursor"])
        archived = rows[case["raw_sha256"]]
        ref = archived["meta"]["teacher_reasoning_refs"][0]
        attempt = raw[ref["raw_row_1based"] - 1]
        first = attempt["parsed"]["parsed_content"]
        if (root.raw_sha256 != case["raw_sha256"] or case["task"] != "multiturn"
                or attempt["source_raw_sha256"] != root.raw_sha256 or attempt["turn"] != 1
                or first["assistant_text"] != text(archived, 1)):
            raise ValueError("archived first answer and source binding differ")
        language = case["language"]
        turns = [
            {key: first[key] for key in ("user_text", "assistant_text")},
            dict(user_text="format change", assistant_text=answer_json(ACK[language])),
            dict(user_text="first question", assistant_text=answer_json(first["assistant_text"])),
        ]
        identity = f"{archived['meta']['student_wire_sha256']}|SODA_FORMAT_ONLY_RENDER_V1"
        generation = "soda_render_" + hashlib.sha256(identity.encode("ascii")).hexdigest()
        candidate = student_candidate(root.prepared, turns, language, "multiturn", tokenizer=tokenizer,
                                      teacher_model_sha256=profile["model_sha256"], generation_id=generation)
        if (text(candidate, 0) != text(archived, 0) or text(candidate, 1) != text(archived, 1)
                or json.loads(text(candidate, 3)) != {"answer": ACK[language]}
                or json.loads(text(candidate, 5)) != {"answer": text(archived, 1)}):
            raise ValueError("format replay changed archived source, question or answer")
        candidate["meta"].update(turn_output_origins=["REVIEWED_EXISTING_TEACHER", "FIXED_ACK", "EXACT_JSON_WRAP"],
                                 source_raw_sha256=root.raw_sha256, archived_generation_id=archived["meta"]["generation_id"],
                                 archived_first_teacher_ref=ref)
        output.append(candidate)
        bought = [row for row in raw if row["source_raw_sha256"] == root.raw_sha256 and row["task"] == "multiturn"]
        proofs.append(dict(row=index, original_teacher_calls=group["attempts"],
                           first_turn_calls=sum(row["turn"] == 1 for row in bought),
                           student_input_tokens=candidate["meta"]["actual_x_tokens"],
                           assistant_target_counts=candidate["meta"]["assistant_turn_target_counts"]))
    OUT.mkdir(exist_ok=False)
    writer = exact.previous.ShardWriter(OUT, "candidate")
    for candidate in output:
        writer.append(candidate)
    exact.previous.verify(OUT, writer.close(lineage=dict(scope="FORMAT_ONLY_RESEARCH", corpus_admitted=False)))
    exact.io.write(OUT / "report.json", dict(complete=True, rows=proofs, actual_teacher_calls=0,
                   admitted_rows=0, student_updates=0, archived_profile_sha256=report["profile_sha256"],
                   source_sha256=exact.io.digest(Path(__file__))))
    print("SODA_FORMAT_ONLY_RENDER", len(proofs), flush=True)


if __name__ == "__main__":
    main()
