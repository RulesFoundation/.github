# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow`; implementation committed as `da539a85e478a52fc87da50dccf6b528a09c59bf` after the progress baseline `b786f77b077703ae97ecc70d565a74b1cbc73737`.
- The narrow reusable-workflow implementation and its adversarial self-tests are complete and reviewed.
- The last locally fetched `origin/main` is the same commit, fetched 2026-08-30 12:55 EDT; a live refresh was attempted but is currently blocked by sandbox DNS (`github.com` cannot be resolved).
- Scope is the reusable-workflow half of axiom-encode issue 1558 only.
- The sibling axiom-encode implementation is still uncommitted; its current `cca60e84` head is progress-only and is not a compatible core pin.

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

## Next

- Obtain the terminal axiom-encode core implementation SHA; do not advertise the incompatible progress-only `cca60e84` SHA.
- Restore GitHub DNS/authentication, fetch and compare live `origin/main`, and integrate any new base commits without discarding this branch.
- Finalize `WORKER-REPORT.md` and the prepared PR text with this branch's terminal commit SHA.
- Push, open a linked draft PR, and verify its actual title, body, draft state, and head SHA without merging.

## Known baseline-only check noise

- Whole-repository `actionlint` reports two pre-existing `SC2129` style findings in untouched `.github/workflows/validate-rulespec-legacy-pending-safe.yml`; the changed workflow passes `actionlint` alone.
- `ruff format --check scripts` would reformat all three pre-existing scripts, including four untouched lines in the modified workflow test. `ruff check scripts` passes, and no unrelated formatting rewrite was made.
