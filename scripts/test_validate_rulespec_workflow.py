#!/usr/bin/env python3
"""Exercise the embedded validation-waiver bootstrap authorization guard."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-rulespec.yml"
EXPECTED_HASH = "396e188da03b212c978b8b7bc222af6e5ee9fd26b32d942b64e92aaf73f8b748"
EXPECTED_ANCHOR = "b7cea0e625460f5170d6b4835283994dece963d8"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def guard_source() -> str:
    workflow = WORKFLOW.read_text()
    start = workflow.index("# waiver-bootstrap-guard-start")
    end = workflow.index("# waiver-bootstrap-guard-end")
    block = textwrap.dedent(workflow[start:end].split("\n", 1)[1])
    assert f'expected_bootstrap="{EXPECTED_HASH}"' in block
    assert f'reviewed_anchor="{EXPECTED_ANCHOR}"' in block
    return block


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, str, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "workflow-test@example.com")
    git(root, "config", "user.name", "Workflow Test")
    waiver = b"validate_failures:\n  retained: {}\n"
    (root / "known-validation-gaps.yaml").write_bytes(waiver)
    anchor = commit(root, "reviewed anchor")
    git(root, "switch", "-qc", "topic")
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/workflows/repository-checks.yml").write_text("name: caller\n")
    (root / "tests").mkdir()
    (root / "tests/test_legacy_rulespec_freeze.py").write_text("# contract\n")
    topic = commit(root, "pin shared workflow")
    digest = hashlib.sha256(waiver).hexdigest()
    return temp, root, anchor, topic, digest


def run_guard(
    root: Path,
    *,
    anchor: str,
    digest: str,
    event: str,
    pr_number: str = "",
    pr_head: str = "",
    github_sha: str = "",
    github_ref: str = "refs/pull/911/merge",
    message: str = "",
    repository: str = "TheAxiomFoundation/rulespec-us",
    base_ref: str = "",
    bootstrap: bool = True,
    bootstrap_value: str | None = None,
) -> subprocess.CompletedProcess[str]:
    protected = root / "protected.yaml"
    block = guard_source().replace(
        f'reviewed_anchor="{EXPECTED_ANCHOR}"', f'reviewed_anchor="{anchor}"'
    ).replace(
        f'expected_bootstrap="{EXPECTED_HASH}"', f'expected_bootstrap="{digest}"'
    )
    script = "\n".join(
        [
            "set -euo pipefail",
            'protected_base="$PROTECTED_BASE"',
            'base_ref="$BASE_REF"',
            block,
        ]
    )
    env = {
        **os.environ,
        "BOOTSTRAP_SHA256": (
            bootstrap_value if bootstrap_value is not None else digest if bootstrap else ""
        ),
        "EVENT_NAME": event,
        "PR_NUMBER": pr_number,
        "PR_HEAD_SHA": pr_head,
        "HEAD_COMMIT_MESSAGE": message,
        "GITHUB_REPOSITORY": repository,
        "GITHUB_SHA": github_sha or git(root, "rev-parse", "HEAD"),
        "GITHUB_REF": github_ref,
        "PROTECTED_BASE": str(protected),
        "BASE_REF": base_ref or anchor,
    }
    return subprocess.run(
        ["bash", "-c", script], cwd=root, env=env, capture_output=True, text=True
    )


def main() -> None:
    temp, root, anchor, topic, digest = fixture()
    try:
        approved_pr = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="911",
            pr_head=topic,
        )
        assert approved_pr.returncode == 0, approved_pr.stderr

        wrong_repo = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="911",
            pr_head=topic,
            repository="example/fork",
        )
        assert wrong_repo.returncode != 0

        wrong_hash = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="911",
            pr_head=topic,
            bootstrap_value="0" * 64,
        )
        assert wrong_hash.returncode != 0

        wrong_pr = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="912",
            pr_head=topic,
        )
        assert wrong_pr.returncode != 0

        (root / "unexpected.txt").write_text("drift\n")
        drift = commit(root, "unreviewed drift")
        changed_pr = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="911",
            pr_head=drift,
        )
        assert changed_pr.returncode != 0

        git(root, "switch", "-q", "main")
        (root / "base.txt").write_text("protected base\n")
        base = commit(root, "base advance")
        git(root, "merge", "--no-ff", "-qm", "Merge pull request #911 from org/topic", topic)
        merge = git(root, "rev-parse", "HEAD")
        approved_push = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="push",
            github_sha=merge,
            github_ref="refs/heads/main",
            message="Merge pull request #911 from org/topic",
            base_ref=base,
        )
        assert approved_push.returncode == 0, approved_push.stderr

        (root / "later.txt").write_text("later protected change\n")
        later_base = commit(root, "later base advance")
        replay_tree = git(root, "rev-parse", f"{later_base}^{{tree}}")
        replay = subprocess.run(
            [
                "git",
                "commit-tree",
                replay_tree,
                "-p",
                later_base,
                "-p",
                topic,
            ],
            cwd=root,
            check=True,
            input="Merge pull request #911 from org/topic\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        git(root, "reset", "--hard", replay)
        replayed_push = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="push",
            github_sha=replay,
            github_ref="refs/heads/main",
            message="Merge pull request #911 from org/topic",
            base_ref=later_base,
        )
        assert replayed_push.returncode != 0

        forged_push = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="push",
            github_sha=base,
            github_ref="refs/heads/main",
            message="Merge pull request #911 from org/topic",
            base_ref=anchor,
        )
        assert forged_push.returncode != 0

        ordinary = run_guard(
            root,
            anchor=anchor,
            digest=digest,
            event="pull_request",
            pr_number="999",
            pr_head=topic,
            base_ref=anchor,
            bootstrap=False,
        )
        assert ordinary.returncode == 0, ordinary.stderr
        assert (root / "protected.yaml").read_bytes() == git(
            root, "show", f"{anchor}:known-validation-gaps.yaml"
        ).encode() + b"\n"
    finally:
        temp.cleanup()

    print("validation-waiver bootstrap authorization: ok")


if __name__ == "__main__":
    main()
