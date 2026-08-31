# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow`; progress baseline committed as `b786f77b077703ae97ecc70d565a74b1cbc73737`.
- The surviving workflow, README, and workflow-test WIP has been completed and is ready for its implementation commit.
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

## Next

- Commit the completed workflow implementation and adversarial self-tests.
- Run the remaining repository-wide checks and independent self-review; fix and commit any findings.
- Wait for or recover the terminal axiom-encode core implementation SHA; do not advertise the progress-only SHA.
- Finalize this file and `WORKER-REPORT.md`, verify commit/PR text, refresh `origin/main`, push, and open a linked draft PR without merging.
