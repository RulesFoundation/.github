# Issue 1558 reusable-workflow progress

## State

- Branch: `fix/1558-waiver-transition-workflow`, rebased onto live `origin/main` at `e973d1563cdb22c09c82f7fd0a262fb642b2750c`. The only untracked handoff files remain the expected `PR_BODY.md` and `WORKER-REPORT.md`, and both are preserved.
- The served-model-attested second Fable review of frozen head `86cfa854715676d3f844f7b61a2c0701edeb550b` approved it as a draft only, confirmed F1-F5 resolved, and identified clear follow-ups: N1 pending-only module activation is currently a fail-closed dead end, N2 is an unused attacker-influenced environment value, and exact tests are missing for activation batches and pending-only cross-module replacement. N3 remains an explicitly accepted fail-closed shrink/no-op design unless direct analysis finds a bypass.
- A fresh live remote-ref and `gh pr view 107` check succeeded on 2026-08-31. Live `origin/main` is `e973d1563cdb22c09c82f7fd0a262fb642b2750c`; PR #107 remains open, draft, clean/mergeable, and green at the prior published head `3e7976cc2aaab4e3e712285814e335493187a950` while this rebased follow-up is finalized locally.
- Salvage ref `refs/codex-salvage/fix-1558-waiver-transition-workflow-20260830-212607-42656` points to `9f9d6a22e609c8f07129672ac90565e3e653d87c`. Its useful workflow/test and handoff bytes were preserved; its generated Python cache was removed and never committed.
- Scope is the reusable-workflow half of axiom-encode issue 1558 only.
- The workflow is reconciled to axiom-encode core candidate `ef7ecd0c0bff53f6d9340f8e4c100cf5ef8b6b21`, version `0.2.1752`, stacked directly after optional-inventory PR #1566. This exact candidate is reviewable but not yet on the protected default branch.
- Rollout remains **BLOCKED** until #1566 and the reviewed compatible core land, the workflow's exact core pin is reverified against the final protected-branch SHA, and callers repin both artifacts together.
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
- Re-inspected the exact requested head, upstream tracking and divergence, merge base, commit subjects, expected untracked handoff files, applicable `/Users/maxghenis/AGENTS.md`, full second Fable adjudication, README/core contract, PR body, worker report, and branch diff before making follow-up changes.
- Extended activation to consume an exact pending-only protected-base module into its exact active form, using the same expiry, raw waiver/toolchain evidence, exact path scope, digest-only toolchain mutation, and no-other-semantic-change proof as active-plus-pending rotation.
- Removed the unused attacker-influenced `HEAD_COMMIT_MESSAGE` environment value and added an exact-source assertion that it stays absent.
- Added exact extracted-source regressions for valid pending-only activation, a two-module activation batch spanning both supported activation forms, and pending creation that tries to replace a pending-only module on another path.
- Re-audited N3: decrement-only shrink/no-op still cannot add or mutate a retained active or pending record, the head waiver bytes remain digest-bound, and the independent core audit still runs on every matrix shard. This remains the documented accepted fail-closed design.
- Re-ran both workflow self-tests, changed-workflow `actionlint`, Ruff, all-workflow YAML parsing, external-cache Python compilation, the exact workflow self-test after compilation, and final whitespace checks successfully after the follow-up changes.
- Rebased the draft onto live main `e973d156`, preserving both untracked handoff files and isolating the workflow diff from the automated lane-registry update.
- Replaced newline path transport with bounded NUL-v1 bytes and the mandatory `--changed-paths-format nul-v1` core interface.
- Froze event base/head refs to exact commits after removing every ambient `GIT_*` variable and restoring a minimal read-only Git environment; materialized base and head waiver/toolchain evidence only from bounded exact `100644 blob` objects; compared live head bytes with the frozen head; and added poisoned-routing, missing, corrupt-object, executable, symlink, and ref-movement regressions.
- Kept pending creation at the exact waiver/toolchain pair. Activation now requires the pair, consumed module, and exactly one encoding-manifest path inline, while the pinned core authenticates the signed v5 manifest and exact generated-file closure. Both pending-only and active-plus-pending forms remain supported; waiver/toolchain-only activation now fails.
- Pinned this workflow candidate to core `ef7ecd0c...` / `0.2.1752`, retained the exact authorized pre-toolchain PR #911 bootstrap outside the core transition path, and passed the updated extracted-source workflow self-test, legacy coverage self-test, changed-workflow `actionlint`, and Ruff lint.

## Next

- Complete static/workflow checks, commit and verify the reconciled head, force-with-lease the already-rebased draft branch only against its verified prior remote head, then obtain new exact-head served-model Fable adjudications for both compatible heads.
- Keep rollout explicitly **BLOCKED** on #1566, the core merge/final SHA, coordinated caller repins, branch protection or merge queue, and legacy-workflow migration. Do not merge, sign, or roll out this draft.

## Known baseline-only check noise

- Whole-repository `actionlint` reports two pre-existing `SC2129` style findings in untouched `.github/workflows/validate-rulespec-legacy-pending-safe.yml`; the changed workflow passes `actionlint` alone.
- `ruff format --check scripts` would reformat the two untouched pre-existing scripts. The modified workflow test is formatted, `ruff check scripts` passes, and no unrelated formatting rewrite was made.
