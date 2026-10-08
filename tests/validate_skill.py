#!/usr/bin/env python3
"""
Pre-publish checks for every skill in this tap. Stdlib only -- run it
directly from the repo root:

    python3 tests/validate_skill.py

Enforces the Hermes Skills Hub authoring rules that are easy to break
without noticing:

  - frontmatter starts on the very first line (no leading whitespace)
  - `name` matches the directory name and ^[a-z][a-z0-9_-]*$
  - `description` is one sentence, <= 60 characters, ends with a period
  - `version` is semver
  - every `references/*.md`, `scripts/*.py`, and `examples/*.py` path that
    SKILL.md mentions actually exists

Exits non-zero on any failure, so it's CI-friendly.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")


def frontmatter(text):
    """Return top-level `key: value` pairs from the YAML frontmatter."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("\"'")
    return fields


def check_skill(skill_dir):
    errors = []
    name = os.path.basename(skill_dir)
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return [f"{name}: missing SKILL.md"]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    fm = frontmatter(text)
    if fm is None:
        return [f"{name}: SKILL.md must start with '---' frontmatter on line 1"]

    if fm.get("name") != name:
        errors.append(f"{name}: frontmatter name '{fm.get('name')}' != directory name")
    if not re.match(r"^[a-z][a-z0-9_-]*$", fm.get("name", "")):
        errors.append(f"{name}: name must match ^[a-z][a-z0-9_-]*$")

    desc = fm.get("description", "")
    if not desc:
        errors.append(f"{name}: missing description")
    elif len(desc) > 60:
        errors.append(f"{name}: description is {len(desc)} chars (hub limit is 60)")
    elif not desc.endswith("."):
        errors.append(f"{name}: description must be one sentence ending with a period")

    if not re.match(r"^\d+\.\d+\.\d+$", fm.get("version", "")):
        errors.append(f"{name}: version must be semver, e.g. 1.0.0")

    for rel in sorted(set(re.findall(r"((?:references|scripts|examples)/[\w.-]+\.(?:md|py))", text))):
        if not os.path.isfile(os.path.join(skill_dir, rel)):
            errors.append(f"{name}: SKILL.md mentions {rel}, which does not exist")

    return errors


def main():
    skills = sorted(
        os.path.join(SKILLS_DIR, d) for d in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, d))
    )
    if not skills:
        print(f"FAILED: no skills found under {SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    errors = [e for s in skills for e in check_skill(s)]
    if errors:
        for e in errors:
            print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    for s in skills:
        print(f"OK: {os.path.basename(s)}")


if __name__ == "__main__":
    main()
