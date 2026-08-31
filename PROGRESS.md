# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow`; frozen review head `585d57a111ac06a398850861b1195f1cb788d80e` is based on cached `origin/main` and merge base `847217fe551238bfccfcd48c02e59edc4fe3a0e4`.
- The served-model-attested Fable review of that exact head returned `REQUEST_CHANGES` with five implementation blockers (F1-F5); remediation is in progress.
- The last locally fetched `origin/main` is `847217fe551238bfccfcd48c02e59edc4fe3a0e4`, fetched 2026-08-30 12:55 EDT; a live refresh was previously blocked by sandbox DNS (`github.com` could not be resolved).
- Scope is the reusable-workflow half of axiom-encode issue 1558 only.
- The sibling axiom-encode implementation is still uncommitted; its current `cca60e84` head is progress-only and is not a compatible core pin.
- Rollout remains **BLOCKED** until a reviewed compatible core implementation has an immutable commit SHA; no core pin will be invented or taken from uncommitted work.

## Done

- Inspected branch/upstream configuration, status, remotes, recent history, and the complete staged and unstaged diff.
- Confirmed there are no staged changes and no repository-local `AGENTS.md` instructions.
- Identified that the surviving WIP passes the protected base toolchain to the encoder audit but its inline ratchet still needs stronger fail-closed validation and adversarial coverage.
- Tightened the inline ratchet to admit exactly one new pending record only when the diff is exactly `known-validation-gaps.yaml` plus `.axiom/toolchain.toml`.
- Required strict waiver/toolchain key shapes, exact protected-base and head digest bindings, and a byte-for-byte toolchain comparison allowing only the canonical waiver digest replacement.
- Preserved decrement-only removal and exact pending-to-active consumption while rejecting pending replacement or retention during activation.
- Added self-tests for shared event-base provenance, third paths, wrong and stale digests, missing evidence, extra/duplicate/aliased keys, unrelated semantic and byte edits, pending batches, direct active replacement, and the valid two phases.
- Passed Python compilation, workflow YAML parsing, `git diff --check`, and the complete `scripts/test_validate_rulespec_workflow.py` self-test.
- Passed the repository's second workflow self-test (`scripts/test_legacy_oracle_coverage_workflow.py`), `ruff check scripts`, changed-workflow `actionlint`, all-workflow YAML parsing, and a repeated full waiver/authorization self-test.
- Completed raw-diff and independent security reviews with no actionable findings. The attempted GitNexus graph review indexed locally but could not register/query because sandbox policy forbids writing its global registry; its generated index was removed.
- Repeated the live `origin/main` fetch after review; DNS remains unavailable, so the cached `847217fe551238bfccfcd48c02e59edc4fe3a0e4` base cannot yet be re-certified as current.
- Re-inspected the applicable `/Users/maxghenis/AGENTS.md`, repository status and instructions, exact frozen head, cached base/merge base, complete base diff, and the untracked `PR_BODY.md` and `WORKER-REPORT.md` without modifying or discarding them.
- Read the complete `/private/tmp/fable-review-waiver-workflow-out.md` attestation and accepted F1-F5: activation needs independent inline expiry/state/scope/raw-evidence proof; creation needs exact-superset semantics; protected-base toolchain retrieval must fail closed; metadata types/expiry need inline validation; and exact regressions are required for every listed attack.

## Next

- Implement F1-F4 in the exact embedded workflow heredoc, including fail-closed protected-base toolchain retrieval with a narrow documented pre-migration compatibility condition.
- Add exact embedded-source self-tests for every Fable F5 attack while preserving all existing creation and authorization coverage.
- Document caller up-to-date-base/merge-queue protection, migration off the legacy pending-safe workflow, and the eventual core audit interface; make both handoff files honestly `BLOCKED` on a reviewed compatible core pin.
- Run the full workflow self-tests, changed-workflow `actionlint`, Ruff, Python compilation, all-workflow YAML parsing, and `git diff --check`; commit each coherent step and verify actual commit messages.
- If every local and remote precondition is green, fetch/reconcile, push, and open or update only a draft PR; verify its actual title/body/draft/head state and do not merge.

## Known baseline-only check noise

- Whole-repository `actionlint` reports two pre-existing `SC2129` style findings in untouched `.github/workflows/validate-rulespec-legacy-pending-safe.yml`; the changed workflow passes `actionlint` alone.
- `ruff format --check scripts` would reformat all three pre-existing scripts, including four untouched lines in the modified workflow test. `ruff check scripts` passes, and no unrelated formatting rewrite was made.
