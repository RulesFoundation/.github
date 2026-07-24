#!/usr/bin/env python3
"""Exercise the legacy workflow's isolated oracle-coverage compatibility path."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-rulespec-legacy-pending-safe.yml"
ENCODER_REF = "dc8feca0d1c15c98ccf817b7dba2b80a39f26e38"
ORACLE_REF = "7f1741128bd3a7c06c305061644fa5e0f0f9c1a1"
ORACLE_SPEC = (
    "axiom-oracles @ git+https://github.com/"
    f"TheAxiomFoundation/axiom-oracles@{ORACLE_REF}"
)


def step_source(workflow: str, name: str, next_name: str) -> str:
    start = workflow.index(f"      - name: {name}")
    end = workflow.index(f"      - name: {next_name}", start)
    return workflow[start:end]


def heredoc_source(step: str, command: str) -> str:
    marker = f"{command}\n"
    start = step.index(marker) + len(marker)
    end = step.index("\n          PY", start)
    lines = step[start:end].splitlines()
    return "\n".join(
        line.removeprefix("          ") for line in lines
    )


def run_dependency_parser(source: str, dependency: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        checkout = root / "_axiom/axiom-encode-oracle-coverage"
        checkout.mkdir(parents=True)
        (checkout / "pyproject.toml").write_text(
            "[project]\n"
            'name = "fixture"\n'
            'version = "0"\n'
            f"dependencies = [{dependency!r}]\n"
        )
        return subprocess.run(
            [sys.executable, "-c", source],
            cwd=root,
            capture_output=True,
            text=True,
        )


def run_filter(
    source: str,
    *,
    items: str,
) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        workspace = root / "rulespec-us"
        workspace.mkdir()
        coverage = root / "coverage.json"
        coverage.write_text(f'{{"items": {items}}}')
        changed = root / "changed.txt"
        changed.write_text(
            "us-in/policies/income_tax/2026_resident_liability_source_hold.yaml\n"
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous_argv = sys.argv
        previous_workspace = os.environ.get("GITHUB_WORKSPACE")
        sys.argv = ["filter", str(coverage), str(changed)]
        os.environ["GITHUB_WORKSPACE"] = str(workspace)
        status = 0
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(source, "<coverage-filter>", "exec"), {})
        except SystemExit as exc:
            status = int(exc.code or 0)
        finally:
            sys.argv = previous_argv
            if previous_workspace is None:
                os.environ.pop("GITHUB_WORKSPACE", None)
            else:
                os.environ["GITHUB_WORKSPACE"] = previous_workspace
        return status, stdout.getvalue(), stderr.getvalue()


def main() -> None:
    workflow = WORKFLOW.read_text()
    assert f"default: {ENCODER_REF}" in workflow

    install = step_source(
        workflow,
        "Install changed-file oracle coverage classifier",
        "Validate changed PolicyEngine oracle coverage classification",
    )
    assert "pip install -e" not in install
    assert 'pip install --force-reinstall --no-deps "$oracles_spec"' in install
    assert "retains legacy axiom-encode" in install

    parser = heredoc_source(install, "            python - <<'PY'")
    valid = run_dependency_parser(parser, ORACLE_SPEC)
    assert valid.returncode == 0, valid.stderr
    assert valid.stdout.strip() == ORACLE_SPEC

    mutable = run_dependency_parser(
        parser,
        "axiom-oracles @ git+https://github.com/"
        "TheAxiomFoundation/axiom-oracles@main",
    )
    assert mutable.returncode != 0

    coverage_start = workflow.index(
        "      - name: Validate changed PolicyEngine oracle coverage classification"
    )
    coverage_end = workflow.index("\n  validate-complete:", coverage_start)
    coverage = workflow[coverage_start:coverage_end]
    assert '--root "$GITHUB_WORKSPACE/.."' in coverage
    assert 'f"{repo}/{line.strip()}"' in coverage
    filter_source = heredoc_source(
        coverage,
        '          python - "$coverage_json" "$RULESPEC_FILE_LIST" <<\'PY\'',
    )
    target_file = (
        "rulespec-us/us-in/policies/income_tax/"
        "2026_resident_liability_source_hold.yaml"
    )
    comparable = (
        f'[{{"file": "{target_file}", "legal_id": "us-in:target#value", '
        '"status": "comparable", "tested": true}]'
    )
    status, stdout, stderr = run_filter(filter_source, items=comparable)
    assert status == 0, stderr
    assert "passed for 1 output(s)" in stdout

    unmapped = (
        f'[{{"file": "{target_file}", "legal_id": "us-in:target#value", '
        '"status": "unmapped", "tested": true}]'
    )
    status, _, stderr = run_filter(filter_source, items=unmapped)
    assert status == 1
    assert "us-in:target#value: unmapped" in stderr

    status, _, stderr = run_filter(filter_source, items="[]")
    assert status == 1
    assert "matched zero executable outputs" in stderr

    print("legacy oracle coverage overlay: ok")


if __name__ == "__main__":
    main()
