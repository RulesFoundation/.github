# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow` at `847217fe551238bfccfcd48c02e59edc4fe3a0e4`.
- The pre-existing workflow, README, and workflow-test changes remain uncommitted and preserved.
- The last locally fetched `origin/main` is the same commit, fetched 2026-08-30 12:55 EDT; a live refresh was attempted but is currently blocked by sandbox DNS (`github.com` cannot be resolved).
- Scope is the reusable-workflow half of axiom-encode issue 1558 only.

## Done

- Inspected branch/upstream configuration, status, remotes, recent history, and the complete staged and unstaged diff.
- Confirmed there are no staged changes and no repository-local `AGENTS.md` instructions.
- Identified that the surviving WIP passes the protected base toolchain to the encoder audit but its inline ratchet still needs stronger fail-closed validation and adversarial coverage.

## Next

- Recover the exact encoder-core issue-1558 contract and required core head.
- Tighten the inline ratchet to allow only the encoder-supported pending shape while preserving decrement-only and pending-to-active behavior.
- Add adversarial self-tests for path scope, digests, schema keys, batches, active replacement, and stale protected evidence.
- Run all repository checks, parse/lint checks, and `git diff --check`; self-review and fix findings.
- Commit coherent steps, finalize this file and the requested output report, verify commit/PR text, push, and open a linked draft PR without merging.
