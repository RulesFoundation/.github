#!/usr/bin/env python3
"""Exercise the embedded exact reviewed-migration authorization guard."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

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
    assert 'AXIOM_ENCODE_WAIVER_AUDIT_WORKERS: "1"' in audit_step
    assert '--protected-base-toolchain "$protected_toolchain"' in audit_step


def test_validation_waiver_base_evidence_uses_one_event_ref() -> None:
    workflow = WORKFLOW.read_text()
    start = workflow.index("      - name: Enforce validation waiver ratchet")
    end = workflow.index("      - name: Reject manual RuleSpec changes")
    audit_step = workflow[start:end]

    assert 'base_ref="${{ github.event.pull_request.base.sha }}"' in audit_step
    assert 'git show "$base_ref:known-validation-gaps.yaml"' in audit_step
    assert 'git show "$base_ref:.axiom/toolchain.toml"' in audit_step
    assert '"$base_ref" "$GITHUB_SHA"' in audit_step
    assert "HEAD_COMMIT_MESSAGE" not in audit_step


def validation_waiver_ratchet_source() -> str:
    workflow = WORKFLOW.read_text()
    start = workflow.index("# validation-waiver-ratchet-start")
    end = workflow.index("# validation-waiver-ratchet-end")
    block = textwrap.dedent(workflow[start:end].split("\n", 1)[1])
    marker = (
        "python - \\\n"
        '  "$protected_base" \\\n'
        "  known-validation-gaps.yaml \\\n"
        '  "$changed_paths" \\\n'
        '  "$protected_toolchain" \\\n'
        "  .axiom/toolchain.toml <<'PY'\n"
    )
    assert block.startswith(marker)
    source = block[len(marker) :]
    source = source.rsplit("\nPY", 1)[0]
    return textwrap.dedent(source)


def protected_toolchain_evidence_source() -> str:
    workflow = WORKFLOW.read_text()
    start = workflow.index("# protected-toolchain-evidence-start")
    end = workflow.index("# protected-toolchain-evidence-end")
    block = textwrap.dedent(workflow[start:end].split("\n", 1)[1])
    assert block.startswith("toolchain_args=()\n")
    assert 'git cat-file -e "$base_ref:.axiom/toolchain.toml"' in block
    assert block.endswith("fi\n")
    return block


def waiver_bootstrap_guard_source() -> str:
    workflow = WORKFLOW.read_text()
    start = workflow.index("# waiver-bootstrap-guard-start")
    end = workflow.index("# waiver-bootstrap-guard-end")
    block = textwrap.dedent(workflow[start:end].split("\n", 1)[1])
    assert block.startswith('if [ -n "$BOOTSTRAP_SHA256" ]; then\n')
    assert 'git show "$MIGRATION_CANDIDATE:known-validation-gaps.yaml"' in block
    assert block.endswith("fi\n")
    return block


def run_validation_waiver_ratchet(
    root: Path,
    *,
    base: dict,
    head: dict,
    changed: list[str],
    base_toolchain: bytes | None = None,
    head_toolchain: bytes | None = None,
    base_waiver: bytes | None = None,
    head_waiver: bytes | None = None,
    omit_base_toolchain: bool = False,
) -> subprocess.CompletedProcess[str]:
    base_path = root / "base-waivers.yaml"
    head_path = root / "head-waivers.yaml"
    changed_path = root / "changed-paths.txt"
    base_toolchain_path = root / "base-toolchain.toml"
    head_toolchain_path = root / "head-toolchain.toml"
    base_path.write_bytes(
        base_waiver
        if base_waiver is not None
        else yaml.safe_dump(json.loads(json.dumps(base)), sort_keys=True).encode()
    )
    head_path.write_bytes(
        head_waiver
        if head_waiver is not None
        else yaml.safe_dump(json.loads(json.dumps(head)), sort_keys=True).encode()
    )
    changed_path.write_text("\n".join(changed) + "\n")
    if omit_base_toolchain:
        base_toolchain_path.unlink(missing_ok=True)
    else:
        base_toolchain_path.write_bytes(
            base_toolchain or toolchain_bytes(base_path.read_bytes())
        )
    head_toolchain_path.write_bytes(
        head_toolchain or toolchain_bytes(head_path.read_bytes())
    )
    return subprocess.run(
        [
            "python",
            "-c",
            validation_waiver_ratchet_source(),
            str(base_path),
            str(head_path),
            str(changed_path),
            str(base_toolchain_path),
            str(head_toolchain_path),
        ],
        capture_output=True,
        text=True,
    )


def run_protected_toolchain_evidence(
    root: Path,
    *,
    base_ref: str,
    bootstrap_sha256: str = "",
    migration_authorized: str = "false",
    path_prefix: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    runner_temp = root / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    protected_toolchain = runner_temp / "protected-toolchain.toml"
    env = {
        **os.environ,
        "BOOTSTRAP_SHA256": bootstrap_sha256,
        "MIGRATION_AUTHORIZED": migration_authorized,
        "RUNNER_TEMP": str(runner_temp),
    }
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    if extra_env is not None:
        env.update(extra_env)
    script = (
        "set -euo pipefail\n"
        'base_ref="$1"\n'
        'protected_toolchain="$2"\n'
        + protected_toolchain_evidence_source()
        + 'printf "toolchain-arg-count=%s\\n" "${#toolchain_args[@]}"\n'
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            script,
            "protected-toolchain-evidence-test",
            base_ref,
            str(protected_toolchain),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    return result, protected_toolchain


def run_authorized_bootstrap_toolchain_evidence(
    root: Path,
    *,
    base_ref: str,
    candidate: str,
    bootstrap_sha256: str,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    runner_temp = root / "bootstrap-runner-temp"
    runner_temp.mkdir(exist_ok=True)
    protected_base = runner_temp / "protected-known-validation-gaps.yaml"
    protected_toolchain = runner_temp / "protected-toolchain.toml"
    env = {
        **os.environ,
        "BOOTSTRAP_SHA256": bootstrap_sha256,
        "MIGRATION_AUTHORIZED": "true",
        "MIGRATION_CANDIDATE": candidate,
        "RUNNER_TEMP": str(runner_temp),
    }
    script = (
        "set -euo pipefail\n"
        'base_ref="$1"\n'
        'protected_base="$2"\n'
        'protected_toolchain="$3"\n'
        + waiver_bootstrap_guard_source()
        + protected_toolchain_evidence_source()
        + 'printf "toolchain-arg-count=%s\\n" "${#toolchain_args[@]}"\n'
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            script,
            "authorized-bootstrap-evidence-test",
            base_ref,
            str(protected_base),
            str(protected_toolchain),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    return result, protected_base


def waiver_metadata(seed: str) -> dict[str, str]:
    return {
        "fingerprint": f"sha256:{seed * 64}",
        "owner": "@waiver-reviewer",
        "issue": "https://github.com/TheAxiomFoundation/axiom-encode/issues/1558",
        "expires": (datetime.now(timezone.utc).date() + timedelta(days=365)).isoformat(),
    }


def toolchain_bytes(
    waiver_bytes: bytes,
    *,
    release: str = "test-release",
    corpus_digest: str = "a" * 64,
) -> bytes:
    return (
        "[toolchain]\n"
        f'axiom_corpus_release = "{release}"\n'
        f'axiom_corpus_release_content_sha256 = "{corpus_digest}"\n'
        f'validation_waiver_set_sha256 = "{hashlib.sha256(waiver_bytes).hexdigest()}"\n'
    ).encode()


def toolchain_evidence_repository(root: Path, *, include_toolchain: bool) -> str:
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "workflow-test@example.com")
    git(root, "config", "user.name", "Workflow Test")
    git(root, "config", "gc.auto", "0")
    (root / "tracked.txt").write_text("base\n")
    if include_toolchain:
        toolchain = root / ".axiom" / "toolchain.toml"
        toolchain.parent.mkdir()
        toolchain.write_bytes(toolchain_bytes(b"protected waiver bytes"))
    return commit(root, "protected base")


def test_validation_waiver_ratchet_admits_one_exactly_scoped_pending() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {"validate_failures": {"us/statutes/1.yaml": {"active": active}}}
    head = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending}
        }
    }
    with tempfile.TemporaryDirectory() as directory:
        accepted = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=head,
            changed=["known-validation-gaps.yaml", ".axiom/toolchain.toml"],
        )
        assert accepted.returncode == 0, accepted.stderr

        third_path = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=head,
            changed=[
                "known-validation-gaps.yaml",
                ".axiom/toolchain.toml",
                "README.md",
            ],
        )
        assert third_path.returncode != 0
        assert "must change exactly" in third_path.stderr


def test_validation_waiver_ratchet_binds_exact_toolchain_and_waiver_bytes() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {"validate_failures": {"us/statutes/1.yaml": {"active": active}}}
    head = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending}
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base_bytes = yaml.safe_dump(base, sort_keys=True).encode()
        head_bytes = yaml.safe_dump(head, sort_keys=True).encode()

        wrong_digest = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_toolchain=toolchain_bytes(b"not the head waiver bytes"),
        )
        assert wrong_digest.returncode != 0
        assert "does not bind the exact head waiver bytes" in wrong_digest.stderr

        stale_base = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_toolchain=toolchain_bytes(b"stale protected-base bytes"),
        )
        assert stale_base.returncode != 0
        assert "StaleBaseEvidence" in stale_base.stderr

        missing_base = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            omit_base_toolchain=True,
        )
        assert missing_base.returncode != 0
        assert "cannot read protected-base .axiom/toolchain.toml" in missing_base.stderr

        extra_key = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_toolchain=toolchain_bytes(head_bytes) + b'unexpected = "value"\n',
        )
        assert extra_key.returncode != 0
        assert "must contain exactly" in extra_key.stderr

        semantic_change = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_toolchain=toolchain_bytes(base_bytes),
            head_toolchain=toolchain_bytes(head_bytes, release="other-release"),
        )
        assert semantic_change.returncode != 0
        assert "may not change corpus release metadata" in semantic_change.stderr

        byte_change = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_toolchain=toolchain_bytes(head_bytes) + b"# unrelated byte change\n",
        )
        assert byte_change.returncode != 0
        assert "bytes may change only" in byte_change.stderr


def test_validation_waiver_ratchet_rejects_extra_waiver_keys() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {"validate_failures": {"us/statutes/1.yaml": {"active": active}}}
    head = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending}
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        extra_root = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": active, "pending": pending}
                },
                "unexpected": {},
            },
            changed=changed,
        )
        assert extra_root.returncode != 0
        assert "must contain exactly validate_failures" in extra_root.stderr

        extra_metadata = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": {**pending, "unexpected": "value"},
                    }
                }
            },
            changed=changed,
        )
        assert extra_metadata.returncode != 0
        assert "must contain exactly" in extra_metadata.stderr

        duplicate_root = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_waiver=(
                b"validate_failures: {}\n"
                b"validate_failures: {}\n"
            ),
        )
        assert duplicate_root.returncode != 0
        assert "found duplicate key" in duplicate_root.stderr

        alias_metadata = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_waiver=(
                "validate_failures:\n"
                "  us/statutes/1.yaml:\n"
                "    active: &approval\n"
                "      expires: '2026-10-01'\n"
                "      fingerprint: sha256:" + "a" * 64 + "\n"
                "      issue: https://github.com/TheAxiomFoundation/axiom-encode/issues/1558\n"
                "      owner: '@waiver-reviewer'\n"
                "    pending: *approval\n"
            ).encode(),
        )
        assert alias_metadata.returncode != 0
        assert "anchors and aliases are not allowed" in alias_metadata.stderr


def test_validation_waiver_ratchet_rejects_pending_batches_and_direct_active() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active},
            "us/statutes/2.yaml": {"active": active},
        }
    }
    batched = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending},
            "us/statutes/2.yaml": {"active": active, "pending": pending},
        }
    }
    direct = {
        "validate_failures": {"us/statutes/1.yaml": {"active": pending}}
    }
    with tempfile.TemporaryDirectory() as directory:
        batched_result = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=batched,
            changed=["known-validation-gaps.yaml", ".axiom/toolchain.toml"],
        )
        assert batched_result.returncode != 0
        assert "exactly one" in batched_result.stderr

        direct_result = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=direct,
            changed=["known-validation-gaps.yaml", ".axiom/toolchain.toml"],
        )
        assert direct_result.returncode != 0
        assert "may only shrink" in direct_result.stderr


def test_validation_waiver_ratchet_rejects_pending_replacement_and_retention() -> None:
    active = waiver_metadata("a")
    old_pending = waiver_metadata("b")
    new_pending = waiver_metadata("c")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": old_pending}
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        replacement = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": new_pending,
                    }
                }
            },
            changed=changed,
        )
        assert replacement.returncode != 0
        assert "may only shrink" in replacement.stderr

        retained = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": old_pending,
                        "pending": old_pending,
                    }
                }
            },
            changed=changed,
        )
        assert retained.returncode != 0
        assert "waivers may only shrink" in retained.stderr


def test_validation_waiver_ratchet_preserves_exact_pending_consumption() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending}
        }
    }
    head = {"validate_failures": {"us/statutes/1.yaml": {"active": pending}}}
    with tempfile.TemporaryDirectory() as directory:
        result = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=head,
            changed=[
                "known-validation-gaps.yaml",
                ".axiom/toolchain.toml",
            ],
        )
    assert result.returncode == 0, result.stderr


def test_validation_waiver_ratchet_admits_pending_only_activation() -> None:
    pending = waiver_metadata("b")
    base = {
        "validate_failures": {"us/statutes/1.yaml": {"pending": pending}}
    }
    head = {"validate_failures": {"us/statutes/1.yaml": {"active": pending}}}
    with tempfile.TemporaryDirectory() as directory:
        result = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=head,
            changed=[
                "known-validation-gaps.yaml",
                ".axiom/toolchain.toml",
            ],
        )
    assert result.returncode == 0, result.stderr


def test_validation_waiver_ratchet_rejects_activation_batches() -> None:
    active = waiver_metadata("a")
    first_pending = waiver_metadata("b")
    second_pending = waiver_metadata("c")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"pending": first_pending},
            "us/statutes/2.yaml": {
                "active": active,
                "pending": second_pending,
            },
        }
    }
    head = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": first_pending},
            "us/statutes/2.yaml": {"active": second_pending},
        }
    }
    with tempfile.TemporaryDirectory() as directory:
        result = run_validation_waiver_ratchet(
            Path(directory),
            base=base,
            head=head,
            changed=[
                "known-validation-gaps.yaml",
                ".axiom/toolchain.toml",
            ],
        )
    assert result.returncode != 0
    assert "ActivationBatch" in result.stderr


def test_validation_waiver_ratchet_rejects_cross_module_composites() -> None:
    active = waiver_metadata("a")
    old_pending = waiver_metadata("b")
    new_pending = waiver_metadata("c")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": old_pending},
            "us/statutes/2.yaml": {"active": active},
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        replacement = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": active},
                    "us/statutes/2.yaml": {
                        "active": active,
                        "pending": new_pending,
                    },
                }
            },
            changed=changed,
        )
        assert replacement.returncode != 0
        assert "PendingComposite" in replacement.stderr

        pending_only_replacement = run_validation_waiver_ratchet(
            root,
            base={
                "validate_failures": {
                    "us/statutes/1.yaml": {"pending": old_pending},
                    "us/statutes/2.yaml": {"active": active},
                }
            },
            head={
                "validate_failures": {
                    "us/statutes/2.yaml": {
                        "active": active,
                        "pending": new_pending,
                    }
                }
            },
            changed=changed,
        )
        assert pending_only_replacement.returncode != 0
        assert "PendingComposite" in pending_only_replacement.stderr

        mixed = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": old_pending},
                    "us/statutes/2.yaml": {
                        "active": active,
                        "pending": new_pending,
                    },
                }
            },
            changed=changed,
        )
        assert mixed.returncode != 0
        assert "MixedTransition" in mixed.stderr


def test_validation_waiver_ratchet_rejects_removals_during_creation() -> None:
    active = waiver_metadata("a")
    old_pending = waiver_metadata("b")
    new_pending = waiver_metadata("c")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active},
            "us/statutes/2.yaml": {"active": active},
            "us/statutes/3.yaml": {"active": active, "pending": old_pending},
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        active_removal = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": new_pending,
                    },
                    "us/statutes/3.yaml": {
                        "active": active,
                        "pending": old_pending,
                    },
                }
            },
            changed=changed,
        )
        assert active_removal.returncode != 0
        assert "PendingComposite" in active_removal.stderr

        pending_removal = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": new_pending,
                    },
                    "us/statutes/2.yaml": {"active": active},
                    "us/statutes/3.yaml": {"active": active},
                }
            },
            changed=changed,
        )
        assert pending_removal.returncode != 0
        assert "PendingComposite" in pending_removal.stderr


def test_validation_waiver_activation_rejects_unrelated_removals() -> None:
    active = waiver_metadata("a")
    target_pending = waiver_metadata("b")
    unrelated_pending = waiver_metadata("c")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {
                "active": active,
                "pending": target_pending,
            },
            "us/statutes/2.yaml": {"active": active},
            "us/statutes/3.yaml": {
                "active": active,
                "pending": unrelated_pending,
            },
        }
    }
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        active_removal = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": target_pending},
                    "us/statutes/3.yaml": {
                        "active": active,
                        "pending": unrelated_pending,
                    },
                }
            },
            changed=changed,
        )
        assert active_removal.returncode != 0
        assert "ActivationComposite" in active_removal.stderr

        pending_removal = run_validation_waiver_ratchet(
            root,
            base=base,
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": target_pending},
                    "us/statutes/2.yaml": {"active": active},
                    "us/statutes/3.yaml": {"active": active},
                }
            },
            changed=changed,
        )
        assert pending_removal.returncode != 0
        assert "ActivationComposite" in pending_removal.stderr


def test_validation_waiver_ratchet_rejects_invalid_transition_metadata() -> None:
    active = waiver_metadata("a")
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    invalid_expiries: list[tuple[object, str]] = [
        ("2000-01-01", "Expiry"),
        ("not-a-date", "Expiry"),
        ("2030-1-01", "Expiry"),
        ("2030-02-30", "Expiry"),
        (20300101, "Metadata"),
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for value, error in invalid_expiries:
            pending = waiver_metadata("b")
            pending["expires"] = value
            creation = run_validation_waiver_ratchet(
                root,
                base={
                    "validate_failures": {
                        "us/statutes/1.yaml": {"active": active}
                    }
                },
                head={
                    "validate_failures": {
                        "us/statutes/1.yaml": {
                            "active": active,
                            "pending": pending,
                        }
                    }
                },
                changed=changed,
            )
            assert creation.returncode != 0
            assert error in creation.stderr

            activation = run_validation_waiver_ratchet(
                root,
                base={
                    "validate_failures": {
                        "us/statutes/1.yaml": {
                            "active": active,
                            "pending": pending,
                        }
                    }
                },
                head={
                    "validate_failures": {
                        "us/statutes/1.yaml": {"active": pending}
                    }
                },
                changed=changed,
            )
            assert activation.returncode != 0
            assert error in activation.stderr

        non_string_owner = waiver_metadata("c")
        non_string_owner["owner"] = 1558
        owner_type = run_validation_waiver_ratchet(
            root,
            base={
                "validate_failures": {"us/statutes/1.yaml": {"active": active}}
            },
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": non_string_owner,
                    }
                }
            },
            changed=changed,
        )
        assert owner_type.returncode != 0
        assert "Metadata" in owner_type.stderr

        owner_type_activation = run_validation_waiver_ratchet(
            root,
            base={
                "validate_failures": {
                    "us/statutes/1.yaml": {
                        "active": active,
                        "pending": non_string_owner,
                    }
                }
            },
            head={
                "validate_failures": {
                    "us/statutes/1.yaml": {"active": non_string_owner}
                }
            },
            changed=changed,
        )
        assert owner_type_activation.returncode != 0
        assert "Metadata" in owner_type_activation.stderr


def test_validation_waiver_activation_rejects_scope_and_evidence_attacks() -> None:
    active = waiver_metadata("a")
    pending = waiver_metadata("b")
    base = {
        "validate_failures": {
            "us/statutes/1.yaml": {"active": active, "pending": pending}
        }
    }
    head = {"validate_failures": {"us/statutes/1.yaml": {"active": pending}}}
    changed = ["known-validation-gaps.yaml", ".axiom/toolchain.toml"]
    base_bytes = yaml.safe_dump(base, sort_keys=True).encode()
    head_bytes = yaml.safe_dump(head, sort_keys=True).encode()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        extra_path = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=[*changed, "us/statutes/1.yaml"],
        )
        assert extra_path.returncode != 0
        assert "ActivationScope" in extra_path.stderr

        missing_base = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            omit_base_toolchain=True,
        )
        assert missing_base.returncode != 0
        assert "cannot read protected-base .axiom/toolchain.toml" in missing_base.stderr

        corrupt_base = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_toolchain=b"[toolchain\n",
        )
        assert corrupt_base.returncode != 0
        assert "not valid UTF-8 TOML" in corrupt_base.stderr

        stale_base_digest = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_toolchain=toolchain_bytes(b"not protected-base waiver bytes"),
        )
        assert stale_base_digest.returncode != 0
        assert "StaleBaseEvidence" in stale_base_digest.stderr

        wrong_head_digest = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_toolchain=toolchain_bytes(b"not head waiver bytes"),
        )
        assert wrong_head_digest.returncode != 0
        assert "HeadDigest" in wrong_head_digest.stderr

        base_waiver_raw_mutation = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_waiver=b"# base raw-byte mutation\n" + base_bytes,
            base_toolchain=toolchain_bytes(base_bytes),
        )
        assert base_waiver_raw_mutation.returncode != 0
        assert "StaleBaseEvidence" in base_waiver_raw_mutation.stderr

        head_waiver_raw_mutation = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_waiver=b"# head raw-byte mutation\n" + head_bytes,
            head_toolchain=toolchain_bytes(head_bytes),
        )
        assert head_waiver_raw_mutation.returncode != 0
        assert "HeadDigest" in head_waiver_raw_mutation.stderr

        base_toolchain_raw_mutation = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            base_toolchain=(
                toolchain_bytes(base_bytes) + b"# base-only raw-byte mutation\n"
            ),
            head_toolchain=toolchain_bytes(head_bytes),
        )
        assert base_toolchain_raw_mutation.returncode != 0
        assert "ToolchainBytes" in base_toolchain_raw_mutation.stderr

        head_toolchain_raw_mutation = run_validation_waiver_ratchet(
            root,
            base=base,
            head=head,
            changed=changed,
            head_toolchain=(
                toolchain_bytes(head_bytes) + b"# head-only raw-byte mutation\n"
            ),
        )
        assert head_toolchain_raw_mutation.returncode != 0
        assert "ToolchainBytes" in head_toolchain_raw_mutation.stderr


def test_protected_toolchain_retrieval_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base_ref = toolchain_evidence_repository(root, include_toolchain=True)
        accepted, protected_toolchain = run_protected_toolchain_evidence(
            root,
            base_ref=base_ref,
        )
        assert accepted.returncode == 0, accepted.stderr
        assert "toolchain-arg-count=2" in accepted.stdout
        assert protected_toolchain.read_bytes() == (
            root / ".axiom" / "toolchain.toml"
        ).read_bytes()

        wrapper_dir = root / "git-wrapper"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "git"
        wrapper.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "show" ]; then\n'
            "  exit 42\n"
            "fi\n"
            'exec "$REAL_GIT" "$@"\n'
        )
        wrapper.chmod(0o755)
        real_git = shutil.which("git")
        assert real_git is not None
        show_failure, _ = run_protected_toolchain_evidence(
            root,
            base_ref=base_ref,
            path_prefix=wrapper_dir,
            extra_env={"REAL_GIT": real_git},
        )
        assert show_failure.returncode != 0
        assert "BaseToolchainUnreadable" in show_failure.stderr

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base_ref = toolchain_evidence_repository(root, include_toolchain=False)
        missing, _ = run_protected_toolchain_evidence(root, base_ref=base_ref)
        assert missing.returncode != 0
        assert "BaseToolchainMissing" in missing.stderr

        unreadable_ref, _ = run_protected_toolchain_evidence(
            root,
            base_ref="0" * 40,
        )
        assert unreadable_ref.returncode != 0
        assert "BaseRefUnreadable" in unreadable_ref.stderr

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base_ref = toolchain_evidence_repository(root, include_toolchain=True)
        blob = git(root, "rev-parse", f"{base_ref}:.axiom/toolchain.toml")
        blob_object = Path(
            git(
                root,
                "rev-parse",
                "--git-path",
                f"objects/{blob[:2]}/{blob[2:]}",
            )
        )
        if not blob_object.is_absolute():
            blob_object = root / blob_object
        assert blob_object.is_file()
        blob_object.unlink()
        unreadable_object, _ = run_protected_toolchain_evidence(
            root,
            base_ref=base_ref,
        )
        assert unreadable_object.returncode != 0
        assert "entry exists but its object is unreadable" in unreadable_object.stderr


def test_parallel_validation_workers_are_bounded_and_fail_closed() -> None:
    workflow = WORKFLOW.read_text()
    start = workflow.index("      - name: Validate RuleSpec YAML")
    end = workflow.index("      - name: Execute RuleSpec companion tests")
    validate_step = workflow[start:end]

    assert "validation-workers:" in workflow
    assert "default: 1" in workflow
    assert '[[ "$VALIDATION_WORKERS" =~ ^[1-4]$ ]]' in validate_step
    assert 'if ! wait "$pid"; then' in validate_step
    assert 'status=1' in validate_step
    assert 'for log_path in "${logs[@]}"; do' in validate_step
    assert 'exit "$status"' in validate_step


def write_authorization(
    root: Path,
    *,
    topic: str,
    retired_sha256: str = RETIRED,
    waiver_sha256: str = WAIVER,
) -> None:
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
                        "retired_schema_bootstrap_sha256": retired_sha256,
                        "validation_waiver_bootstrap_sha256": waiver_sha256,
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


def test_exact_authorized_bootstrap_may_lack_base_toolchain() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "workflow-test@example.com")
        git(root, "config", "user.name", "Workflow Test")
        git(root, "config", "gc.auto", "0")
        (root / "base.txt").write_text("initial\n")
        common = commit(root, "common")

        git(root, "switch", "-qc", "topic")
        waiver_bytes = b"validate_failures: {}\n"
        waiver_path = root / "known-validation-gaps.yaml"
        waiver_path.write_bytes(waiver_bytes)
        topic = commit(root, "exact bootstrap topic")
        waiver_sha256 = hashlib.sha256(waiver_bytes).hexdigest()

        git(root, "switch", "-q", "main")
        git(root, "reset", "--hard", common)
        write_authorization(
            root,
            topic=topic,
            waiver_sha256=waiver_sha256,
        )
        base = commit(root, "authorize exact bootstrap topic")

        authorization = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            waiver=waiver_sha256,
        )
        assert authorization.returncode == 0, authorization.stderr
        assert authorization.stdout.splitlines() == [
            "authorized=true",
            f"candidate={topic}",
        ]

        wrong_pr = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            pr_number="912",
            waiver=waiver_sha256,
        )
        assert wrong_pr.returncode != 0

        wrong_digest = run_authorization(
            root,
            base=base,
            event="pull_request",
            pr_head=topic,
            waiver="0" * 64,
        )
        assert wrong_digest.returncode != 0

        git(root, "switch", "-q", "topic")
        bootstrap, protected_base = run_authorized_bootstrap_toolchain_evidence(
            root,
            base_ref=base,
            candidate=topic,
            bootstrap_sha256=waiver_sha256,
        )
        assert bootstrap.returncode == 0, bootstrap.stderr
        assert "Accepted exact rulespec-us PR #911" in bootstrap.stdout
        assert "exact authorized rulespec-us PR #911 bootstrap" in bootstrap.stdout
        assert "toolchain-arg-count=0" in bootstrap.stdout
        assert protected_base.read_bytes() == waiver_bytes


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
    test_validation_waiver_audit_is_exhaustively_partitioned_across_matrix()
    test_validation_waiver_base_evidence_uses_one_event_ref()
    test_validation_waiver_ratchet_admits_one_exactly_scoped_pending()
    test_validation_waiver_ratchet_binds_exact_toolchain_and_waiver_bytes()
    test_validation_waiver_ratchet_rejects_extra_waiver_keys()
    test_validation_waiver_ratchet_rejects_pending_batches_and_direct_active()
    test_validation_waiver_ratchet_rejects_pending_replacement_and_retention()
    test_validation_waiver_ratchet_preserves_exact_pending_consumption()
    test_validation_waiver_ratchet_admits_pending_only_activation()
    test_validation_waiver_ratchet_rejects_activation_batches()
    test_validation_waiver_ratchet_rejects_cross_module_composites()
    test_validation_waiver_ratchet_rejects_removals_during_creation()
    test_validation_waiver_activation_rejects_unrelated_removals()
    test_validation_waiver_ratchet_rejects_invalid_transition_metadata()
    test_validation_waiver_activation_rejects_scope_and_evidence_attacks()
    test_protected_toolchain_retrieval_fails_closed()
    test_exact_authorized_bootstrap_may_lack_base_toolchain()
    test_parallel_validation_workers_are_bounded_and_fail_closed()
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
