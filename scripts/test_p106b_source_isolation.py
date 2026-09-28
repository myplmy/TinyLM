#!/usr/bin/env python3
"""Public P106B job export must not read or emit protected dictionary data."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_p106b_multisource_deck as deck
from scripts.p106b_shards import verify


def main() -> None:
    aya = deck._job(source_family="aya_dataset", source_repo="CohereLabs/aya_dataset",
                    source_revision="r1", source_sha256="A" * 64, source_id="aya-1",
                    source_language="en", target_language="ko", split="train",
                    license_name="Apache-2.0_card", task="translate",
                    source_payload={"source_turns": [{"user_text": "Q?", "assistant_text": "A."}]})
    oasst = deck._job(source_family="oasst2", source_repo="OpenAssistant/oasst2",
                      source_revision="r2", source_sha256="B" * 64, source_id="tree-1",
                      source_language="en", target_language="en", split="val",
                      license_name="Apache-2.0_card", task="repair",
                      source_payload={"source_turns": [{"user_text": "Why?", "assistant_text": "Because."}]})
    with tempfile.TemporaryDirectory(prefix="p106b_public_isolation_") as temporary:
        root = Path(temporary)
        public_manifest = root / "public_manifest.json"
        public_manifest.write_text("{}", encoding="utf-8")
        output = root / "HF" / "sft_ready" / "public_job_deck"
        quarantine = root / "HF" / "sft_ready" / "krdict_by_sa_quarantine"
        public = {"sources": {"aya": {"repo": "CohereLabs/aya_dataset", "revision": "r1"},
                              "oasst": {"repo": "OpenAssistant/oasst1", "revision": "r0"}}}

        def forbidden_protected_read():
            raise AssertionError("public-only execution touched the protected dictionary")

        with (patch.object(deck, "ROOT", root),
              patch.object(deck, "OUTPUT_DIR", output),
              patch.object(deck, "DICT_QUARANTINE_DIR", quarantine),
              patch.object(deck, "PUBLIC_MANIFEST", public_manifest),
              patch.object(deck, "public_inventory", return_value=(public, set())),
              patch.object(deck, "protected_inventory", side_effect=forbidden_protected_read),
              patch.object(deck, "aya_jobs", return_value=iter((aya,))),
              patch.object(deck, "oasst2_jobs", return_value=iter((oasst,)))):
            report = deck.census(write=True)
            assert report["output_scope"] == "PUBLIC_ONLY"
            assert report["jobs"] == report["public_jobs_emitted"] == 2
            assert report["dictionary_jobs_emitted"] == 0
            assert report["rights_gate"] == "PROTECTED_NOT_READ_HOLD"
            assert report["protected_source"] is None
            assert not quarantine.exists()
            manifest = json.loads((output / "public_jobs_shards_manifest.json").read_text(encoding="utf-8"))
            verify(output, manifest)
            assert manifest["rows"] == 2
            shard = (output / manifest["shards"][0]["path"]).read_text(encoding="utf-8")
            assert "krdict" not in shard and "protected_locator" in shard
            try:
                deck.census(write=True)
            except FileExistsError:
                pass
            else:
                raise AssertionError("public write-once output was overwritten")
    print("[PASS] public-only write-once shards, dictionary unread/unemitted, quarantine untouched")


if __name__ == "__main__":
    main()
