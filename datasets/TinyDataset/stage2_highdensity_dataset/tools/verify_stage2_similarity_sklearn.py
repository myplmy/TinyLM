#!/usr/bin/env python3
"""Independent scikit-learn check of an internal Stage2 train char similarity maximum."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "stage1_highdensity_dataset" / "tools"
sys.path.insert(0, str(COMMON))

from stage2_10_corpus_common import (  # noqa: E402
    existing_source_path,
    load_ledger,
    read_source,
    select_reservations,
)


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", type=int, required=True)
    parser.add_argument("--block-size", type=int, default=256)
    args = parser.parse_args()

    ledger = load_ledger(
        ROOT
        / "stage1_highdensity_dataset"
        / "TinyLM_Stage2_Stage10_Concept_Family_Reservation.json"
    )
    reservations = select_reservations(
        ledger, stages={2}, areas={args.area}, split="train"
    )
    texts: list[str] = []
    owners: list[str] = []
    for reservation in reservations:
        source = existing_source_path(ROOT, reservation)
        if source is None:
            raise FileNotFoundError(reservation.reservation_id)
        for row in read_source(source, split="train"):
            texts.append(row.text)
            owners.append(f"{reservation.reservation_id}:{row.line_number}")

    matrix = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        preprocessor=normalize,
        lowercase=False,
        norm="l2",
        smooth_idf=True,
        sublinear_tf=False,
        dtype=np.float64,
    ).fit_transform(texts)

    maximum = 0.0
    maximum_pair: tuple[int, int] | None = None
    threshold_pairs = 0
    for start in range(0, matrix.shape[0], args.block_size):
        stop = min(start + args.block_size, matrix.shape[0])
        scores = (matrix[start:stop] @ matrix.T).tocsr()
        for local_row in range(stop - start):
            query = start + local_row
            row_start = scores.indptr[local_row]
            row_stop = scores.indptr[local_row + 1]
            columns = scores.indices[row_start:row_stop]
            values = scores.data[row_start:row_stop]
            keep = columns > query
            if not np.any(keep):
                continue
            kept_columns = columns[keep]
            kept_values = values[keep]
            threshold_pairs += int(np.count_nonzero(kept_values >= 0.72))
            index = int(np.argmax(kept_values))
            candidate = float(kept_values[index])
            if candidate > maximum:
                maximum = candidate
                maximum_pair = (query, int(kept_columns[index]))

    result = {
        "area": args.area,
        "records": len(texts),
        "char_3_5_tfidf_pairs_ge_0_72": threshold_pairs,
        "char_3_5_tfidf_max": maximum,
        "pair": None,
    }
    if maximum_pair is not None:
        left, right = maximum_pair
        result["pair"] = {
            "query_owner": owners[left],
            "reference_owner": owners[right],
            "query_text": texts[left],
            "reference_text": texts[right],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
