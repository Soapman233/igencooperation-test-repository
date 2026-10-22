#!/usr/bin/env python3
"""Validate every case in cases/ against schema/case.schema.json.

Pure standard library — no pip install required. The JSON Schema is the single
source of truth: this script implements only the keywords that schema actually
uses, so the two can never drift apart.

Usage:
    python tools/validate.py            # human-readable
    python tools/validate.py --quiet    # summary only
    python tools/validate.py --json     # machine-readable

Exit code 0 = all cases valid. Exit code 1 = at least one error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "cases"
SCHEMA_PATH = ROOT / "schema" / "case.schema.json"

# Soft quality hints. These never fail the build; they flag cases that will
# probably be sent back for revision.
FALSIFIER_MARKERS = ("证伪", "若", "如果", "当", "if ", "unless", "falsif", "when ")
OBSERVABLE_MIN_CHARS = 40


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check(value, schema: dict, path: str, errors: list[str], warnings: list[str]) -> None:
    """Validate `value` against the subset of JSON Schema this project uses."""

    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}: missing required field '{field}'")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                check(item, props[key], f"{path}.{key}", errors, warnings)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected field '{key}'")

    elif expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return
        if schema.get("uniqueItems") and len(set(map(str, value))) != len(value):
            errors.append(f"{path}: duplicate items are not allowed")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                check(item, item_schema, f"{path}[{index}]", errors, warnings)

    elif expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} chars ({len(value)})")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} chars ({len(value)})")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")


def lint(case: dict, warnings: list[str], label: str) -> None:
    """Non-blocking quality checks."""
    falsifier = case.get("falsifier", "")
    if falsifier and not any(marker in falsifier.lower() for marker in FALSIFIER_MARKERS):
        warnings.append(
            f"{label}: 'falsifier' contains no falsification marker "
            f"(证伪/若/如果/if/unless). Is it decidable?"
        )
    observable = case.get("observable", "")
    if observable and len(observable) < OBSERVABLE_MIN_CHARS:
        warnings.append(
            f"{label}: 'observable' is short ({len(observable)} chars) — "
            f"it should explain why the failure raises no suspicion"
        )
    if not case.get("notes"):
        warnings.append(f"{label}: no 'notes' — state what this case does NOT prove")


def selftest(schema: dict) -> int:
    """Prove this validator can actually fail.

    A gate that has never been seen to reject anything is not a gate. Each
    mutation below is a defect this project must catch; if any mutation slips
    through, the validator itself is broken.
    """
    template = {
        "id": "sf-9999",
        "title": "self test case",
        "falsifies": "a criterion worth overturning",
        "trigger": "a precondition long enough to pass",
        "observable": "a description of what the operator sees, long enough",
        "falsifier": "若把该字段移除后结论不变，则判据失效",
        "reported_verdict": "pass",
        "expected_verdict": "unknown",
        "reachability": "production",
        "domain": "unattended-loop",
        "contributed_by": "eigenflux#IuknQ",
    }

    def drop(field):
        def mutate(case):
            case.pop(field, None)
        return mutate

    def set_to(field, value):
        def mutate(case):
            case[field] = value
        return mutate

    mutations = [
        ("missing required field 'falsifier'", drop("falsifier")),
        ("unknown enum value for expected_verdict", set_to("expected_verdict", "probably-fine")),
        ("malformed contributor handle", set_to("contributed_by", "somebody")),
        ("malformed id", set_to("id", "case-1")),
        ("unknown extra field", set_to("severity", "high")),
    ]

    print("validator selftest — every injected defect must be rejected")
    failures = 0
    for label, mutate in mutations:
        case = json.loads(json.dumps(template))
        mutate(case)
        errors: list[str] = []
        check(case, schema, "selftest", errors, [])
        caught = bool(errors)
        print(f"  [{'PASS' if caught else 'FAIL'}] {label}"
              + ("" if caught else "  <-- validator did NOT catch this"))
        if not caught:
            failures += 1

    # And the unmutated template must pass, or the selftest proves nothing.
    errors, warnings = [], []
    check(json.loads(json.dumps(template)), schema, "selftest", errors, warnings)
    clean = not errors
    print(f"  [{'PASS' if clean else 'FAIL'}] unmutated template is accepted"
          + ("" if clean else f"  <-- {errors}"))
    if not clean:
        failures += 1

    print()
    print(f"selftest: {len(mutations) + 1 - failures}/{len(mutations) + 1} passed")
    return 1 if failures else 0



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="summary only")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--selftest", action="store_true",
                        help="inject known defects and assert the validator rejects them")
    args = parser.parse_args()

    schema = load_json(SCHEMA_PATH)

    if args.selftest:
        return selftest(schema)

    files = sorted(CASES_DIR.glob("*.json"))

    results = []
    seen_ids: dict[str, str] = {}

    for path in files:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            case = load_json(path)
        except json.JSONDecodeError as exc:
            results.append({"file": path.name, "id": None, "errors": [f"invalid JSON: {exc}"], "warnings": []})
            continue

        check(case, schema, path.stem, errors, warnings)

        case_id = case.get("id")
        if isinstance(case_id, str):
            if case_id != path.stem:
                errors.append(f"id '{case_id}' does not match filename '{path.stem}'")
            if case_id in seen_ids:
                errors.append(f"duplicate id '{case_id}' (also in {seen_ids[case_id]})")
            else:
                seen_ids[case_id] = path.name

        lint(case, warnings, path.stem)
        results.append({"file": path.name, "id": case_id, "errors": errors, "warnings": warnings})

    total_errors = sum(len(r["errors"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    if args.json:
        print(json.dumps({
            "cases": len(files),
            "errors": total_errors,
            "warnings": total_warnings,
            "results": results,
        }, ensure_ascii=False, indent=2))
        return 1 if total_errors else 0

    if not args.quiet:
        for result in results:
            status = "FAIL" if result["errors"] else ("warn" if result["warnings"] else "ok  ")
            print(f"[{status}] {result['file']}")
            for message in result["errors"]:
                print(f"        error: {message}")
            for message in result["warnings"]:
                print(f"        warn : {message}")

    print()
    print(f"cases: {len(files)}  errors: {total_errors}  warnings: {total_warnings}")
    if total_errors:
        print("RESULT: FAILED — fix the errors above before committing.")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
