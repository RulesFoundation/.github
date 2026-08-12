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


def test_retired_schema_freeze_classifies_only_plural_citations() -> None:
    workflow = WORKFLOW.read_text()
    start = workflow.index("      - name: Verify immutable retired-schema freeze")
    end = workflow.index("      - name: Fetch pinned signed corpus release object")
    freeze_step = workflow[start:end]

    assert '"corpus_citation_paths" in source_verification' in freeze_step
    assert "upstream_source_check" not in freeze_step


def test_retired_schema_prefreeze_bridge_is_fail_closed() -> None:
    workflow = WORKFLOW.read_text()
    start = workflow.index("      - name: Verify immutable retired-schema freeze")
    end = workflow.index("      - name: Fetch pinned signed corpus release object")
    freeze_step = workflow[start:end]

    assert "allow-retired-schema-prefreeze" in workflow
    assert 'default: false' in workflow
    assert "pre-freeze compatibility is restricted to rulespec-us" in freeze_step
    assert "pre-freeze compatibility requires the generated guard" in freeze_step
    assert "pre-freeze compatibility cannot be used with a freeze" in freeze_step


def test_validation_waiver_audit_is_exhaustively_partitioned_across_matrix() -> None:
    workflow = WORKFLOW.read_text()
    start = workflow.index("      - name: Enforce validation waiver ratchet")
    end = workflow.index("      - name: Reject manual RuleSpec changes")
    audit_step = workflow[start:end]

    assert "matrix.shard == needs.shards.outputs.first" not in audit_step
    assert '--partition-key "${{ matrix.shard }}"' in audit_step
    assert "--partition-keys-json '${{ needs.shards.outputs.matrix }}'" in audit_step


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
    pr_base_ref: str = "main",
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
        "PR_BASE_REF": pr_base_ref,
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


def test_conflicted_merge_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "workflow-test@example.com")
        git(root, "config", "user.name", "Workflow Test")
        conflict = root / "conflict.txt"
        conflict.write_text("common\n")
        common = commit(root, "common")
        git(root, "switch", "-qc", "topic")
        conflict.write_text("topic\n")
        topic = commit(root, "conflicting topic")
        git(root, "switch", "-q", "main")
        git(root, "reset", "--hard", common)
        conflict.write_text("main\n")
        write_authorization(root, topic=topic)
        base = commit(root, "authorize conflicting topic")
        forged_merge = subprocess.run(
            [
                "git",
                "commit-tree",
                git(root, "rev-parse", f"{base}^{{tree}}"),
                "-p",
                base,
                "-p",
                topic,
            ],
            cwd=root,
            check=True,
            input="forged conflicted merge\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        result = run_authorization(
            root,
            base=base,
            event="push",
            github_sha=forged_merge,
            github_ref="refs/heads/main",
        )
        assert result.returncode != 0


def main() -> None:
    temp, root, base, topic = fixture()
    try:
        ordinary = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            retired="",
            waiver="",
            guard="true",
        )
        assert ordinary.returncode == 0, ordinary.stderr
        assert ordinary.stdout.splitlines() == ["authorized=false", "candidate="]

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
        wrong_base = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            pr_base_ref="release",
        )
        assert wrong_base.returncode != 0
        wrong_digest = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            waiver="3" * 64,
        )
        assert wrong_digest.returncode != 0
        wrong_retired = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            retired="3" * 64,
        )
        assert wrong_retired.returncode != 0
        wrong_pr = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            pr_number="912",
        )
        assert wrong_pr.returncode != 0
        wrong_repository = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            repository="example/fork",
        )
        assert wrong_repository.returncode != 0

        authorization = root / ".axiom/reviewed-migrations.json"
        duplicate = authorization.read_text().replace(
            f'"head": "{topic}"',
            f'"head": "{"0" * 40}", "head": "{topic}"',
        )
        authorization.write_text(duplicate)
        duplicate_base = commit(root, "duplicate authorization key")
        duplicate_result = run_authorization(
            root, base=duplicate_base, event="pull_request", pr_head=topic
        )
        assert duplicate_result.returncode != 0

        authorization.write_text("{\"format\":")
        malformed_base = commit(root, "malformed authorization")
        malformed_result = run_authorization(
            root, base=malformed_base, event="pull_request", pr_head=topic
        )
        assert malformed_result.returncode != 0

        write_authorization(root, topic=topic)
        authorization.write_bytes(authorization.read_text().encode("utf-16"))
        utf16_base = commit(root, "non-UTF-8 authorization")
        utf16_result = run_authorization(
            root, base=utf16_base, event="pull_request", pr_head=topic
        )
        assert utf16_result.returncode != 0

        authorization.unlink()
        target = root / "authorization-target.json"
        target.write_text("{}\n")
        authorization.symlink_to(Path("..") / target.name)
        symlink_base = commit(root, "symlink authorization")
        symlink_result = run_authorization(
            root, base=symlink_base, event="pull_request", pr_head=topic
        )
        assert symlink_result.returncode != 0

        git(root, "switch", "-q", "main")
        git(root, "reset", "--hard", base)
        non_merge = run_authorization(
            root,
            base=base,
            event="push",
            github_sha=topic,
            github_ref="refs/heads/main",
        )
        assert non_merge.returncode != 0

        altered_tree = subprocess.run(
            [
                "git",
                "commit-tree",
                git(root, "rev-parse", f"{base}^{{tree}}"),
                "-p",
                base,
                "-p",
                topic,
            ],
            cwd=root,
            check=True,
            input="altered merge tree\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        altered_result = run_authorization(
            root,
            base=base,
            event="push",
            github_sha=altered_tree,
            github_ref="refs/heads/main",
        )
        assert altered_result.returncode != 0

        octopus = subprocess.run(
            [
                "git",
                "commit-tree",
                git(root, "rev-parse", f"{base}^{{tree}}"),
                "-p",
                base,
                "-p",
                topic,
                "-p",
                duplicate_base,
            ],
            cwd=root,
            check=True,
            input="octopus\n",
            capture_output=True,
            text=True,
        ).stdout.strip()
        octopus_result = run_authorization(
            root,
            base=base,
            event="push",
            github_sha=octopus,
            github_ref="refs/heads/main",
        )
        assert octopus_result.returncode != 0

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
        wrong_first_parent = run_authorization(
            root,
            base=git(root, "rev-parse", f"{base}^"),
            event="push",
            github_sha=merge,
            github_ref="refs/heads/main",
        )
        assert wrong_first_parent.returncode != 0

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

    test_conflicted_merge_is_rejected()

    workflow = WORKFLOW.read_text()
    assert "migration-authorization-path" in workflow
    assert "bootstrap is not bound to an exact protected authorization" in workflow
    print("exact reviewed-migration authorization: ok")


if __name__ == "__main__":
    main()
