# Copyright 2026 Agentic Data Intelligence SA
# SPDX-License-Identifier: Apache-2.0
"""Check the adi-authoring JSON Schemas.

Each schema must be a valid JSON Schema 2020-12 document whose $refs all
resolve. Every file the bundle schema describes (``contract.yaml`` ->
``contract_document.schema.json``, ...) must ship a per-document schema, and
the bundle repeats each per-document schema's root and $defs; those copies must
stay identical, or agents validating a single document and agents validating
the whole bundle would be told different things.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

SCHEMAS_DIR = Path("plugin/skills/adi-authoring/schemas")
BUNDLE = SCHEMAS_DIR / "adi_contract_bundle_v1.schema.json"

errors = 0


def error(path: Path, message: str) -> None:
    global errors
    errors += 1
    print(f"::error file={path}::{message}")


def refs(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            found.add(node["$ref"])
        for value in node.values():
            found |= refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= refs(value)
    return found


def document_schema_name(yaml_name: str) -> str:
    return yaml_name.removesuffix(".yaml") + "_document.schema.json"


def check_schema(path: Path) -> dict | None:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error(path, f"invalid JSON: {exc}")
        return None
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        error(path, "$schema must be https://json-schema.org/draft/2020-12/schema")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        error(path, f"not a valid JSON Schema: {exc.message}")
        return None
    resolver = Registry().with_resource("", Resource.from_contents(schema)).resolver()
    for ref in sorted(refs(schema)):
        try:
            resolver.lookup(ref)
        except Unresolvable:
            error(path, f"$ref {ref} does not resolve")
    return schema


def main() -> int:
    if not BUNDLE.is_file():
        error(BUNDLE, "bundle schema is missing")
        return 1
    paths = sorted(SCHEMAS_DIR.glob("*.schema.json"))
    schemas = {path: check_schema(path) for path in paths}
    bundle = schemas[BUNDLE]
    if bundle is None:
        return 1
    bundle_defs = bundle.get("$defs", {})

    # Every bundle property names a document; each needs its own schema whose root
    # matches the bundle's definition for it.
    expected = {}
    for yaml_name, prop in bundle.get("properties", {}).items():
        path = SCHEMAS_DIR / document_schema_name(yaml_name)
        expected[path] = yaml_name
        if path not in schemas:
            error(path, f"missing: {BUNDLE.name} describes {yaml_name} but this per-document schema does not exist")
            continue
        schema = schemas[path]
        ref = next(iter(sorted(refs(prop))), None)
        if schema is None or ref is None:
            continue
        root = {k: v for k, v in schema.items() if k not in ("$schema", "$defs")}
        if root != bundle_defs.get(ref.removeprefix("#/$defs/")):
            error(path, f"root schema differs from {ref} in {BUNDLE.name}")
    for path in schemas:
        if path != BUNDLE and path not in expected:
            error(path, f"not described by {BUNDLE.name}; add it to the bundle or remove it")

    for path, schema in schemas.items():
        if path == BUNDLE or schema is None:
            continue
        for name, definition in schema.get("$defs", {}).items():
            if name not in bundle_defs:
                error(path, f"$defs/{name} is missing from {BUNDLE.name}")
            elif definition != bundle_defs[name]:
                error(path, f"$defs/{name} differs from the copy in {BUNDLE.name}")
    print(f"Checked {len(paths)} schemas.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
