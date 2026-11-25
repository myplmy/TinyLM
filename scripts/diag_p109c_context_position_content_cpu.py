"""Separate the position of the question from the presence of a 512-token history."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from unittest.mock import patch

from scripts import diag_p109c_context_turn_length_cpu as previous


REF, BASE = previous.REF, previous.BASE
TAG = "p109c_context_position_content_cpu_20261126"
PROFILE = REF.EVIDENCE / f"{TAG}_profile.json"
OUT = REF.EVIDENCE / TAG
END = datetime.fromisoformat("2026-11-26T14:00:00+09:00")
WIDTH = 512

BACKGROUND = {
    "en": (
        "The morning began with a layer of mist settled over the upper meadow. A soft wind bent the "
        "reeds along the edge of a pool where small birds had gathered to drink. Its water was "
        "clear enough to show the different colors of the stones underneath. The trail went around "
        "the shore and entered an open stand of tall pine trees. A fallen branch had caught some "
        "dry needles and leaves, which moved slightly whenever the wind reached that part of the "
        "forest. Farther from the water, the ground rose toward a narrow ridge. The climbing path "
        "was smooth in some places and broken into little shelves of bare rock in others. Over the "
        "ridge, a broad slope was covered by a mixture of pale grass, flowering shrubs, and young "
        "trees. Flowers with small white petals were growing close to an exposed ledge. A patch of "
        "yellow flowers was visible lower down where the ground stayed moist. From the widest part "
        "of the path, the valley opened in both directions and the trees thinned toward the river. "
        "There were long bands of shade on the bank when clouds passed in front of the sun. Beyond "
        "the far bend, water moved across a bed of gravel and made a quiet sound against the stones. "
        "A few large leaves hung over the stream without touching the surface. Small clouds arrived "
        "from the west and seemed to dissolve as they crossed the warmer ground. The dry branches "
        "in the upper canopy reflected the light more brightly than the shaded trunks. Near the "
        "bottom of the slope, shallow pools had gathered between the tree roots. There the sound of "
        "moving water was less distinct, and the sheltered air felt warmer. A line of bushes marked "
        "the place where the trail left the woods and crossed a field of tall grass. Across this "
        "open part, the first hills could be seen again with their shapes softened by the haze. "
        "The clouds that had been scattered in the morning began to gather above the longest ridge. "
        "At the wood's edge, shadows followed the outline of the leaves across the path. A thin "
        "shaft of light fell through a space between two branches onto a patch of moss. The river "
        "was still audible after the water itself was hidden by the trees. Evening light revealed "
        "the uneven surface of the distant hillside and the textures of the grass near the trail. "
        "In the last stretch, the breeze subsided and the lower woods grew quiet."
    ),
    "ko": (
        "아침에 얇은 안개가 언덕 위 초지에 내려앉았습니다. 얕은 물가의 갈대 끝은 약한 바람에 조금씩 "
        "움직였습니다. 작은 새들이 물을 마시려고 늪지 가장자리로 모여들었습니다. 돌의 색을 구별할 수 있을 "
        "정도로 웅덩이의 물이 맑았습니다. 물가를 돌아가는 오솔길은 키 큰 소나무가 드문드문 선 숲으로 "
        "이어졌습니다. 떨어진 가지에 걸린 솔잎과 마른 잎은 바람이 숲속까지 닿을 때마다 흔들렸습니다. 물가에서 "
        "멀어지자 좁은 능선으로 오르는 경사가 나타났습니다. 길 중간에는 걷기 편한 흙과 계단처럼 갈라진 바위가 "
        "번갈아 있었습니다. 능선 너머 넓은 비탈에는 밝은 풀과 꽃 피는 관목과 어린 나무가 골고루 자랐습니다. "
        "볕이 드는 돌턱 곁에서는 작은 흰 꽃잎이 보였습니다. 습기를 머금은 낮은 곳에는 여러 송이의 노란 꽃이 "
        "펴 있었습니다. 길이 가장 넓어지는 곳에서 양쪽 골짜기가 보였고 강가 쪽으로 갈수록 나무가 줄었습니다. "
        "구름이 햇빛을 가리면 강둑에 길쭉한 그늘이 생겼습니다. 굽이 너머에서 물은 자갈 위를 지나 돌에 부딪쳤습니다. "
        "넓은 잎 몇 장이 수면에 닿지 않은 채 개울 위로 드리웠습니다. 서쪽에서 다가온 작은 구름은 따뜻한 땅을 "
        "지나면서 천천히 흩어졌습니다. 위쪽의 마른 가지에는 그늘의 나무줄기보다 빛이 강하게 반사되었습니다. "
        "비탈 아랫부분에는 나무뿌리 사이에 얕은 물이 고였습니다. 그곳에서는 물소리가 희미했고 공기가 따뜻하게 "
        "느껴졌습니다. 키 큰 풀이 많은 들판과 숲 사이를 낮은 덤불이 가르고 있었습니다. 들판에 나오니 처음 봤던 "
        "언덕이 안개 너머로 흐릿하게 보였습니다. 아침에 흩어졌던 구름은 긴 산등성이 뒤에서 다시 모였습니다. 나뭇잎의 "
        "윤곽과 비슷한 그림자가 길 위에 생겼습니다. 가지의 틈으로 들어온 빛이 이끼가 자란 곳에 닿았습니다. 나무에 "
        "가려 강이 보이지 않게 된 뒤에도 물소리는 들렸습니다. 해 질 무렵 멀리 보이는 언덕의 굴곡과 발밑 풀의 "
        "질감이 선명해졌습니다. 마지막 구간에서 바람이 약해지자 낮은 숲이 조용해졌습니다."
    ),
}


def prepare():
    inputs_path, report_path = (previous.OUT / name for name in ("inputs.json", "report.json"))
    inputs, report = map(REF.completed.read_json, (inputs_path, report_path))
    if (report["status"] != "COMPLETE" or report["input_sha256"] != REF.file_sha(inputs_path)
            or inputs["model_sha256"] != REF.CHECKPOINT_SHA256
            or inputs["source_sha256"] != REF.file_sha(Path(previous.__file__))):
        raise ValueError("the prior prompt, model, and generated answers must describe one comparison")
    old = {arm: {row["id"]: row for row in report["rows"] if row["arm"] == arm}
           for arm in ("one_sentence", str(WIDTH))}
    tokenizer = REF.completed.load_tokenizer()
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False).ids
    header = encode("<|im_start|>user\n")
    backgrounds = {language: encode(text + "\n") for language, text in BACKGROUND.items()}
    cases = []
    for case in inputs["cases"]:
        variants, key, lang = case["input_variants"], case["id"], case["language"]
        short, long = variants["one_sentence"], variants[str(WIDTH)]
        suffix = short[len(header):]
        offset = WIDTH - len(short)
        background = backgrounds[lang][-offset:]
        if (not 0 < offset <= len(backgrounds[lang]) or short[:len(header)] != header
                or len(long) != WIDTH or long[:len(header)] != header or long[-len(suffix):] != suffix
                or not old["one_sentence"][key]["usable"] or old[str(WIDTH)][key]["usable"]
                or len(set(background).intersection((2, 3, 4))) or background == long[len(header):-len(suffix)]):
            raise ValueError("the new comparison must preserve the positive short and failed 512-token controls")
        fresh = header + background + suffix
        if len(fresh) != WIDTH or fresh[-len(case["ids"]):] != long[-len(case["ids"]):]:
            raise ValueError("the fresh background changed the fixed question or its position")
        cases.append(dict(case, input_variants={"short_offset": short, "different_background_512": fresh},
                          rope_offset=offset))
    if sorted(case["language"] for case in cases) != ["en"] * 3 + ["ko"] * 3:
        raise ValueError("the fixed long-answer panel must contain three cases in each language")
    profile = dict(cases=cases, checkpoint_sha256=REF.CHECKPOINT_SHA256, max_new=BASE.MAX_NEW,
                   old_inputs_sha256=REF.file_sha(inputs_path), old_report_sha256=REF.file_sha(report_path),
                   source_sha256={Path(filename).name: REF.file_sha(Path(filename)) for filename in
                                  (__file__, previous.__file__, previous.previous.__file__,
                                   previous.previous.bare.__file__)})
    return profile, tokenizer, old


def evaluate(profile, tokenizer, old, cutoff):
    model = previous.previous.streaming.model_for("short_fp32")
    model.cfg.kv_dtype = "fp32"
    cos, sin = model.rope_cos, model.rope_sin
    rows = []
    for index, case in enumerate(profile["cases"]):
        names = tuple(case["input_variants"])
        for arm in (names if index % 2 == 0 else names[::-1]):
            shifted = arm == "short_offset"
            offset = case["rope_offset"] if shifted else 0
            case_input = dict(case, input_variants={arm: case["input_variants"][arm]})
            if len(cos) - offset < len(case_input["input_variants"][arm]) + BASE.MAX_NEW:
                raise ValueError("the original rotary table cannot cover all requested positions")
            with patch.object(model, "rope_cos", cos[offset:]), patch.object(model, "rope_sin", sin[offset:]):
                row, = previous.score(model, tokenizer, [case_input], cutoff)
            archived = old["one_sentence" if shifted else str(WIDTH)][case["id"]]
            same_output = previous.previous.identity(row["metadata"]) == previous.previous.identity(archived["metadata"])
            rows.append(dict(row, rotary_offset=offset, archived_arm=archived["arm"],
                             same_generated_ids_and_stop=same_output))
            print(case["language"], arm, row["usable"], row["final_agrees_and_ended"], flush=True)
    return rows


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("use only CPU 14 and disable CUDA visibility")
    if args.mode == "prepare":
        if args.profile_sha256 or args.stop_by or PROFILE.exists() or OUT.exists():
            parser.error("use a new output profile for a model-free preparation")
        profile, _, _ = prepare()
        REF.native.publish(PROFILE, profile)
        print(PROFILE, REF.file_sha(PROFILE), [case["rope_offset"] for case in profile["cases"]], flush=True)
        return
    if (not args.profile_sha256 or args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= END or OUT.exists()):
        parser.error("use the matching seal, a new record, and an authorized timestamp")
    profile, tokenizer, old = prepare()
    recorded = json.loads(REF.native.manifest_bytes(PROFILE, args.profile_sha256))
    if json.loads(json.dumps(profile)) != recorded:
        raise ValueError("the current inputs differ from the sealed comparison")
    body = REF.checkpoint()
    OUT.mkdir(exist_ok=False)
    rows = evaluate(profile, tokenizer, old, args.stop_by.timestamp())
    if REF.file_sha(body) != profile["checkpoint_sha256"]:
        raise ValueError("the evaluation weights changed during the comparison")
    summary = {}
    for arm in ("short_offset", "different_background_512"):
        group = [row for row in rows if row["arm"] == arm]
        summary[arm] = dict(requests=len(group), usable=sum(row["usable"] for row in group),
                            final_and_stop=sum(row["final_agrees_and_ended"] for row in group),
                            unchanged_output=sum(row["same_generated_ids_and_stop"] for row in group))
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", profile_sha256=args.profile_sha256.upper(),
                                                summary=summary, rows=rows))
    print("P109C_CONTEXT_POSITION_CONTENT", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
