"""Count exact SODA content matches in the already cached English Aya release."""

from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
from time import monotonic
import unicodedata

import pyarrow.compute as pc
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "handoff/audit/research_20261118_01a1e647"
PREVIOUS = AUDIT / "EXISTING_ENGLISH_FAMILY_METADATA_v3.json"
OUTPUT = AUDIT / "SODA_AYA_CONTENT_GROUPS_v1.json"
INPUT = ROOT / "HF/sft_sources/p106b_aya_collection_en_a3af2fde"
MANIFEST = INPUT / "source_manifest.json"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
REVISION = "a3af2fde4b4cb5b2775830b11244a1a20b5f004f"
FAMILIES = ("SODA-inst", "SODA-inst (T)")
VARIANTS = ("plain_1", "plain_2", "plain_3", "plain_4", "translated_1")
COLUMNS = ("id", "dataset_name", "template_id", "language", "split", "inputs", "targets")
SUMMARY_QUESTION = "\n\n\nWhat do you think the narrative of the conversation above is?"
STORY_PREFIX = "I have the following short story premise:\n"
STORY_SUFFIX = "\n\nNow, can you extend that into a short dialogue script?"
DIALOGUE_PREFIX = "Sure, here is one possible dialogue:\\n\\n "
GIST_PREFIX = "This is the gist of the dialogue - "
TOPIC_PREFIX = "Write a short paragraph of narrative given the following topic:\n\n"
PARAGRAPH_PREFIX = "Sure, here is a short paragraph:\n"


