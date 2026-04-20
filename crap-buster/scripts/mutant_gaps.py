#!/usr/bin/env python3
"""
mutant_gaps.py — parse PIT / pitest mutations.xml and report surviving mutants.

PIT emits mutations.xml like:

    <mutations>
      <mutation detected="false" status="SURVIVED" ...>
        <sourceFile>Foo.java</sourceFile>
        <mutatedClass>com.example.Foo</mutatedClass>
        <mutatedMethod>bar</mutatedMethod>
        <methodDescription>()V</methodDescription>
        <lineNumber>42</lineNumber>
        <mutator>org.pitest.mutationtest.engine.gregor.mutators.NegateConditionalsMutator</mutator>
        <description>negated conditional</description>
      </mutation>
    </mutations>

A surviving mutant is one the test suite failed to kill — i.e., a gap in
verification, not just in coverage. These are exactly the targets Phase 3
of crap-buster writes new tests for.

Usage:
    mutant_gaps.py --input target/pit-reports/<timestamp>/mutations.xml \\
                   --out docs/quality/surviving-mutants-YYYY-MM-DD.md \\
                   --json docs/quality/surviving-mutants-YYYY-MM-DD.json
    mutant_gaps.py --input ... --out report.md --compare baseline.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Mutant:
    klass: str
    method: str
    descriptor: str
    line: int
    mutator: str          # short name, e.g. "NegateConditionals"
    description: str
    source_file: str


MUTATOR_SHORT_RE = re.compile(r"([A-Za-z]+)Mutator$")


def _shorten_mutator(fqn: str) -> str:
    if not fqn:
        return "Unknown"
    last = fqn.rsplit(".", 1)[-1]
    m = MUTATOR_SHORT_RE.match(last)
    if m:
        return m.group(1)
    return last


def parse_pit(xml_path: Path) -> tuple[list[Mutant], dict[str, int]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    totals = {"total": 0, "killed": 0, "survived": 0, "no_coverage": 0, "other": 0}
    survivors: list[Mutant] = []

    for mut in root.findall("mutation"):
        status = (mut.get("status") or "").upper()
        detected = (mut.get("detected") or "").lower() == "true"
        totals["total"] += 1
        if status == "KILLED":
            totals["killed"] += 1
            continue
        if status == "SURVIVED":
            totals["survived"] += 1
        elif status == "NO_COVERAGE":
            totals["no_coverage"] += 1
        else:
            totals["other"] += 1

        # Collect both SURVIVED and NO_COVERAGE — both are gaps, slightly different kinds.
        if detected:
            continue
        if status not in ("SURVIVED", "NO_COVERAGE"):
            continue

        survivors.append(Mutant(
            klass=(mut.findtext("mutatedClass") or "").strip(),
            method=(mut.findtext("mutatedMethod") or "").strip(),
            descriptor=(mut.findtext("methodDescription") or "").strip(),
            line=int(mut.findtext("lineNumber") or "0"),
            mutator=_shorten_mutator((mut.findtext("mutator") or "").strip()),
            description=(mut.findtext("description") or "").strip(),
            source_file=(mut.findtext("sourceFile") or "").strip(),
        ))

    return survivors, totals


def group_by_class(mutants: list[Mutant]) -> dict[str, list[Mutant]]:
    out: dict[str, list[Mutant]] = defaultdict(list)
    for m in mutants:
        out[m.klass].append(m)
    for k in out:
        out[k].sort(key=lambda m: (m.line, m.method))
    return dict(sorted(out.items()))


def write_markdown(mutants: list[Mutant], totals: dict[str, int], out_path: Path,
                   baseline: dict | None = None) -> None:
    total = totals["total"]
    killed = totals["killed"]
    score = (killed / total * 100) if total else 0

    lines: list[str] = []
    lines.append(f"# Surviving mutants — {len(mutants)} across {len(set(m.klass for m in mutants))} classes")
    lines.append("")
    lines.append(f"- Mutation score: **{score:.1f}%** ({killed}/{total} mutants killed)")
    lines.append(f"- Survived: {totals['survived']}, no coverage: {totals['no_coverage']}, other: {totals['other']}")

    if baseline:
        b_total = baseline.get("total", 0)
        b_killed = baseline.get("killed", 0)
        b_score = (b_killed / b_total * 100) if b_total else 0
        lines.append("")
        lines.append(f"## Delta vs baseline")
        lines.append("")
        lines.append(f"- Mutation score: {b_score:.1f}% → {score:.1f}% ({score - b_score:+.1f} pp)")
        lines.append(f"- Survivors: {baseline.get('survivors', 0)} → {len(mutants)} "
                     f"({len(mutants) - baseline.get('survivors', 0):+d})")

    lines.append("")
    lines.append("## Survivors by class")

    for klass, items in group_by_class(mutants).items():
        lines.append("")
        lines.append(f"### `{klass}` — {len(items)} survivors")
        lines.append("")
        lines.append("| Line | Method | Mutator | Description |")
        lines.append("|---:|---|---|---|")
        for m in items:
            lines.append(f"| {m.line} | `{m.method}{m.descriptor}` | {m.mutator} | {m.description} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(mutants: list[Mutant], totals: dict[str, int], json_path: Path) -> None:
    payload = {
        "total": totals["total"],
        "killed": totals["killed"],
        "survived": totals["survived"],
        "no_coverage": totals["no_coverage"],
        "survivors": len(mutants),
        "mutants": [asdict(m) for m in mutants],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse PIT mutations.xml for surviving mutants.")
    ap.add_argument("--input", required=True, help="Path to PIT mutations.xml")
    ap.add_argument("--out", required=True, help="Path for the Markdown report")
    ap.add_argument("--json", help="Optional path for the JSON snapshot")
    ap.add_argument("--compare", help="Optional path to a prior JSON for delta reporting")
    args = ap.parse_args()

    xml_path = Path(args.input)
    if not xml_path.is_file():
        print(f"error: input not found: {xml_path}", file=sys.stderr)
        return 2

    mutants, totals = parse_pit(xml_path)

    baseline = None
    if args.compare:
        base_path = Path(args.compare)
        if not base_path.is_file():
            print(f"warning: --compare file not found, skipping delta: {base_path}", file=sys.stderr)
        else:
            baseline = json.loads(base_path.read_text(encoding="utf-8"))

    write_markdown(mutants, totals, Path(args.out), baseline=baseline)
    if args.json:
        write_json(mutants, totals, Path(args.json))

    score = (totals["killed"] / totals["total"] * 100) if totals["total"] else 0
    print(json.dumps({
        "mutation_score_pct": round(score, 2),
        "total_mutants": totals["total"],
        "survivors": len(mutants),
        "classes_with_survivors": len(set(m.klass for m in mutants)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
