# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow`; verified documentation HEAD `00585de36d2aeb39bbc7cd6811484a10db12927f` is eight commits ahead of and zero behind the local `origin/main` snapshot `7dcdf2c5f46ee2a5d38e8f3c176eba52099a6a5a`, which is the exact merge base.
- The served-model-attested Fable review of frozen head `585d57a111ac06a398850861b1195f1cb788d80e` returned `REQUEST_CHANGES` with five implementation blockers (F1-F5). The inline remediation, exact extracted-source adversarial coverage, rollout documentation, and complete local verification are now green and ready to freeze for a second Fable review.
- A live `git fetch --all --prune --tags` was attempted first on 2026-08-31 and failed because sandbox DNS could not resolve `github.com`; `7dcdf2c5f46ee2a5d38e8f3c176eba52099a6a5a` is therefore the newest local remote-tracking snapshot, not a newly certified live tip.
- Salvage ref `refs/codex-salvage/fix-1558-waiver-transition-workflow-20260830-212607-42656` points to `9f9d6a22e609c8f07129672ac90565e3e653d87c`. Its useful workflow/test and handoff bytes were preserved; its generated Python cache was removed and never committed.
- Scope is the reusable-workflow half of axiom-encode issue 1558 only.
- The sibling axiom-encode implementation is still uncommitted; its current `cca60e84` head is progress-only and is not a compatible core pin.
- Rollout remains **BLOCKED** until a reviewed compatible core implementation has an immutable commit SHA; no core pin will be invented or taken from uncommitted work.
- This run uses the user-specified normal Standard service tier, `gpt-5.6-sol`, ultra reasoning, and no `--fast`.

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
- Re-inspected the current branch, cached upstream, merge base, four committed branch changes, exact salvage commit, dirty tracked bytes, untracked `PR_BODY.md`/`WORKER-REPORT.md`, and generated cache. No useful work needs to be guessed or discarded.
- Committed the F1-F5 implementation and exact-source regression expansion as `7e1bbdcdd8da3b3992b5c372a57eb61068cd4f53` after the waiver workflow self-test, changed-workflow `actionlint`, Ruff, and `git diff --check` passed.
- Added exact attacks for cross-module replacement, mixed creation/activation, isolated unrelated removals in both phases, strict/type/real/future expiry failures, activation scope, missing/corrupt/unreadable Git toolchain evidence, base/head waiver and toolchain raw-byte/digest mutations, and the exact authorized PR #911 pre-toolchain bootstrap composition.
- Rebased all six branch commits onto `7dcdf2c5f46ee2a5d38e8f3c176eba52099a6a5a`; the only tree difference from the pre-rebase implementation is that upstream's isolated `LANES.md` registry update is now present.
- Completed independent inline-security and test-coverage audits with no remaining F1-F5 finding.
- Documented the exact eventual core audit interface and independent reproof obligations, coordinated immutable repins, required up-to-date branch protection or merge queue, and mandatory migration off `validate-rulespec-legacy-pending-safe.yml`.
- Passed the complete post-rebase gate: both workflow self-tests, changed-workflow `actionlint`, `ruff check scripts`, all four workflow YAML parses, Python compilation for every script using an external temporary cache, both `git diff --check` forms, and a repository cache-artifact check.

## Next

- Keep `PR_BODY.md` and `WORKER-REPORT.md` explicitly **BLOCKED** on a reviewed compatible core SHA and the caller protection/migration rollout; never advertise `cca60e8420596d4aeaf55b8e5a9b872f32958238` as compatible.
- Freeze the final local head for a second Fable review.
- Restore GitHub DNS and valid `gh` authentication, fetch/reconcile the live base, push, and open or update only a draft PR; verify its actual title/body/draft/base/head state and do not merge.

## Known baseline-only check noise

- Whole-repository `actionlint` reports two pre-existing `SC2129` style findings in untouched `.github/workflows/validate-rulespec-legacy-pending-safe.yml`; the changed workflow passes `actionlint` alone.
- `ruff format --check scripts` would reformat all three pre-existing scripts, including four untouched lines in the modified workflow test. `ruff check scripts` passes, and no unrelated formatting rewrite was made.