def signature(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def checksum(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def extract(name, inputs, targets):
    if not isinstance(inputs, str) or not isinstance(targets, str):
        return "", "", ""
    story = dialogue = topic = ""
    if name == "plain_1" and inputs.endswith(SUMMARY_QUESTION):
        story = targets
        dialogue = inputs.removesuffix(SUMMARY_QUESTION)
    elif name == "plain_2" and inputs.startswith(STORY_PREFIX) and inputs.endswith(STORY_SUFFIX):
        story = inputs.removeprefix(STORY_PREFIX).removesuffix(STORY_SUFFIX)
        if targets.startswith(DIALOGUE_PREFIX):
            dialogue = targets.removeprefix(DIALOGUE_PREFIX).replace("\\n", "\n")
    elif name == "plain_3" and targets.startswith(GIST_PREFIX):
        story = targets.removeprefix(GIST_PREFIX)
    elif name in ("plain_4", "translated_1") and inputs.startswith(TOPIC_PREFIX) and targets.startswith(PARAGRAPH_PREFIX):
        story = targets.removeprefix(PARAGRAPH_PREFIX)
        topic = inputs.removeprefix(TOPIC_PREFIX)
    return tuple(unicodedata.normalize("NFC", item.strip()) for item in (story, dialogue, topic))


def compound_key(story, detail):
    first = story.encode("utf-8")
    return sha256(len(first).to_bytes(8, "little") + first + detail.encode("utf-8")).digest()


class ExactGroups:
    def __init__(self, variants):
        self.variants = variants
        self.groups = {}
        self.rows = Counter()
        self.witnesses = {}

    def add(self, key, variant, row_id):
        self.rows[variant] += 1
        bit = 1 << self.variants.index(variant)
        first_id, previous = divmod(self.groups.get(key, 0), 32)
        if previous & bit:
            return
        if not previous:
            first_id = row_id
        elif previous.bit_count() == 1:
            earlier = self.variants[previous.bit_length() - 1]
            pair = tuple(sorted((earlier, variant)))
            self.witnesses.setdefault(pair, dict(key_sha256=key.hex().upper(),
                row_ids={earlier: first_id, variant: row_id}))
        self.groups[key] = first_id * 32 + (previous | bit)

    def report(self):
        masks = Counter(value % 32 for value in self.groups.values())
        sizes = {name: sum(count for mask, count in masks.items() if mask & (1 << idx))
                 for idx, name in enumerate(self.variants)}
        assert 0 not in masks and all(self.rows[name] >= count for name, count in sizes.items())
        pairs = {}
        for (i, left), (j, right) in combinations(enumerate(self.variants), 2):
            both = (1 << i) | (1 << j)
            pairs[f"{left}__{right}"] = sum(count for mask, count in masks.items() if mask & both == both)
        return dict(input_rows=dict(self.rows), unique_groups=len(self.groups), by_variant=sizes,
            within_variant_extra_rows={name: self.rows[name] - count for name, count in sizes.items()},
            groups_with_multiple_variants=sum(count for mask, count in masks.items() if mask.bit_count() > 1),
            pair_group_counts=pairs, witnesses=list(self.witnesses.values()))


def read_sources():
    previous = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    known = {r["path"]: r for r in previous["files"]}
    expected = [f"english/train-{i:05}-of-00007.parquet" for i in range(7)]
    sources = manifest["sources"]
    if (previous["manifest_sha256"].upper() != checksum(MANIFEST)
            or [r["remote_file"] for r in sources] != expected
            or len(known) != len(expected)):
        raise ValueError("Exact prior seven-file English source manifest required")
    paths = []
    for item, basename in zip(sources, expected, strict=True):
        path = INPUT / basename
        earlier = known[item["path"]]
        if (path.is_symlink() or path.resolve() != path or path.relative_to(ROOT).as_posix() != item["path"]
                or item["revision"] != REVISION or item["sha256"] != earlier["declared_full_sha256"]
                or signature(path) != earlier["file_identity"]):
            raise ValueError(f"Source ownership or file identity changed: {basename}")
        paths.append((path, earlier))
    return paths


def candidate_groups(parquet):
    ordinal = 0
    for index in range(parquet.metadata.num_row_groups):
        group = parquet.metadata.row_group(index)
        columns = {group.column(i).path_in_schema: group.column(i) for i in range(group.num_columns)}
        stat = columns["dataset_name"].statistics
        if stat is None or not stat.has_min_max or any(stat.min <= label <= stat.max for label in FAMILIES):
            yield index, ordinal, group.num_rows, sum(columns[name].total_uncompressed_size for name in COLUMNS)
        ordinal += group.num_rows


def exact_dialogue(value):
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) < 2 or any(not line.partition(": ")[1] for line in lines):
        return ""
    return "\n".join(lines)


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUTPUT.exists():
        raise ValueError("Use CPU-only mode and a fresh audit receipt")
    started = monotonic()
    start = datetime.now().astimezone()
    if END - start < timedelta(seconds=240):
        raise TimeoutError("User 177 window")
    narrative = ExactGroups(VARIANTS)
    topic_story = ExactGroups(("plain_4", "translated_1"))
    dialogue_story = ExactGroups(("plain_1", "plain_2"))
    observed, rejected, offset_disagreements, split_values = Counter(), Counter(), Counter(), Counter()
    file_results = []
    global_row_offset = 0
    for path, prior in read_sources():
        parquet = pq.ParquetFile(path)
        if (parquet.schema_arrow.names != prior["schema_names"]
                or parquet.metadata.num_rows != prior["raw_metadata_rows"]):
            raise ValueError("Parquet schema or extent changed")
        groups, physical_rows, matched, projected = 0, 0, 0, 0
        for index, ordinal, row_count, reserve in candidate_groups(parquet):
            if monotonic() - started > 200 or datetime.now(END.tzinfo) >= END:
                raise TimeoutError("Scoped Aya column audit time limit")
            table = parquet.read_row_group(index, columns=COLUMNS, use_threads=False)
            indexed = table.append_column("source_row", pc.indices_nonzero(pc.is_valid(table["id"])))
            if table.num_rows != row_count or indexed["source_row"].length() != row_count:
                raise ValueError("Source row count or ID presence differs")
            labels = pc.or_(pc.equal(table["dataset_name"], FAMILIES[0]),
                            pc.equal(table["dataset_name"], FAMILIES[1]))
            groups += 1
            physical_rows += row_count
            projected += reserve
            for row in indexed.filter(labels).to_pylist():
                matched += 1
                if row["language"] != "eng" or type(row["id"]) is not int:
                    raise ValueError("Exact English source IDs required")
                kind = "plain" if row["dataset_name"] == FAMILIES[0] else "translated"
                variant = f"{kind}_{row['template_id']}"
                observed[variant] += 1
                split_values[row["split"]] += 1
                if row["id"] != global_row_offset + ordinal + row["source_row"] + 1:
                    offset_disagreements[variant] += 1
                story, dialogue, topic = extract(variant, row["inputs"], row["targets"])
                if not story:
                    rejected[variant] += 1
                    continue
                narrative.add(sha256(story.encode("utf-8")).digest(), variant, row["id"])
                if topic:
                    topic_story.add(compound_key(story, topic), variant, row["id"])
                dialogue = exact_dialogue(dialogue)
                if dialogue:
                    dialogue_story.add(compound_key(story, dialogue), variant, row["id"])
        if signature(path) != prior["file_identity"]:
            raise ValueError("Source file changed during the audit")
        file_results.append(dict(path=path.relative_to(ROOT).as_posix(), file_identity=prior["file_identity"],
                                 manifest_sha256=prior["declared_full_sha256"], groups=groups,
                                 physical_rows=physical_rows, soda_rows=matched, projected_uncompressed_bytes=projected))
        global_row_offset += parquet.metadata.num_rows
        print("SODA_AYA_SOURCE", path.name, groups, matched, flush=True)
    assert sum(observed.values()) == sum(narrative.rows.values()) + sum(rejected.values())
    result = dict(schema="P106B_SODA_AYA_EXACT_CONTENT_GROUPS_V1", revision=REVISION,
                  manifest_sha256=checksum(MANIFEST), source_metadata_sha256=checksum(PREVIOUS),
                  scope="LOCAL_ENGLISH_Aya_SOURCE_LABELS_ONLY", files=file_results, source_split_rows=dict(split_values),
                  observed_rows=dict(observed), wrapper_refusals=dict(rejected),
                  row_ordinal_disagreements=dict(offset_disagreements), narrative=narrative.report(),
                  narrative_and_topic=topic_story.report(), narrative_and_dialogue=dialogue_story.report(),
                  original_ai2_rows_read=0, original_split_joined=0, admitted_rows=0, teacher_calls=0,
                  started=start.isoformat(), finished=datetime.now().astimezone().isoformat(),
                  seconds=monotonic()-started)
    with OUTPUT.open("x", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")
    print("SODA_AYA_GROUPS", dict(observed), dict(rejected), result["narrative"]["unique_groups"],
          result["narrative"]["groups_with_multiple_variants"], flush=True)


if __name__ == "__main__":
    main()
