#!/usr/bin/env python3
"""Detect producer/consumer naming desyncs in a rulespec corpus domain.

Per-file CI catches per-file errors. It does NOT catch the case where two
modules in different files use different names for the same legal concept,
because the engine treats unresolved name references as external inputs by
default. This check composes a domain (e.g. SNAP) into one synthetic
top-level program, compiles it via axiom-rules-engine, then walks the
lowered expression tree for ``Input { name }`` references that don't have
a matching producer.

Most unresolved references are legitimate external inputs (per-household
facts the runtime provides). The heuristic to flag suspicious ones:
names that start with the configured producer prefix (e.g. ``snap_``) are
expected to resolve to producer rules within the corpus; if they don't,
that's almost certainly a producer/consumer naming desync.

Used as a CI gate from the shared ``validate-rulespec`` workflow so every
rulespec-us-* repo inherits the check.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


DOMAIN_CONFIG: dict[str, dict] = {
    "snap": {
        "description": "Federal SNAP (statutes/7 + 7-cfr/273 + policies/usda/snap)",
        "federal_roots": [
            "statutes/7",
            "regulations/7-cfr/273",
            "policies/usda/snap",
        ],
        "state_roots": [],
        "producer_prefixes": ("snap_",),
    },
    "snap_us_co": {
        "description": "Colorado SNAP (CO state corpus + federal SNAP)",
        "federal_roots": [
            "statutes/7",
            "regulations/7-cfr/273",
            "policies/usda/snap",
        ],
        "state_roots": [
            "policies/cdhs/snap",
            "regulations/10-ccr-2506-1",
        ],
        "producer_prefixes": ("snap_", "co_snap_", "colorado_snap_"),
    },
    "snap_us_ny": {
        "description": "New York SNAP (NY state corpus + federal SNAP)",
        "federal_roots": [
            "statutes/7",
            "regulations/7-cfr/273",
            "policies/usda/snap",
        ],
        "state_roots": [
            "policies/otda/snap",
            "regulations/18-nycrr",
        ],
        "producer_prefixes": ("snap_", "ny_snap_"),
    },
}


def find_modules(corpus: Path, roots: list[str], namespace: str) -> list[str]:
    citations: list[str] = []
    for relative in roots:
        root = corpus / relative
        if not root.exists():
            continue
        for yaml_path in sorted(root.rglob("*.yaml")):
            if yaml_path.name.endswith(".test.yaml"):
                continue
            rel = yaml_path.relative_to(corpus).with_suffix("")
            citations.append(f"{namespace}:{rel}")
    return citations


def synthesize_top_module(citations: list[str], output: Path, domain: str) -> None:
    imports = "\n".join(f"  - {c}" for c in citations)
    output.write_text(
        "format: rulespec/v1\n"
        "module:\n"
        "  summary: |-\n"
        f"    Auto-generated {domain} composition for resolution audit.\n"
        f"imports:\n{imports}\n"
        "rules: []\n"
    )


def _compile(engine: Path, program: Path, output: Path, repo_roots: str) -> None:
    env = os.environ.copy()
    env["AXIOM_RULESPEC_REPO_ROOTS"] = repo_roots
    result = subprocess.run(
        [str(engine), "compile", "--program", str(program), "--output", str(output)],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError(
            f"axiom-rules-engine compile failed (exit {result.returncode})"
        )


def _collect_input_refs(expr, accumulator: set[str]) -> None:
    if not isinstance(expr, dict):
        return
    kind = expr.get("kind")
    if kind in {"input", "input_or_else"}:
        name = expr.get("name")
        if name:
            accumulator.add(name)
    if kind == "parameter_lookup":
        _collect_input_refs(expr.get("index"), accumulator)
    for key in (
        "expr", "condition", "then_expr", "else_expr",
        "left", "right", "value", "item",
        "date", "days", "from", "to",
        "where_clause", "where", "index",
    ):
        if key in expr:
            _collect_input_refs(expr[key], accumulator)
    for child in expr.get("items", []) or []:
        _collect_input_refs(child, accumulator)


def _find_unresolved(artifact: dict, producer_prefixes: tuple[str, ...]) -> dict[str, list[str]]:
    program = artifact.get("program", artifact)
    derived = program.get("derived", [])
    parameters = program.get("parameters", [])
    defined = {r["name"] for r in derived}
    defined.update({p["name"] for p in parameters})

    refs_by_name: dict[str, list[str]] = defaultdict(list)
    for rule in derived:
        refs: set[str] = set()
        _collect_input_refs(rule.get("expr") or rule.get("semantics"), refs)
        for name in refs:
            refs_by_name[name].append(rule["name"])

    suspicious: dict[str, list[str]] = {}
    for name, consumers in refs_by_name.items():
        if name in defined:
            continue
        if not name.startswith(producer_prefixes):
            continue
        suspicious[name] = sorted(set(consumers))
    return suspicious


def run_check(
    domain: str,
    federal_corpus: Path,
    engine: Path,
    state_corpus: Path | None = None,
) -> dict[str, list[str]]:
    cfg = DOMAIN_CONFIG[domain]
    citations = find_modules(federal_corpus, cfg["federal_roots"], namespace="us")
    if cfg["state_roots"]:
        if state_corpus is None:
            raise ValueError(f"domain '{domain}' requires --state-corpus")
        state_repo_name = state_corpus.name
        if state_repo_name.startswith("rulespec-"):
            state_ns = state_repo_name[len("rulespec-"):]
        elif state_repo_name.startswith("rules-"):
            state_ns = state_repo_name[len("rules-"):]
        else:
            state_ns = state_repo_name
        citations.extend(find_modules(state_corpus, cfg["state_roots"], state_ns))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        program = tmp_path / "compose.yaml"
        compiled = tmp_path / "compose.compiled.json"
        synthesize_top_module(citations, program, domain)
        _compile(engine, program, compiled, repo_roots=str(federal_corpus.parent))
        artifact = json.loads(compiled.read_text())
    return _find_unresolved(artifact, cfg["producer_prefixes"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "domains", nargs="*", default=None,
        help="Domains to check (default: all known)",
    )
    parser.add_argument(
        "--corpus", type=Path, required=True,
        help="Path to the federal rulespec-us corpus root.",
    )
    parser.add_argument(
        "--state-corpus", type=Path, default=None,
        help="Optional state corpus root (e.g. ~/rules-us-co).",
    )
    parser.add_argument(
        "--engine", type=Path,
        default=Path(os.environ.get("AXIOM_RULES_ENGINE_BINARY", "")) or None,
        help="Path to axiom-rules-engine binary.",
    )
    args = parser.parse_args()

    corpus = args.corpus.expanduser().resolve()
    if not corpus.exists():
        sys.exit(f"federal corpus not found: {corpus}")
    state_corpus = args.state_corpus.expanduser().resolve() if args.state_corpus else None
    if state_corpus is not None and not state_corpus.exists():
        sys.exit(f"state corpus not found: {state_corpus}")
    engine = args.engine.expanduser().resolve() if args.engine else None
    if engine is None or not engine.exists():
        sys.exit("axiom-rules-engine binary not found. Pass --engine or set AXIOM_RULES_ENGINE_BINARY.")

    domains = args.domains or sorted(DOMAIN_CONFIG)
    total_findings = 0
    for domain in domains:
        cfg = DOMAIN_CONFIG.get(domain)
        if cfg is None:
            sys.exit(f"unknown domain '{domain}' (known: {sorted(DOMAIN_CONFIG)})")
        needs_state = bool(cfg["state_roots"])
        if needs_state and state_corpus is None:
            print(f"[{domain}] skipped — requires --state-corpus")
            continue
        print(f"[{domain}] {cfg['description']}")
        findings = run_check(
            domain=domain,
            federal_corpus=corpus,
            engine=engine,
            state_corpus=state_corpus if needs_state else None,
        )
        if not findings:
            print(f"[{domain}] ✓ no unresolved producer references")
            continue
        print(f"[{domain}] {len(findings)} unresolved producer references:")
        for name in sorted(findings):
            consumers = findings[name]
            print(f"  {name}")
            for c in consumers[:3]:
                print(f"    consumed by: {c}")
            if len(consumers) > 3:
                print(f"    ... and {len(consumers) - 3} more")
        total_findings += len(findings)

    if total_findings:
        print(
            f"\nFound {total_findings} unresolved producer references. "
            "Fix by either renaming the consumer to match an existing producer, "
            "or adding a producer with the expected name. References that are "
            "genuinely external inputs should not start with a domain producer "
            "prefix (e.g. `snap_`) — rename to a domain-neutral identifier."
        )
        return 1
    print("\nAll domains clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
