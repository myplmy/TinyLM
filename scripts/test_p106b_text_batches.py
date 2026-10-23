#!/usr/bin/env python3
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import p106b_text_batches as b


class PacketTests(unittest.TestCase):
    def test_visible_controls_do_not_change_plain_text_or_legitimate_whitespace(self):
        text="질문\n답변\tA\r\n"
        shown,counts=b.visible_review_text(text)
        self.assertEqual(shown,text);self.assertEqual(counts,{})

    def test_visible_controls_are_shown_not_silently_removed(self):
        codes=list(range(9))+[11,12]+list(range(14,32))
        text="x"+"".join(map(chr,codes))+"y"
        shown,counts=b.visible_review_text(text)
        for code in codes:
            self.assertNotIn(chr(code),shown)
            self.assertEqual(counts[f"U+{code:04X}"],1)
            self.assertIn(f"[U+{code:04X}]",shown)
        self.assertIn("실제 원문",shown)

    def test_control_display_preserves_verified_native_source_and_candidate_shard(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/"out";out.mkdir()
            original="left"+chr(2)+"right"
            writer=b.ShardWriter(out,"review")
            writer.append(dict(source=dict(id=1,text=original),draft=dict(decision="HOLD",
                proposed_text=original,changes=[],reason="인쇄 문자 검토"),training_admission="NOT_ADMITTED"))
            manifest=writer.close(lineage=dict(training_admission="NOT_ADMITTED"))
            shard=out/manifest["shards"][0]["path"];before=shard.read_bytes()
            result=b.render_review(out,root/"view.md")
            self.assertEqual(shard.read_bytes(),before);b.verify(out,manifest)
            shown=(root/"view.md").read_text(encoding="utf-8")
            self.assertIn("left[U+0002]right",shown);self.assertNotIn(chr(2),shown)
            self.assertEqual(result["display_control_counts"],{"U+0002":2})
            self.assertFalse(result["source_and_candidate_bytes_modified"])

    def triage_fixture(self, root, responses):
        messages = [dict(role="user", content="질문"), dict(role="assistant", content="불확실한 원답")]
        canonical = dict(messages=messages, meta=dict(source_id="toy", supervised_assistant_turns=[1]))
        raw = (json.dumps(canonical, ensure_ascii=False) + "\n").encode()
        cp = root / "canonical.jsonl"; cp.write_bytes(raw)
        sources = [dict(source_index=i, source_id="toy", root_id="root" + str(i),
            messages=messages, meta=canonical["meta"],
            source_line_sha256=b.hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest().upper())
            for i in range(len(responses))]
        packet = root / "packet.json"; packet.write_text(json.dumps(dict(sources=sources,
            canonical_sha256=b.file_sha(cp))), encoding="utf-8")
        response = root / "response.json"; response.write_text(json.dumps(responses), encoding="utf-8")
        with mock.patch.object(b, "CANONICAL", cp), mock.patch.object(b, "source_rows",
                return_value=iter((i, raw, canonical) for i in range(len(responses)))):
            result = b.import_packet(packet, response, root / "out", "sft")
        self.assertEqual(cp.read_bytes(), raw)
        return result

    def test_triage_only_preserves_source_but_never_invents_three_variants(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder)
            result = self.triage_fixture(root, [dict(source_index=0, variants=[], triage_reason="원문 오류 의심")])
            self.assertEqual(result["source_rows"], 1)
            self.assertEqual(result["authored_source_rows"], 0)
            self.assertEqual(result["output_rows"], 0)
            self.assertEqual(result["triage_only_source_rows"], 1)
            self.assertFalse((root / "out/authoring_shards_manifest.json").exists())
            triage = json.loads((root / "out/triage_000000.jsonl").read_text())
            self.assertEqual(triage["original_messages"][1]["content"], "불확실한 원답")
            self.assertEqual(triage["classification"], "NOT_AUTHORED_TRIAGE_ONLY")
            self.assertEqual(triage["training_admission"], "NOT_ADMITTED")
            b.render_review(root / "out", root / "review.md")
            text = (root / "review.md").read_text()
            self.assertIn("새 변형: 0개", text)
            self.assertIn("불확실한 원답", text)
            self.assertNotIn("한국어 번역", text)

    def test_mixed_triage_and_authored_counts_and_human_text_are_separate(self):
        messages = [dict(role="user", content="질문"), dict(role="assistant", content="불확실한 원답")]
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder)
            result = self.triage_fixture(root, [dict(source_index=0, variants=[], triage_reason="추가 검토"),
                dict(source_index=1, variants=[dict(kind=k, messages=messages) for k in b.KINDS], triage_reason="")])
            self.assertEqual((result["source_rows"], result["authored_source_rows"],
                              result["output_rows"], result["triage_only_source_rows"]), (2, 1, 3, 1))
            self.assertEqual(result["triage_only_source_ids"], [0])
            b.render_review(root / "out", root / "review.md")
            text = (root / "review.md").read_text()
            self.assertEqual(text.count("## 원천 0 / 작성하지 않고 보류"), 1)
            self.assertIn("## 원천 1", text)
            self.assertIn("새 변형: 0개", text)

    def test_triage_only_needs_nonempty_literal_reason_before_any_output(self):
        for variants, reason in (([], ""), ([], "  "), ([], None), ({}, "검토")):
            with self.subTest(variants=variants, reason=reason), tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
                root = Path(folder)
                with self.assertRaisesRegex(ValueError, "triage_reason|nonempty reason"):
                    self.triage_fixture(root, [dict(source_index=0, variants=variants, triage_reason=reason)])
                self.assertFalse((root / "out").exists())

    def test_sft_dispatch_reserves_incomplete_sources_and_never_reissues_from_zero(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root=Path(folder);work=root/"work";(work/"packets").mkdir(parents=True)
            canonical=root/"canonical.jsonl";canonical.write_text("{}\n",encoding="utf-8")
            digest=b.file_sha(canonical)
            (work/"packets/sft_000001.json").write_text(json.dumps(dict(canonical_sha256=digest,
                sources=[dict(source_index=1)])),encoding="utf-8")
            jobs=root/"data_cache/p106b_native_text_audit_v2_policy/jobs";jobs.mkdir(parents=True)
            (jobs/"sft_canonical_en_jobs_v2_000000.jsonl").write_text("".join(json.dumps(
                dict(source_index=i,state="NOT_AUTHORED"))+"\n" for i in (1,2,3)),encoding="utf-8")
            def rows():
                return iter((i,b'{}\n',dict(meta=dict(source_id=str(i)),messages=[])) for i in (1,2,3))
            with mock.patch.object(b,"ROOT",root),mock.patch.object(b,"BASE",work), \
                    mock.patch.object(b,"CANONICAL",canonical),mock.patch.object(b,"source_rows",side_effect=rows):
                first=work/"packets/sft_000002.json";b.sft_packet(first,0,1)
                self.assertEqual(json.loads(first.read_text())["sources"][0]["source_index"],2)
                second=work/"packets/sft_000003.json";b.sft_packet(second,0,1)
                self.assertEqual(json.loads(second.read_text())["sources"][0]["source_index"],3)
                with self.assertRaisesRegex(ValueError,"no new source"):
                    b.sft_packet(work/"packets/sft_000004.json",0,1)

    def test_sft_dispatch_rejects_foreign_lineage_and_noninteger_ids(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            work=Path(folder);(work/"packets").mkdir()
            path=work/"packets/sft_000001.json"
            with mock.patch.object(b,"BASE",work):
                for packet in (dict(canonical_sha256="other",sources=[]),
                        dict(canonical_sha256="right",sources=[dict(source_index=True)])):
                    path.write_text(json.dumps(packet),encoding="utf-8")
                    with self.assertRaises(ValueError):b.issued_sft_sources("right")

    def test_explicit_comma_repair_preserves_string_literals_and_escapes(self):
        raw = r'[{"code":"a,] \\\" b,}","messages":[1,2,],},]'
        value, removed = b.explicit_trailing_comma_repair(raw)
        self.assertEqual(value,[dict(code='a,] \\\" b,}',messages=[1,2])])
        self.assertEqual(len(removed),3)

    def test_explicit_comma_repair_never_invents_missing_records_or_fixes_other_errors(self):
        for raw in ('[{"a":1} {"b":2}]','[{"a":"unterminated,]}','[1,2,broken,]'):
            with self.subTest(raw=raw),self.assertRaises(ValueError): b.explicit_trailing_comma_repair(raw)
        with self.assertRaisesRegex(ValueError,"ordinary import"): b.explicit_trailing_comma_repair('[{"a":1}]')

    def test_line_references_resolve_exact_range_and_preserve_other_text(self):
        source = "도입\n이름: 역할\n나머지\n"
        result, receipt = b.apply_positioned_edits(source,[dict(source_lines=[2,2],source_start="이름:",source_end="역할",
            action="MOVE_TO_PROSE",replacement="이름은 해당 역할을 맡았다.\n")])
        self.assertEqual(result,"도입\n이름은 해당 역할을 맡았다.\n나머지\n")
        self.assertEqual(receipt[0]["source_span_sha256"],b.sha("이름: 역할\n"))

    def test_line_reference_rejects_bad_bounds_ack_overlap_and_added_remove_content(self):
        good=dict(source_lines=[2,2],source_start="표제",source_end="표제",action="REMOVE",replacement="")
        source="첫줄\n표제\n표제\n"
        for patch in (dict(source_lines=[0,2]),dict(source_lines=[True,2]),dict(source_start="다름"),
                      dict(replacement="새 내용"),dict(source_span="표제")):
            with self.subTest(patch=patch),self.assertRaises(ValueError): b.apply_positioned_edits(source,[dict(good,**patch)])
        with self.assertRaisesRegex(ValueError,"overlap"):
            b.apply_positioned_edits(source,[good,good])
        self.assertEqual(b.apply_positioned_edits(source,[good])[0],"첫줄\n표제\n")

    def test_line_count_matches_lf_view_even_with_bare_carriage_return(self):
        self.assertEqual(b.lf_lines("a\rb\nc\n"),["a\rb\n","c\n"])

    def test_boundary_error_identifies_declared_change_without_moving_it(self):
        source="first\nsecond\nthird\n"
        good=dict(source_lines=[1,1],source_start="first",source_end="first",action="REMOVE",replacement="")
        bad=dict(source_lines=[2,3],source_start="second",source_end="wrong",action="REMOVE",replacement="")
        before=json.loads(json.dumps([good,bad]))
        with self.assertRaisesRegex(ValueError,"no fuzzy alignment") as found:
            b.apply_positioned_edits(source,[good,bad])
        detail=json.loads(str(found.exception).split("; ",2)[2])
        self.assertEqual(detail["change_index"],1)
        self.assertEqual(detail["source_lines"],[2,3])
        self.assertTrue(detail["start_ack_matches"])
        self.assertFalse(detail["end_ack_matches"])
        self.assertEqual(detail["expected_end"],"third")
        self.assertEqual([good,bad],before)

    def test_blank_boundary_error_is_explicit_not_guessed(self):
        bad=dict(source_lines=[1,2],source_start="heading",source_end="heading",action="REMOVE",replacement="")
        with self.assertRaises(ValueError) as found:
            b.apply_positioned_edits("heading\n \n",[bad])
        detail=json.loads(str(found.exception).split("; ",2)[2])
        self.assertEqual(detail["source_lines"],[1,2])
        self.assertEqual(detail["expected_end"],"")
        self.assertFalse(detail["end_ack_matches"])

    def test_only_boundary_ack_outer_whitespace_is_normalized_not_source_text(self):
        source="도입\n  제목 항목\n후문\n"
        result,receipt=b.apply_positioned_edits(source,[dict(source_lines=[2,2],
            source_start="  제목",source_end="항목  ",action="REMOVE",replacement="")])
        self.assertEqual(result,"도입\n후문\n")
        self.assertEqual(receipt[0]["source_span_sha256"],b.sha("  제목 항목\n"))
        self.assertTrue(receipt[0]["boundary_ack_whitespace_normalized"])
        self.assertEqual(receipt[0]["normalized_boundary_ack"],dict(source_start="제목",source_end="항목"))
        for begin in ("제 목", "제목 아님"):
            with self.assertRaises(ValueError):b.apply_positioned_edits(source,[dict(source_lines=[2,2],
                source_start=begin,source_end="항목",action="REMOVE",replacement="")])

    def test_strict_prefix_never_decodes_patch_markers_or_broken_row(self):
        text = '[{"id":1,"content":"escaped\\n+ legitimate"}, {"id":2,broken}\\n+ ]'
        rows, _ = b.valid_array_prefix(text)
        self.assertEqual(rows, [dict(id=1, content="escaped\n+ legitimate")])

    def test_prefix_does_not_skip_missing_record_separator(self):
        rows, _ = b.valid_array_prefix('[{"id":1} {"id":2}]')
        self.assertEqual(rows, [dict(id=1)])

    def test_source_object_directory_requires_full_exact_coverage(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder); responses = root / "responses"; responses.mkdir()
            text = "본문\n"
            (root / "packet.json").write_text(json.dumps(dict(documents=[dict(id=1,text=text,sha256=b.sha(text))])),encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly cover"):
                b.import_packet(root / "packet.json", responses, root / "out", "native")
            (responses / "1.json").write_text(json.dumps(dict(id=1, decision="KEEP", changes=[], review_notes="원형")),encoding="utf-8")
            result = b.import_packet(root / "packet.json", responses, root / "out", "native")
            self.assertEqual(result["response_identity_kind"], "SORTED_FILENAME_TO_FILE_SHA256_BUNDLE")
            self.assertEqual(result["source_rows"], 1)

    def import_one(self, response):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder)
            source = dict(id=1, text="본문\n외부 링크\n", sha256=b.sha("본문\n외부 링크\n"))
            (root / "packet.json").write_text(json.dumps(dict(documents=[source])), encoding="utf-8")
            (root / "response.json").write_text(json.dumps(response), encoding="utf-8")
            return b.import_packet(root / "packet.json", root / "response.json", root / "out", "native")

    def test_compact_keep_reconstructed_without_copy(self):
        r = self.import_one([dict(id=1, decision="KEEP", changes=[], review_notes="본문 보존")])
        self.assertEqual(r["output_rows"], 1)
        self.assertEqual(r["training_admission"], "NOT_ADMITTED")

    def test_declared_removal_only(self):
        r = self.import_one([dict(id=1, decision="REWRITE", review_notes="빈 꼬리",
            changes=[dict(source_span="외부 링크\n", action="REMOVE", replacement="", reason="빈 표제")])])
        self.assertEqual(r["source_rows"], 1)

    def test_review_missing_per_change_reason_is_explicit_not_invented(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root=Path(folder); text="본문\n외부 링크\n"
            packet=dict(documents=[dict(id=1,text=text,sha256=b.sha(text))])
            response=[dict(id=1,decision="REWRITE",review_notes="전체 검토 사유",
                changes=[dict(source_span="외부 링크\n",action="REMOVE",replacement="")])]
            (root/"packet.json").write_text(json.dumps(packet),encoding="utf-8")
            (root/"response.json").write_text(json.dumps(response),encoding="utf-8")
            b.import_packet(root/"packet.json",root/"response.json",root/"out","native")
            before=(root/"response.json").read_bytes()
            b.render_review(root/"out",root/"review.md")
            review=(root/"review.md").read_text(encoding="utf-8")
            self.assertIn("변경별 사유 미기재",review)
            self.assertIn("전체 검토 사유",review)
            self.assertEqual((root/"response.json").read_bytes(),before)

    def test_foreign_source_and_undeclared_changes_refused(self):
        with self.assertRaisesRegex(ValueError, "source IDs"):
            self.import_one([dict(id=2, decision="KEEP", changes=[])])
        with self.assertRaisesRegex(ValueError, "undeclared"):
            self.import_one([dict(id=1, decision="KEEP", changes=[], proposed_text="새 사실")])

    def test_review_reason_alias_or_missing_note_is_rendered_without_editing_inputs(self):
        for metadata, expected in ((dict(reason="작성자가 남긴 실제 사유"), "작성자가 남긴 실제 사유"),
                                   ({}, "상위 검토 사유 미기재"),
                                   (dict(review_notes="우선 사유", reason="대체 사유"), "우선 사유")):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory(dir=b.ROOT/"data_cache") as folder:
                root=Path(folder); text="원문 그대로\n"
                packet=dict(documents=[dict(id=1,text=text,sha256=b.sha(text))])
                response=[dict(id=1,decision="HOLD",changes=[],**metadata)]
                (root/"packet.json").write_text(json.dumps(packet),encoding="utf-8")
                (root/"response.json").write_text(json.dumps(response),encoding="utf-8")
                b.import_packet(root/"packet.json",root/"response.json",root/"out","native")
                before={p:p.read_bytes() for p in (root/"out").iterdir() if p.is_file()}
                b.render_review(root/"out",root/"review.md")
                review=(root/"review.md").read_text(encoding="utf-8")
                self.assertIn(expected,review)
                self.assertIn(text,review)
                self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))

    def test_hold_cannot_hide_edit(self):
        with self.assertRaisesRegex(ValueError, "KEEP/HOLD"):
            self.import_one([dict(id=1, decision="HOLD",
                changes=[dict(source_span="외부 링크\n", action="REMOVE", replacement="", reason="빈 표제")])])

    def test_multiturn_variant_all_messages_required(self):
        original = [dict(role=r, content=c) for r, c in
                    (("user", "첫 질문"), ("assistant", "첫 답"), ("user", "수정"), ("assistant", "교정 답"))]
        with self.assertRaises(ValueError):
            b.validate_variant_conversation(original, dict(kind="ko_translation", messages=original[:2]))

    def test_requested_language_and_unchanged_hold_are_not_translation_evidence(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder)
            messages = [dict(role="user", content="प्रश्न"), dict(role="assistant", content="उत्तर")]
            canonical = dict(messages=messages, meta=dict(source_id="toy"))
            raw = (json.dumps(canonical, ensure_ascii=False) + "\n").encode()
            (root / "canonical.jsonl").write_bytes(raw)
            source = dict(source_index=3, source_id="toy", root_id="root",
                source_line_sha256=b.hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest().upper(), messages=messages)
            (root / "packet.json").write_text(json.dumps(dict(sources=[source],
                canonical_sha256=b.file_sha(root / "canonical.jsonl"))), encoding="utf-8")
            response = [dict(source_index=3, source_id="toy", root_id="root", triage_reason="실제 원어 확인 필요",
                variants=[dict(kind=k, messages=messages) for k in b.KINDS])]
            (root / "response.json").write_text(json.dumps(response), encoding="utf-8")
            with mock.patch.object(b, "CANONICAL", root / "canonical.jsonl"), mock.patch.object(b, "source_rows", return_value=iter([(3, raw, canonical)])):
                r = b.import_packet(root / "packet.json", root / "response.json", root / "out", "sft")
            self.assertEqual(r["unchanged_variant_rows"], 3)
            self.assertEqual(r["distinct_changed_source_conversations"], 0)
            self.assertFalse(r["language_quota_eligible"])
            row = json.loads((root / "out/authoring_000000.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["language"], "UNVERIFIED")
            self.assertEqual(row["requested_language"], "ko")
            self.assertEqual(row["source_metadata"], canonical["meta"])
            self.assertEqual(row["meta"]["source_id"], canonical["meta"]["source_id"])
            self.assertEqual(row["meta"]["language"], "UNVERIFIED")
            self.assertEqual(row["supervision_contract"], "TURN_MASK_REVIEW_REQUIRED")

    def test_sft_metadata_is_packet_owned_but_wrong_supplied_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root=Path(folder);messages=[dict(role="user",content="Question"),dict(role="assistant",content="Answer")]
            canonical=dict(messages=messages,meta=dict(source_id="correct"));raw=(json.dumps(canonical)+"\n").encode()
            cp=root/"canonical.jsonl";cp.write_bytes(raw)
            source=dict(source_index=7,source_id="correct",root_id="root7",messages=messages,
                source_line_sha256=b.hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest().upper())
            packet=root/"packet.json";packet.write_text(json.dumps(dict(sources=[source],canonical_sha256=b.file_sha(cp))),encoding="utf-8")
            response=root/"response.json";record=dict(source_index=7,triage_reason="",variants=[dict(kind=k,messages=messages) for k in b.KINDS])
            response.write_text(json.dumps([record]),encoding="utf-8")
            with mock.patch.object(b,"CANONICAL",cp),mock.patch.object(b,"source_rows",return_value=iter([(7,raw,canonical)])):
                r=b.import_packet(packet,response,root/"out","sft")
            row=json.loads((root/"out/authoring_000000.jsonl").read_text().splitlines()[0])
            self.assertEqual((row["source_id"],row["root_id"]),("correct","root7"))
            self.assertIn("code_sha256",r)
            record["source_id"]="wrong";response.write_text(json.dumps([record]),encoding="utf-8")
            with mock.patch.object(b,"CANONICAL",cp),mock.patch.object(b,"source_rows",return_value=iter([(7,raw,canonical)])):
                with self.assertRaisesRegex(ValueError,"source identity"):b.import_packet(packet,response,root/"rejected","sft")

    def test_sft_import_preserves_only_explicit_source_supervised_turns(self):
        for allowed in ([2], [3], [True], [1,1], []):
            with self.subTest(allowed=allowed), tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
                root=Path(folder)
                messages=[dict(role=r,content=c) for r,c in (("user","첫 질문"),
                    ("assistant","처음 오해"),("user","교정 요청"),("assistant","교정 답"))]
                canonical=dict(messages=messages,meta=dict(source_id="toy",supervised_assistant_turns=allowed))
                raw=(json.dumps(canonical,ensure_ascii=False)+"\n").encode()
                original=root/"canonical.jsonl";original.write_bytes(raw)
                source=dict(source_index=7,source_id="toy",root_id="root",messages=messages,
                    meta=canonical["meta"],source_line_sha256=b.hashlib.sha256(raw.rstrip(b"\r\n")).hexdigest().upper())
                packet=root/"packet.json";packet.write_text(json.dumps(dict(sources=[source],canonical_sha256=b.file_sha(original))),encoding="utf-8")
                response=root/"response.json";response.write_text(json.dumps([dict(source_index=7,source_id="toy",root_id="root",triage_reason="",
                    variants=[dict(kind=k,messages=messages) for k in b.KINDS])]),encoding="utf-8")
                with mock.patch.object(b,"CANONICAL",original),mock.patch.object(b,"source_rows",return_value=iter([(7,raw,canonical)])):
                    if allowed==[2]:
                        b.import_packet(packet,response,root/"out","sft")
                        row=json.loads((root/"out/authoring_000000.jsonl").read_text().splitlines()[0])
                        self.assertEqual(row["meta"]["supervised_assistant_turns"],[2])
                        self.assertEqual(row["supervision_contract"],"INHERITED_EXPLICIT_ALLOWLIST")
                        self.assertEqual(row["messages"],messages)
                        self.assertEqual(row["training_admission"],"NOT_ADMITTED")
                    else:
                        with self.assertRaisesRegex(ValueError,"allowlist"):b.import_packet(packet,response,root/"out","sft")

    def test_full_queue_restores_original_span_and_excludes_issued_packet(self):
        from types import SimpleNamespace
        import numpy as np
        with tempfile.TemporaryDirectory(dir=b.ROOT / "data_cache") as folder:
            root = Path(folder)
            source = root / "original.bin"
            source.write_bytes(np.array([10,11,2,12,2], dtype="<u2").tobytes())
            tok = root / "data_cache/tok-ko-en-32768-chat32.json"
            tok.parent.mkdir(parents=True); tok.write_text("fixture", encoding="utf-8")
            text = "본문이 충분한 원문이어서 반드시 정확하게 보존합니다. 기타\n원문 사실"
            directory = root / "format"; directory.mkdir()
            writer = b.ShardWriter(directory / "review_queue", "positions")
            writer.append(dict(eos_segment_index=7, cache_segment_ids=[0,2],
                original_text_sha256=b.sha(text), review_reasons=["structured_list_relation_needs_source_reading"]))
            writer.close(lineage=dict(mock_only=True))
            manifest = json.loads((directory / "review_queue/positions_shards_manifest.json").read_text())
            report = dict(source="original.bin", source_sha256=b.file_sha(source), tokenizer_sha256=b.file_sha(tok),
                full_eos_pool_transformed=True, original_writes=0, manifests=dict(review_queue=manifest))
            (directory / "report.json").write_text(json.dumps(report), encoding="utf-8")
            work = root / "work"; (work / "packets").mkdir(parents=True)
            published = root / "data_cache/p106b_native_text_audit_v2_policy"
            published.mkdir(parents=True); (published / "published21_packet.json").write_text('{"documents":[]}', encoding="utf-8")
            fake = SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda _: SimpleNamespace(decode=lambda ids, **kw: text if ids==[10,11] else "WRONG")))
            with mock.patch.object(b,"ROOT",root), mock.patch.object(b,"BASE",work), mock.patch.dict(sys.modules,{"tokenizers":fake}):
                target = work / "packets/native_full_ko_000001.json"
                result = b.native_full_packet(directory,target,0,1,"ko")
                self.assertEqual(result["next_source_index"],8)
                row = json.loads(target.read_text())["documents"][0]
                self.assertEqual(row["text"],text)
                self.assertEqual(row["cache_segment_ids"],[0,2])
                with self.assertRaisesRegex(ValueError,"exhausted"):
                    b.native_full_packet(directory,work/"second.json",0,1,"ko")


if __name__ == "__main__":
    unittest.main()
