#!/usr/bin/env python3
"""Validate ontology/terms.json.

Checks the invariants a term table actually needs — not just JSON validity:

  * every term has the required descriptive fields
  * term ids are unique
  * an alias belongs to exactly one term, and never shadows another term's id
  * every `distinct_from.term` points at a real term, and not at itself
  * the five core terms are present
  * enumerated terms carry a non-empty enum

Pure standard library.

Usage:
    python tools/validate_ontology.py
    python tools/validate_ontology.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = ROOT / "ontology" / "terms.json"

CORE_TERMS = ["receipt", "attestation", "witness", "verdict", "unknown"]
REQUIRED_FIELDS = ["id", "tier", "label_zh", "label_en", "definition", "aliases", "distinct_from"]
VALID_TIERS = {"core", "supporting"}


def load() -> dict:
    with ONTOLOGY_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check(doc: dict) -> list[str]:
    errors: list[str] = []

    if doc.get("schema_version") != "ontology.v1":
        errors.append(f"schema_version must be 'ontology.v1', got {doc.get('schema_version')!r}")

    terms = doc.get("terms")
    if not isinstance(terms, list) or not terms:
        errors.append("'terms' must be a non-empty list")
        return errors

    ids: dict[str, int] = {}
    alias_owner: dict[str, str] = {}
    all_ids = {t.get("id") for t in terms if isinstance(t.get("id"), str)}
    # `distinct_from` may point at another term, or at a value of some term's
    # enum (e.g. `fail` / `blocked` are verdict values, not standalone terms).
    enum_values = {
        str(value)
        for term in terms
        for value in (term.get("enum") or [])
    }
    valid_targets = all_ids | enum_values

    for index, term in enumerate(terms):
        label = term.get("id") or f"terms[{index}]"

        for field in REQUIRED_FIELDS:
            if field not in term:
                errors.append(f"{label}: missing required field '{field}'")

        term_id = term.get("id")
        if isinstance(term_id, str):
            if not term_id.strip():
                errors.append(f"{label}: empty id")
            elif term_id in ids:
                errors.append(f"{label}: duplicate id '{term_id}'")
            else:
                ids[term_id] = index

        if term.get("tier") not in VALID_TIERS:
            errors.append(f"{label}: tier must be one of {sorted(VALID_TIERS)}, got {term.get('tier')!r}")

        for field in ("label_zh", "label_en", "definition"):
            value = term.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: '{field}' must be a non-empty string")

        aliases = term.get("aliases")
        if not isinstance(aliases, list):
            errors.append(f"{label}: 'aliases' must be a list")
        else:
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    errors.append(f"{label}: alias entries must be non-empty strings")
                    continue
                key = alias.strip().lower()
                if key in alias_owner:
                    errors.append(
                        f"{label}: alias '{alias}' already claimed by '{alias_owner[key]}'"
                    )
                else:
                    alias_owner[key] = str(term_id)

        if "enum" in term:
            enum = term["enum"]
            if not isinstance(enum, list) or not enum:
                errors.append(f"{label}: 'enum' must be a non-empty list")
            elif len(set(map(str, enum))) != len(enum):
                errors.append(f"{label}: 'enum' contains duplicates")

        distinct = term.get("distinct_from")
        if isinstance(distinct, list):
            for entry in distinct:
                if not isinstance(entry, dict):
                    errors.append(f"{label}: distinct_from entries must be objects")
                    continue
                target = entry.get("term")
                if target not in valid_targets:
                    errors.append(f"{label}: distinct_from references unknown term '{target}'")
                if target == term_id:
                    errors.append(f"{label}: distinct_from must not reference itself")
                why = entry.get("why")
                if not isinstance(why, str) or len(why.strip()) < 10:
                    errors.append(
                        f"{label}: distinct_from '{target}' needs a 'why' of at least 10 chars"
                    )
        else:
            errors.append(f"{label}: 'distinct_from' must be a list")

    # An alias must not shadow another term's id — that makes lookup ambiguous.
    for alias, owner in alias_owner.items():
        if alias in ids and alias != owner:
            errors.append(f"alias '{alias}' (of '{owner}') shadows term id '{alias}'")

    present = {t.get("id") for t in terms if isinstance(t.get("id"), str)}
    for core in CORE_TERMS:
        if core not in present:
            errors.append(f"core term '{core}' is missing")

    return errors


def selftest() -> int:
    """Inject defects and assert this validator rejects them."""
    base = {
        "schema_version": "ontology.v1",
        "terms": [
            {
                "id": "alpha",
                "tier": "core",
                "label_zh": "甲",
                "label_en": "alpha",
                "definition": "a definition long enough to pass",
                "aliases": ["甲别名"],
                "distinct_from": [],
            },
            {
                "id": "beta",
                "tier": "supporting",
                "label_zh": "乙",
                "label_en": "beta",
                "definition": "another definition long enough",
                "aliases": ["乙别名"],
                "distinct_from": [{"term": "alpha", "why": "because they differ materially"}],
            },
        ],
    }

    def mutate(fn):
        doc = json.loads(json.dumps(base))
        fn(doc)
        return doc

    mutations = [
        ("duplicate term id", lambda d: d["terms"].append(dict(d["terms"][0]))),
        ("alias claimed twice", lambda d: d["terms"][1]["aliases"].append("甲别名")),
        ("unknown distinct_from target", lambda d: d["terms"][1]["distinct_from"].append(
            {"term": "gamma", "why": "points at nothing at all"})),
        ("distinct_from references itself", lambda d: d["terms"][1]["distinct_from"].append(
            {"term": "beta", "why": "this is a self reference"})),
        ("missing definition", lambda d: d["terms"][0].pop("definition")),
        ("invalid tier", lambda d: d["terms"][0].__setitem__("tier", "important")),
        ("alias shadows another id", lambda d: d["terms"][1]["aliases"].append("alpha")),
    ]

    print("ontology validator selftest — every injected defect must be rejected")
    failures = 0
    for label, fn in mutations:
        errors = check(mutate(fn))
        caught = bool(errors)
        print(f"  [{'PASS' if caught else 'FAIL'}] {label}"
              + ("" if caught else "  <-- validator did NOT catch this"))
        if not caught:
            failures += 1

    print()
    print(f"selftest: {len(mutations) - failures}/{len(mutations)} passed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    errors = check(load())
    for message in errors:
        print(f"error: {message}")
    print()
    print(f"ontology errors: {len(errors)}")
    if errors:
        print("RESULT: FAILED")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
