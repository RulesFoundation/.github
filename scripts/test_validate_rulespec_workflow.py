#!/usr/bin/env python3
"""Exercise the embedded exact reviewed-migration authorization guard."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-rulespec.yml"
RETIRED = "1" * 64
WAIVER = "2" * 64


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def authorization_source() -> str:
    workflow = WORKFLOW.read_text()
    start = workflow.index("# reviewed-migration-authorization-start")
    end = workflow.index("# reviewed-migration-authorization-end")
    block = textwrap.dedent(workflow[start:end].split("\n", 1)[1])
    marker = "python - <<'PY' >> \"$GITHUB_OUTPUT\"\n"
    assert block.startswith(marker)
    assert block.endswith("          PY\n") or block.endswith("PY\n")
    source = block[len(marker) :]
    source = source.rsplit("\nPY", 1)[0]
    return textwrap.dedent(source)


def write_authorization(root: Path, *, topic: str) -> None:
    path = root / ".axiom/reviewed-migrations.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "format": "axiom/reviewed-migrations/v1",
                "migrations": [
                    {
                        "pull_request": 911,
                        "head": topic,
                        "retired_schema_bootstrap_sha256": RETIRED,
                        "validation_waiver_bootstrap_sha256": WAIVER,
                    }
                ],
            }
        )
        + "\n"
    )


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "workflow-test@example.com")
    git(root, "config", "user.name", "Workflow Test")
    (root / "base.txt").write_text("initial\n")
    common = commit(root, "common")
    git(root, "switch", "-qc", "topic")
    (root / "topic.txt").write_text("reviewed\n")
    topic = commit(root, "reviewed topic")
    git(root, "switch", "-q", "main")
    git(root, "reset", "--hard", common)
    write_authorization(root, topic=topic)
    base = commit(root, "authorize exact topic")
    return temp, root, base, topic


def run_authorization(
    root: Path,
    *,
    base: str,
    event: str,
    pr_head: str = "",
    pr_number: str = "911",
    github_sha: str = "",
    github_ref: str = "refs/pull/911/merge",
    repository: str = "TheAxiomFoundation/rulespec-us",
    retired: str = RETIRED,
    waiver: str = WAIVER,
    guard: str = "false",
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "AUTHORIZATION_PATH": ".axiom/reviewed-migrations.json",
        "BASE_SHA": base,
        "EVENT_NAME": event,
        "PR_HEAD_SHA": pr_head,
        "PR_NUMBER": pr_number,
        "RETIRED_SCHEMA_BOOTSTRAP": retired,
        "VALIDATION_WAIVER_BOOTSTRAP": waiver,
        "RUN_GENERATED_GUARD": guard,
        "GITHUB_REPOSITORY": repository,
        "GITHUB_REF": github_ref,
        "GITHUB_SHA": github_sha or pr_head,
    }
    return subprocess.run(
        ["python", "-c", authorization_source()],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> None:
    temp, root, base, topic = fixture()
    try:
        approved = run_authorization(
            root, base=base, event="pull_request", pr_head=topic
        )
        assert approved.returncode == 0, approved.stderr
        assert approved.stdout.splitlines() == [
            "authorized=true",
            f"candidate={topic}",
        ]

        wrong_head = run_authorization(
            root, base=base, event="pull_request", pr_head=base
        )
        assert wrong_head.returncode != 0
        wrong_digest = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            waiver="3" * 64,
        )
        assert wrong_digest.returncode != 0
        wrong_repository = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            repository="example/fork",
        )
        assert wrong_repository.returncode != 0

        git(root, "switch", "-q", "main")
        git(root, "merge", "--no-ff", "-qm", "merge reviewed topic", topic)
        merge = git(root, "rev-parse", "HEAD")
        approved_push = run_authorization(
            root,
            base=base,
            event="push",
            github_sha=merge,
            github_ref="refs/heads/main",
        )
        assert approved_push.returncode == 0, approved_push.stderr

        (root / "later.txt").write_text("later\n")
        later_base = commit(root, "later base")
        replay_tree = git(root, "rev-parse", f"{later_base}^{{tree}}")
        replay = subprocess.run(
            ["git", "commit-tree", replay_tree, "-p", later_base, "-p", topic],
            cwd=root,
            check=True,
            input="replay\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        replayed = run_authorization(
            root,
            base=later_base,
            event="push",
            github_sha=replay,
            github_ref="refs/heads/main",
        )
        assert replayed.returncode != 0
    finally:
        temp.cleanup()

    workflow = WORKFLOW.read_text()
    assert "migration-authorization-path" in workflow
    assert "bootstrap is not bound to an exact protected authorization" in workflow
    print("exact reviewed-migration authorization: ok")


if __name__ == "__main__":
    main()
