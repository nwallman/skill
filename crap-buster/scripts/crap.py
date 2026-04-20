#!/usr/bin/env python3
"""
crap.py — turn a JaCoCo jacoco.xml into a per-method CRAP report.

CRAP (Change Risk Anti-Pattern) score:
    CRAP(m) = comp(m)^2 + comp(m)^2 * (1 - coverage(m))^3
where comp is cyclomatic complexity and coverage is the fraction of lines
covered (0.0 .. 1.0). Low CRAP = simple and well-tested; high CRAP =
complex and poorly tested.

JaCoCo reports coverage as missed/covered counters per method. This script
joins the LINE and COMPLEXITY counters at the <method> level.

Usage:
    crap.py --input target/site/jacoco/jacoco.xml \\
            --out   docs/quality/baseline-YYYY-MM-DD.md \\
            --json  docs/quality/baseline-YYYY-MM-DD.json
    crap.py --input ... --out report.md --compare baseline.json

The --compare mode adds a delta column comparing the current run to an
earlier baseline JSON.

Exits non-zero only on argument / file errors.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MethodRow:
    package: str
    klass: str
    method: str
    descriptor: str
    line_start: int
    complexity: int
    lines_covered: int
    lines_missed: int
    coverage: float       # 0.0 .. 1.0, based on lines
    crap: float

    @property
    def fq(self) -> str:
        return f"{self.package}.{self.klass}.{self.method}{self.descriptor}"


def _counter(node: ET.Element, counter_type: str) -> tuple[int, int]:
    """Return (covered, missed) for the named counter, or (0,0) if absent."""
    for c in node.findall("counter"):
        if c.get("type") == counter_type:
            covered = int(c.get("covered", "0"))
            missed = int(c.get("missed", "0"))
            return covered, missed
    return 0, 0


def parse_jacoco(xml_path: Path) -> list[MethodRow]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    rows: list[MethodRow] = []
    for pkg in root.iter("package"):
        pkg_name = pkg.get("name", "").replace("/", ".")
        for cls in pkg.findall("class"):
            cls_name = cls.get("name", "").replace("/", ".")
            # Trim package prefix from the fully-qualified class name.
            if pkg_name and cls_name.startswith(pkg_name + "."):
                simple_cls = cls_name[len(pkg_name) + 1:]
            else:
                simple_cls = cls_name
            for m in cls.findall("method"):
                name = m.get("name", "")
                desc = m.get("desc", "")
                line = int(m.get("line", "0"))
                comp_cov, comp_miss = _counter(m, "COMPLEXITY")
                line_cov, line_miss = _counter(m, "LINE")
                complexity = comp_cov + comp_miss
                if complexity == 0:
                    # Can happen for synthetic bridge methods; skip.
                    continue
                total_lines = line_cov + line_miss
                if total_lines == 0:
                    # Abstract or interface method; skip.
                    continue
                coverage = line_cov / total_lines
                crap = (complexity ** 2) + (complexity ** 2) * ((1 - coverage) ** 3)
                rows.append(MethodRow(
                    package=pkg_name,
                    klass=simple_cls,
                    method=name,
                    descriptor=desc,
                    line_start=line,
                    complexity=complexity,
                    lines_covered=line_cov,
                    lines_missed=line_miss,
                    coverage=round(coverage, 4),
                    crap=round(crap, 2),
                ))
    rows.sort(key=lambda r: r.crap, reverse=True)
    return rows


def histogram(rows: list[MethodRow]) -> dict[str, int]:
    buckets = {"<=5": 0, "6-10": 0, "11-20": 0, "21-50": 0, ">50": 0}
    for r in rows:
        if r.crap <= 5:
            buckets["<=5"] += 1
        elif r.crap <= 10:
            buckets["6-10"] += 1
        elif r.crap <= 20:
            buckets["11-20"] += 1
        elif r.crap <= 50:
            buckets["21-50"] += 1
        else:
            buckets[">50"] += 1
    return buckets


def write_markdown(rows: list[MethodRow], out_path: Path, baseline: dict | None = None) -> None:
    total_methods = len(rows)
    avg_crap = sum(r.crap for r in rows) / total_methods if total_methods else 0
    buckets = histogram(rows)

    lines: list[str] = []
    lines.append(f"# CRAP report — {total_methods} methods")
    lines.append("")
    lines.append(f"- Average CRAP: **{avg_crap:.2f}**")
    lines.append(f"- Methods by CRAP bucket: " + ", ".join(f"{k}: {v}" for k, v in buckets.items()))

    if baseline:
        base_total = baseline.get("total_methods", 0)
        base_avg = baseline.get("avg_crap", 0)
        base_buckets = baseline.get("buckets", {})
        lines.append("")
        lines.append(f"## Delta vs baseline")
        lines.append("")
        lines.append(f"- Methods: {base_total} → {total_methods} ({total_methods - base_total:+d})")
        lines.append(f"- Average CRAP: {base_avg:.2f} → {avg_crap:.2f} ({avg_crap - base_avg:+.2f})")
        lines.append("")
        lines.append("| Bucket | Baseline | Current | Delta |")
        lines.append("|---|---:|---:|---:|")
        for b in ["<=5", "6-10", "11-20", "21-50", ">50"]:
            bv = base_buckets.get(b, 0)
            cv = buckets.get(b, 0)
            lines.append(f"| {b} | {bv} | {cv} | {cv - bv:+d} |")

    lines.append("")
    lines.append("## Top 50 methods by CRAP")
    lines.append("")
    lines.append("| CRAP | Complexity | Coverage | Method |")
    lines.append("|---:|---:|---:|---|")
    for r in rows[:50]:
        lines.append(
            f"| {r.crap:.1f} | {r.complexity} | {r.coverage*100:.0f}% "
            f"| `{r.package}.{r.klass}.{r.method}{r.descriptor}` (L{r.line_start}) |"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(rows: list[MethodRow], json_path: Path) -> None:
    total_methods = len(rows)
    avg_crap = sum(r.crap for r in rows) / total_methods if total_methods else 0
    payload = {
        "total_methods": total_methods,
        "avg_crap": round(avg_crap, 2),
        "buckets": histogram(rows),
        "methods": [asdict(r) for r in rows],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute per-method CRAP from JaCoCo XML.")
    ap.add_argument("--input", required=True, help="Path to jacoco.xml")
    ap.add_argument("--out", required=True, help="Path for the Markdown report")
    ap.add_argument("--json", help="Optional path for the JSON snapshot")
    ap.add_argument("--compare", help="Optional path to a prior JSON for delta reporting")
    args = ap.parse_args()

    xml_path = Path(args.input)
    if not xml_path.is_file():
        print(f"error: input not found: {xml_path}", file=sys.stderr)
        return 2

    rows = parse_jacoco(xml_path)

    baseline = None
    if args.compare:
        base_path = Path(args.compare)
        if not base_path.is_file():
            print(f"warning: --compare file not found, skipping delta: {base_path}", file=sys.stderr)
        else:
            baseline = json.loads(base_path.read_text(encoding="utf-8"))

    write_markdown(rows, Path(args.out), baseline=baseline)
    if args.json:
        write_json(rows, Path(args.json))

    # Summary on stdout so the caller can parse it.
    avg_crap = sum(r.crap for r in rows) / len(rows) if rows else 0
    print(json.dumps({
        "methods": len(rows),
        "avg_crap": round(avg_crap, 2),
        "buckets": histogram(rows),
        "over_10": sum(1 for r in rows if r.crap > 10),
        "over_30": sum(1 for r in rows if r.crap > 30),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
