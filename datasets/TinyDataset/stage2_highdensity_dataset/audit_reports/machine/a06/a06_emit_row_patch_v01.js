/* Emit an explicit A06 row-level patch; this helper never writes source. */
"use strict";
const fs = require("fs");
const path = require("path");

const HIGH_CONFIDENCE_RO = {
  "기록로": "기록으로", "승인로": "승인으로", "알림로": "알림으로", "차량로": "차량으로",
  "구역로": "구역으로", "트랩로": "트랩으로", "표본로": "표본으로", "계층로": "계층으로",
  "배수문로": "배수문으로", "슬롯로": "슬롯으로", "제출함로": "제출함으로", "게시판로": "게시판으로",
  "계정로": "계정으로", "승객로": "승객으로", "운반함로": "운반함으로", "팬로": "팬으로",
  "편성로": "편성으로", "랙로": "랙으로", "목록로": "목록으로", "배전반로": "배전반으로",
  "산림원로": "산림원으로", "판정로": "판정으로", "경계선로": "경계선으로", "관제판로": "관제판으로",
  "대기장로": "대기장으로", "묘목로": "묘목으로", "방송로": "방송으로", "상태판로": "상태판으로",
  "수문로": "수문으로", "일정로": "일정으로", "재킷로": "재킷으로", "접속반로": "접속반으로",
  "공급반로": "공급반으로", "대기함로": "대기함으로", "요원로": "요원으로", "촬영본로": "촬영본으로",
  "크레인로": "크레인으로", "탐침로": "탐침으로",
};

function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function directDuplicate(text) {
  let out = text;
  for (const word of ["경로", "표본"]) {
    const re = new RegExp(`(?<![A-Za-z가-힣])(${esc(word)})\\s+\\1(?![A-Za-z가-힣])`, "g");
    out = out.replace(re, "$1");
  }
  return out;
}

const fileArg = process.argv[2];
if (!fileArg) throw new Error("usage: node a06_emit_row_patch_v01.js <source.psv>");
const file = path.resolve(fileArg);
const name = path.basename(file);
const source = fs.readFileSync(file, "utf8");
const lines = source.split(/\r?\n/);
if (lines.length && lines[lines.length - 1] === "") lines.pop();
const changed = [];
for (let i = 1; i < lines.length; i += 1) {
  const oldLine = lines[i];
  const cells = oldLine.split("|");
  if (cells.length !== 4) continue;
  let concept = cells[0];
  let text = cells[3];
  const beforeConcept = concept;
  const beforeText = text;
  for (const [token, expected] of Object.entries(HIGH_CONFIDENCE_RO)) {
    concept = concept.split(token).join(expected);
    text = text.split(token).join(expected);
  }
  concept = directDuplicate(concept);
  text = directDuplicate(text);
  if (concept !== beforeConcept || text !== beforeText) {
    const next = [concept, cells[1], cells[2], text].join("|");
    changed.push({ line: i + 1, oldLine, next });
  }
}
if (!changed.length) process.exit(0);
let out = "*** Begin Patch\n";
out += `*** Update File: ${file.replace(/\\/g, "/")}\n`;
for (const item of changed) {
  out += "@@\n";
  out += `-${item.oldLine}\n`;
  out += `+${item.next}\n`;
}
out += "*** End Patch\n";
process.stdout.write(out);
