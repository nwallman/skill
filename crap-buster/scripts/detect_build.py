#!/usr/bin/env python3
"""
detect_build.py — inspect a Java project and report what crap-buster needs to know.

Reports:
  - build tool: maven | gradle-groovy | gradle-kotlin | unknown
  - build file path(s)
  - Spring Boot version (if detectable)
  - Java version (source/target, from build file if declared)
  - JaCoCo plugin present: yes | no
  - PIT plugin present: yes | no
  - Lombok on classpath: yes | no
  - lombok.config has addLombokGeneratedAnnotation: yes | no | no-config-file
  - test framework: junit5 | junit4 | mixed | unknown

Output: JSON on stdout. Non-zero exit only for fatal errors (no recognisable
build file). Everything else is reported as a field the caller can react to.

Usage:
  python detect_build.py [project_root]

If project_root is omitted, uses cwd.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def find_build_file(root: Path) -> tuple[str, Path] | None:
    pom = root / "pom.xml"
    if pom.is_file():
        return "maven", pom
    gkts = root / "build.gradle.kts"
    if gkts.is_file():
        return "gradle-kotlin", gkts
    gg = root / "build.gradle"
    if gg.is_file():
        return "gradle-groovy", gg
    return None


def parse_pom(path: Path) -> dict:
    """Best-effort POM parser. Tolerates namespaces and missing fields."""
    info = {
        "spring_boot_version": None,
        "java_version": None,
        "has_jacoco": False,
        "has_pit": False,
        "has_lombok": False,
        "has_junit5": False,
        "has_junit4": False,
    }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        info["parse_error"] = str(e)
        return info

    # Strip default namespace to make XPath sane.
    text_no_ns = re.sub(r'\sxmlns="[^"]+"', "", text, count=1)
    try:
        root = ET.fromstring(text_no_ns)
    except ET.ParseError as e:
        info["parse_error"] = f"pom parse error: {e}"
        return info

    # Spring Boot: either as parent, or as dependency management.
    parent = root.find("parent")
    if parent is not None:
        group = (parent.findtext("groupId") or "").strip()
        artifact = (parent.findtext("artifactId") or "").strip()
        version = (parent.findtext("version") or "").strip()
        if group == "org.springframework.boot" and "spring-boot-starter-parent" in artifact:
            info["spring_boot_version"] = version

    for dep in root.iter("dependency"):
        g = (dep.findtext("groupId") or "").strip()
        a = (dep.findtext("artifactId") or "").strip()
        if g == "org.projectlombok" and a == "lombok":
            info["has_lombok"] = True
        if g == "org.junit.jupiter":
            info["has_junit5"] = True
        if g == "junit" and a == "junit":
            info["has_junit4"] = True
        if g == "org.springframework.boot" and info["spring_boot_version"] is None and a.startswith("spring-boot-"):
            v = (dep.findtext("version") or "").strip()
            if v:
                info["spring_boot_version"] = v

    # Plugins: JaCoCo and PIT.
    for plugin in root.iter("plugin"):
        g = (plugin.findtext("groupId") or "").strip()
        a = (plugin.findtext("artifactId") or "").strip()
        if g == "org.jacoco" and a == "jacoco-maven-plugin":
            info["has_jacoco"] = True
        if g == "org.pitest" and a in ("pitest-maven", "pitest-junit5-plugin"):
            info["has_pit"] = True

    # Java version.
    for props in root.iter("properties"):
        for child in props:
            tag = child.tag
            if tag in ("java.version", "maven.compiler.source", "maven.compiler.target", "maven.compiler.release"):
                if child.text and child.text.strip():
                    info["java_version"] = child.text.strip()
                    break
        if info["java_version"]:
            break

    return info


def parse_gradle(path: Path) -> dict:
    """Regex-based Gradle scanner. Not perfect, but good enough to identify plugins/deps."""
    info = {
        "spring_boot_version": None,
        "java_version": None,
        "has_jacoco": False,
        "has_pit": False,
        "has_lombok": False,
        "has_junit5": False,
        "has_junit4": False,
    }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        info["parse_error"] = str(e)
        return info

    # Plugins
    if re.search(r'\bid\s*\(?\s*["\']jacoco["\']', text):
        info["has_jacoco"] = True
    if re.search(r'\bid\s*\(?\s*["\']info\.solidsoft\.pitest["\']', text):
        info["has_pit"] = True

    # Spring Boot
    sb_plugin = re.search(r'org\.springframework\.boot["\']\s*(?:version\s*["\']([\d.]+)["\'])?', text)
    if sb_plugin:
        info["spring_boot_version"] = sb_plugin.group(1)
    if not info["spring_boot_version"]:
        sb_dep = re.search(r'spring-boot-starter[^"\']*["\']\s*,\s*version\s*:\s*["\']([\d.]+)', text)
        if sb_dep:
            info["spring_boot_version"] = sb_dep.group(1)

    # Java version
    jv = re.search(r'sourceCompatibility\s*=?\s*(?:JavaVersion\.VERSION_)?["\']?([\d.]+)["\']?', text)
    if jv:
        info["java_version"] = jv.group(1).replace("_", ".")
    else:
        jv2 = re.search(r'languageVersion\.set\(JavaLanguageVersion\.of\((\d+)\)\)', text)
        if jv2:
            info["java_version"] = jv2.group(1)

    # Deps
    if "org.projectlombok" in text or '"lombok"' in text or "'lombok'" in text:
        info["has_lombok"] = True
    if "junit-jupiter" in text:
        info["has_junit5"] = True
    if re.search(r'["\']junit["\']\s*:\s*["\']junit["\']', text) or "junit:junit:" in text:
        info["has_junit4"] = True

    return info


def check_lombok_config(root: Path) -> str:
    """Returns: yes | no | no-config-file"""
    cfg = root / "lombok.config"
    if not cfg.is_file():
        return "no-config-file"
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return "no-config-file"
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == "lombok.addLombokGeneratedAnnotation" and val.strip().lower() in ("true", "yes", "on"):
            return "yes"
    return "no"


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    found = find_build_file(root)
    if not found:
        print(json.dumps({
            "fatal": f"no pom.xml or build.gradle[.kts] found under {root}",
        }))
        return 1

    build_tool, build_file = found
    if build_tool == "maven":
        details = parse_pom(build_file)
    else:
        details = parse_gradle(build_file)

    # Test framework summary
    if details["has_junit5"] and details["has_junit4"]:
        test_framework = "mixed"
    elif details["has_junit5"]:
        test_framework = "junit5"
    elif details["has_junit4"]:
        test_framework = "junit4"
    else:
        test_framework = "unknown"

    lombok_config_status = check_lombok_config(root) if details["has_lombok"] else "n/a"

    out = {
        "project_root": str(root),
        "build_tool": build_tool,
        "build_file": str(build_file),
        "spring_boot_version": details["spring_boot_version"],
        "java_version": details["java_version"],
        "has_jacoco": details["has_jacoco"],
        "has_pit": details["has_pit"],
        "has_lombok": details["has_lombok"],
        "lombok_generated_annotation_enabled": lombok_config_status,
        "test_framework": test_framework,
        "has_git": (root / ".git").exists(),
    }
    if "parse_error" in details:
        out["parse_error"] = details["parse_error"]

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
